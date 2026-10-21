/**
 * AuthStore
 *
 * Purpose:
 *     Central authentication store handling user session, tokens, login, MFA, and logout states.
 *
 * Inputs:
 *     Credentials, MFA verification codes, session restoration triggers, and logout commands.
 *
 * Outputs:
 *     Signals representing user profile, authentication status, error messages, and tokens.
 */
import { Injectable, signal, computed, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { catchError, finalize, map, shareReplay, tap } from 'rxjs/operators';
import { AuthApi, User } from '../api/auth-api';
import { HttpAuthApiService } from '../api/http-auth-api.service';
import { MockAuthApiService } from '../api/mock-auth-api.service';
import { StateService } from '../services/state.service';
import { environment } from '../../../environments/environment';

export type AuthStatus = 'idle' | 'loading' | 'authenticated' | 'unauthenticated' | 'mfa_required' | 'error';

@Injectable({
  providedIn: 'root'
})
export class AuthStore {
  /** Message shown when the session can no longer be renewed. */
  static readonly SESSION_EXPIRED_MESSAGE = 'Tu sesión expiró. Vuelve a iniciar sesión para continuar.';

  /** Renews the access token this long before it actually expires. */
  private static readonly RENEWAL_LEAD_MS = 90_000;

  /** A token that expires within this window is treated as already stale. */
  private static readonly STALE_WINDOW_MS = 30_000;

  private router = inject(Router);
  private stateService = inject(StateService);
  private authApi: AuthApi = environment.useMock ? inject(MockAuthApiService) : inject(HttpAuthApiService);

  // Core Signals - Access Token is stored in memory and mirrored to
  // sessionStorage so closing the tab ends the session (demo-friendly).
  readonly user = signal<User | null>(null);
  readonly accessToken = signal<string | null>(null);
  readonly status = signal<AuthStatus>('idle');
  readonly error = signal<string | null>(null);
  readonly mfaPendingEmail = signal<string | null>(null);
  readonly mfaPendingToken = signal<string | null>(null);
  readonly showSessionExpiredModal = signal<boolean>(false);

  /** Expiry (epoch ms) of the current access token; null when it cannot be read. */
  readonly tokenExpiresAt = signal<number | null>(null);

  // Derived Computed Signals
  readonly isAuthenticated = computed(() => !!this.user() && !!this.accessToken());
  readonly isLoading = computed(() => this.status() === 'loading');
  readonly isMfaRequired = computed(() => this.status() === 'mfa_required');
  readonly userRole = computed(() => this.user()?.role || 'Instructor');

  private broadcastChannel: BroadcastChannel | null = null;

  /** Timer that renews the access token before it expires. */
  private renewalTimer: ReturnType<typeof setTimeout> | null = null;

  /** In-flight renewal shared by concurrent callers. */
  private pendingRefresh$: Observable<string> | null = null;

  /** Identifies the newest renewal so a late answer cannot revive a closed session. */
  private refreshGeneration = 0;

  /** Incremented on every logout to invalidate pending renewals. */
  private sessionEpoch = 0;

  constructor() {
    this.restoreLocalSession();
    this.initBroadcastChannel();
  }

  private restoreLocalSession() {
    if (typeof window !== 'undefined' && window.sessionStorage) {
      try {
        // Drop tokens left in localStorage by older builds so the session
        // never leaks across tabs/restarts.
        localStorage.removeItem('nuevamente_jwt_token');
        localStorage.removeItem('nuevamente_user');

        const token = sessionStorage.getItem('nuevamente_jwt_token');
        const userStr = sessionStorage.getItem('nuevamente_user');
        if (token && userStr) {
          const user = JSON.parse(userStr);
          this.accessToken.set(token);
          this.user.set(user);
          this.status.set('authenticated');
          this.tokenExpiresAt.set(this.decodeTokenExpiry(token));
          this.scheduleTokenRenewal();
        }
      } catch (e) {
        console.warn('[AuthStore] Error restaurando sesión:', e);
      }
    }
  }

  private initBroadcastChannel() {
    if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
      this.broadcastChannel = new BroadcastChannel('nuevamente_auth_channel');
      this.broadcastChannel.onmessage = (event) => {
        if (event.data?.type === 'LOGOUT') {
          this.handleLocalLogoutState();
          this.router.navigate(['/auth/login'], { replaceUrl: true });
        }
      };
    }
  }

  // Session Initialization via HttpOnly Refresh Cookie
  initSession(): Promise<boolean> {
    return new Promise((resolve) => {
      if (this.isAuthenticated()) {
        resolve(true);
        return;
      }
      // Demo mode: never restore a session silently. A new tab always starts
      // on the login screen so a demo user can be picked explicitly.
      if (environment.enableDemoLogin) {
        this.status.set('unauthenticated');
        resolve(false);
        return;
      }
      this.status.set('loading');
      this.authApi.refreshToken().subscribe({
        next: (res) => {
          if (res.access_token && res.user) {
            this.setSession(res.access_token, res.user);
            resolve(true);
          } else {
            this.handleLocalLogoutState();
            resolve(false);
          }
        },
        error: () => {
          this.handleLocalLogoutState();
          resolve(false);
        }
      });
    });
  }

  login(email: string, password: string, mfaCode?: string) {
    this.status.set('loading');
    this.error.set(null);

    this.authApi.login(email, password, mfaCode).subscribe({
      next: (res) => {
        if (res.requires_mfa) {
          this.mfaPendingEmail.set(email);
          this.mfaPendingToken.set(res.mfa_token || null);
          this.status.set('mfa_required');
        } else if (res.access_token && res.user) {
          this.setSession(res.access_token, res.user);
          this.router.navigate(['/workspace']);
        }
      },
      error: (err) => {
        this.status.set('error');
        this.error.set(err?.error?.detail || 'Error al iniciar sesión. Verifique sus datos.');
      }
    });
  }

  loginMfa(mfaCode: string) {
    const email = this.mfaPendingEmail();
    const token = this.mfaPendingToken();
    if (!email) return;

    this.status.set('loading');
    this.error.set(null);

    this.authApi.loginMfa(email, mfaCode, token || undefined).subscribe({
      next: (res) => {
        if (res.access_token && res.user) {
          this.mfaPendingEmail.set(null);
          this.mfaPendingToken.set(null);
          this.setSession(res.access_token, res.user);
          this.router.navigate(['/workspace']);
        }
      },
      error: (err) => {
        this.status.set('mfa_required');
        this.error.set(err?.error?.detail || 'Código MFA incorrecto.');
      }
    });
  }

  register(name: string, email: string, password: string, role?: string, organization?: string) {
    this.status.set('loading');
    this.error.set(null);

    this.authApi.register(name, email, password, role, organization).subscribe({
      next: (res) => {
        if (res.access_token && res.user) {
          this.setSession(res.access_token, res.user);
          this.router.navigate(['/workspace']);
        }
      },
      error: (err) => {
        this.status.set('error');
        this.error.set(err?.error?.detail || 'Error al registrar la cuenta.');
      }
    });
  }

  setSession(token: string, user: User) {
    this.accessToken.set(token);
    this.user.set(user);
    this.status.set('authenticated');
    this.error.set(null);
    this.showSessionExpiredModal.set(false);
    this.tokenExpiresAt.set(this.decodeTokenExpiry(token));
    if (typeof window !== 'undefined' && window.sessionStorage) {
      try {
        sessionStorage.setItem('nuevamente_jwt_token', token);
        sessionStorage.setItem('nuevamente_user', JSON.stringify(user));
      } catch (e) {}
    }
    this.scheduleTokenRenewal();
  }

  logout() {
    this.authApi.logout().subscribe({
      next: () => this.executeLogout(),
      error: () => this.executeLogout()
    });
  }

  logoutAll() {
    this.authApi.logoutAll().subscribe({
      next: () => this.executeLogout(),
      error: () => this.executeLogout()
    });
  }

  private executeLogout() {
    this.handleLocalLogoutState();
    if (this.broadcastChannel) {
      this.broadcastChannel.postMessage({ type: 'LOGOUT' });
    }
    this.router.navigate(['/auth/login'], { replaceUrl: true });
  }

  handleLocalLogoutState() {
    this.user.set(null);
    this.accessToken.set(null);
    this.status.set('unauthenticated');
    this.error.set(null);
    this.tokenExpiresAt.set(null);
    this.sessionEpoch++;
    this.clearTokenRenewal();
    this.stateService.clearSessionData();
    if (typeof window !== 'undefined' && window.sessionStorage) {
      try {
        sessionStorage.removeItem('nuevamente_jwt_token');
        sessionStorage.removeItem('nuevamente_user');
        sessionStorage.removeItem('nuevamente_active_adaptation');
        sessionStorage.removeItem('nuevamente_projects');
      } catch (e) {}
    }
  }

  triggerSessionExpired() {
    this.showSessionExpiredModal.set(true);
  }

  closeSessionExpiredModal() {
    this.showSessionExpiredModal.set(false);
  }

  getAuthApi(): AuthApi {
    return this.authApi;
  }

  /**
   * Returns an access token that is safe to send, renewing it first when the
   * current one already expired or is about to expire.
   */
  getValidAccessToken(): Observable<string | null> {
    const token = this.accessToken();
    if (!token) return of(null);
    if (!this.needsRefresh(token)) return of(token);
    return this.refreshSession().pipe(map(() => this.accessToken()));
  }

  /** True when the token is missing or expires within the stale window. */
  needsRefresh(token: string | null = this.accessToken()): boolean {
    if (!token) return true;
    const expiresAt = this.decodeTokenExpiry(token);
    if (expiresAt === null) return false; // Unknown expiry: keep using the token.
    return expiresAt - Date.now() <= AuthStore.STALE_WINDOW_MS;
  }

  /**
   * Renews the access token with the HttpOnly refresh cookie.
   *
   * Concurrent callers share a single request. A failure is reported to the
   * caller, which decides whether the session-expired notice is shown.
   */
  refreshSession(): Observable<string> {
    if (this.pendingRefresh$) return this.pendingRefresh$;

    const generation = ++this.refreshGeneration;
    const epoch = this.sessionEpoch;

    this.pendingRefresh$ = this.authApi.refreshToken().pipe(
      tap(res => {
        // A logout happened while the renewal was in flight: the closed
        // session must not be revived.
        if (epoch !== this.sessionEpoch) return;
        if (res.access_token && res.user) {
          this.setSession(res.access_token, res.user);
        }
      }),
      map(res => {
        const token = res.access_token || this.accessToken();
        if (!token) throw new Error(AuthStore.SESSION_EXPIRED_MESSAGE);
        return token;
      }),
      catchError(() => throwError(() => new Error(AuthStore.SESSION_EXPIRED_MESSAGE))),
      finalize(() => {
        if (generation === this.refreshGeneration) {
          this.pendingRefresh$ = null;
        }
      }),
      shareReplay({ bufferSize: 1, refCount: false })
    );

    return this.pendingRefresh$;
  }

  /** Reads the `exp` claim (epoch ms) from a JWT; null when it cannot be read. */
  private decodeTokenExpiry(token: string): number | null {
    const segments = token.split('.');
    if (segments.length < 2 || typeof atob === 'undefined') return null;
    try {
      const base64 = segments[1].replace(/-/g, '+').replace(/_/g, '/');
      const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
      const payload = JSON.parse(atob(padded));
      return typeof payload?.exp === 'number' ? payload.exp * 1000 : null;
    } catch {
      return null;
    }
  }

  /**
   * Renews the access token shortly before it expires, so an idle session
   * never breaks the next request.
   */
  private scheduleTokenRenewal(): void {
    this.clearTokenRenewal();
    const expiresAt = this.tokenExpiresAt();
    if (!expiresAt) return;
    const delay = expiresAt - Date.now() - AuthStore.RENEWAL_LEAD_MS;
    // Already stale: the next request renews the token on demand instead.
    if (delay <= 0) return;
    this.renewalTimer = setTimeout(() => {
      this.renewalTimer = null;
      this.refreshSession().subscribe({
        error: () => console.warn('[AuthStore] No se pudo renovar el token de acceso.')
      });
    }, delay);
  }

  private clearTokenRenewal(): void {
    if (this.renewalTimer !== null) {
      clearTimeout(this.renewalTimer);
      this.renewalTimer = null;
    }
  }
}
