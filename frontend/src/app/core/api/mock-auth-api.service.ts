import { Injectable } from '@angular/core';
import { Observable, of, throwError } from 'rxjs';
import { delay } from 'rxjs/operators';
import { AuthApi, AuthResponse, User, ApiToken, MfaSetupData } from './auth-api';

interface MockUserRecord {
  user: User;
  passwordHash: string;
}

@Injectable({
  providedIn: 'root'
})
export class MockAuthApiService extends AuthApi {
  private usersMap = new Map<string, MockUserRecord>();
  private currentSessionUserId: string | null = null;

  private mockTokens: ApiToken[] = [
    {
      id: 'tok_001',
      name: 'CI/CD Pipeline Production',
      token_prefix: 'npm_a8f3',
      created_at: Date.now() - 86400000 * 10,
      expires_at: Date.now() + 86400000 * 20,
      last_used_at: Date.now() - 3600000 * 4
    }
  ];

  constructor() {
    super();
    this.initMockUsers();
  }

  private initMockUsers(): void {
    // Default demo user
    const defaultUser: User = {
      id: 'usr_ana_001',
      email: 'ana.martinez@empresa.com',
      name: 'Ana Martínez',
      role: 'Instructor',
      organization: 'Educación Corp',
      avatarLetter: 'A',
      isVerified: true,
      mfaEnabled: false,
      createdAt: Date.now() - 86400000 * 30
    };

    this.usersMap.set('ana.martinez@empresa.com', {
      user: defaultUser,
      passwordHash: 'Password123!'
    });

    // Load persisted users metadata (NO TOKENS) from localStorage
    try {
      if (typeof localStorage !== 'undefined') {
        const savedUsers = localStorage.getItem('nuevamente_mock_users');
        if (savedUsers) {
          const list: { user: User; passwordHash: string }[] = JSON.parse(savedUsers);
          if (Array.isArray(list)) {
            list.forEach(item => {
              if (item?.user?.email && item?.passwordHash) {
                this.usersMap.set(item.user.email.toLowerCase(), item);
              }
            });
          }
        }

        // Default to unauthenticated session so the Login screen is displayed on launch
        this.currentSessionUserId = null;
      }
    } catch (e) {
      console.warn('Error loading mock users from storage', e);
    }
  }

  private saveUsersToStorage(): void {
    try {
      if (typeof localStorage !== 'undefined') {
        const list = Array.from(this.usersMap.values());
        localStorage.setItem('nuevamente_mock_users', JSON.stringify(list));
      }
    } catch (e) {
      console.warn('Error saving mock users to storage', e);
    }
  }

  private setSessionUser(email: string | null): void {
    if (email && this.usersMap.has(email.toLowerCase())) {
      this.currentSessionUserId = this.usersMap.get(email.toLowerCase())!.user.id;
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('nuevamente_mock_session_email', email.toLowerCase());
      }
    } else {
      this.currentSessionUserId = null;
      if (typeof localStorage !== 'undefined') {
        localStorage.removeItem('nuevamente_mock_session_email');
      }
    }
  }

  login(email: string, password: string, mfaCode?: string): Observable<AuthResponse> {
    const cleanEmail = (email || '').trim().toLowerCase();
    const record = this.usersMap.get(cleanEmail);

    if (!record || record.passwordHash !== password) {
      return throwError(() => ({
        status: 401,
        error: { detail: 'Credenciales incorrectas' }
      })).pipe(delay(300));
    }

    this.setSessionUser(cleanEmail);

    return of({
      status: 'exito',
      message: `Bienvenido de nuevo, ${record.user.name}`,
      access_token: 'mock_jwt_access_token_' + Date.now(),
      token_type: 'bearer',
      expires_in: 900,
      user: record.user
    }).pipe(delay(300));
  }

  startOAuth(provider: string): Observable<AuthResponse> {
    return throwError(() => ({
      status: 501,
      error: {
        detail: 'OAUTH_NOT_CONFIGURED',
        code: 'OAUTH_NOT_CONFIGURED',
        message: 'La autenticación social no está configurada en el servidor.'
      }
    })).pipe(delay(200));
  }

  loginMfa(email: string, mfaCode: string, mfaToken?: string): Observable<AuthResponse> {
    return this.login(email, 'Password123!');
  }

  register(name: string, email: string, password: string, role?: string, organization?: string): Observable<AuthResponse> {
    const cleanEmail = (email || '').trim().toLowerCase();

    // Check duplicate
    if (this.usersMap.has(cleanEmail)) {
      return throwError(() => ({
        status: 400,
        error: { detail: 'El correo electrónico ya está registrado.' }
      })).pipe(delay(300));
    }

    // Password validation: >=8 chars, uppercase, number, symbol
    const isValidPassword = 
      password.length >= 8 &&
      /[A-Z]/.test(password) &&
      /[0-9]/.test(password) &&
      /[^A-Za-z0-9]/.test(password);

    if (!isValidPassword) {
      return throwError(() => ({
        status: 400,
        error: { detail: 'La contraseña debe tener al menos 8 caracteres, una mayúscula, un número y un símbolo.' }
      })).pipe(delay(300));
    }

    const newUser: User = {
      id: 'usr_' + Math.random().toString(36).substr(2, 6),
      email: cleanEmail,
      name: name,
      role: role || 'Instructor',
      organization: organization || 'Organización',
      avatarLetter: name.charAt(0).toUpperCase(),
      isVerified: true,
      mfaEnabled: false,
      createdAt: Date.now()
    };

    this.usersMap.set(cleanEmail, {
      user: newUser,
      passwordHash: password
    });

    this.saveUsersToStorage();
    this.setSessionUser(cleanEmail);

    return of({
      status: 'exito',
      message: 'Cuenta registrada exitosamente',
      access_token: 'mock_jwt_access_token_' + Date.now(),
      token_type: 'bearer',
      expires_in: 900,
      user: newUser
    }).pipe(delay(400));
  }

  verifyEmail(email: string, code: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Correo verificado' }).pipe(delay(300));
  }

  resendVerification(email: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Código reenviado' }).pipe(delay(300));
  }

  forgotPassword(email: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Si la cuenta existe, se ha enviado un enlace de recuperación.' }).pipe(delay(300));
  }

  resetPassword(token: string, newPassword: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Contraseña restablecida exitosamente.' }).pipe(delay(300));
  }

  changePassword(currentPassword: string, newPassword: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Contraseña actualizada' }).pipe(delay(300));
  }

  sendMagicLink(email: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Enlace mágico enviado a su correo.' }).pipe(delay(300));
  }

  verifyMagicLink(token: string): Observable<AuthResponse> {
    return this.login('ana.martinez@empresa.com', 'Password123!');
  }

  refreshToken(): Observable<AuthResponse> {
    if (!this.currentSessionUserId) {
      return throwError(() => ({
        status: 401,
        error: { detail: 'Unauthenticated' }
      })).pipe(delay(200));
    }

    const currentRecord = Array.from(this.usersMap.values()).find(r => r.user.id === this.currentSessionUserId);
    if (!currentRecord) {
      this.setSessionUser(null);
      return throwError(() => ({
        status: 401,
        error: { detail: 'Unauthenticated' }
      })).pipe(delay(200));
    }

    return of({
      status: 'exito',
      message: 'Sesión renovada',
      access_token: 'mock_jwt_access_token_refreshed_' + Date.now(),
      token_type: 'bearer',
      expires_in: 900,
      user: currentRecord.user
    }).pipe(delay(200));
  }

  logout(): Observable<{ status: string; message: string }> {
    this.setSessionUser(null);
    return of({ status: 'exito', message: 'Sesión cerrada' }).pipe(delay(150));
  }

  logoutAll(): Observable<{ status: string; message: string }> {
    this.setSessionUser(null);
    return of({ status: 'exito', message: 'Todas las sesiones cerradas' }).pipe(delay(200));
  }

  getMe(): Observable<User> {
    if (!this.currentSessionUserId) {
      return throwError(() => ({ status: 401, error: { detail: 'Unauthenticated' } }));
    }
    const currentRecord = Array.from(this.usersMap.values()).find(r => r.user.id === this.currentSessionUserId);
    if (!currentRecord) {
      return throwError(() => ({ status: 401, error: { detail: 'Unauthenticated' } }));
    }
    return of(currentRecord.user).pipe(delay(150));
  }

  setupMfa(): Observable<MfaSetupData> {
    return of({
      secret: 'JBSWY3DPEHPK3PXP',
      qr_svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="180" height="180"><rect width="200" height="200" fill="#ffffff"/><rect x="20" y="20" width="50" height="50" fill="#0f172a"/><rect x="130" y="20" width="50" height="50" fill="#0f172a"/><rect x="20" y="130" width="50" height="50" fill="#0f172a"/></svg>`,
      backup_codes: ['9A8F-3C2B', '4E7D-1F9A', '8C3B-2A1E', '5F6E-7D8C', '1A2B-3C4D', '5E6F-7A8B', '9C0D-1E2F', '3A4B-5C6D']
    }).pipe(delay(300));
  }

  enableMfa(code: string): Observable<{ status: string; message: string }> {
    return of({ status: 'exito', message: 'MFA Activado' }).pipe(delay(200));
  }

  disableMfa(password: string): Observable<{ status: string; message: string }> {
    return of({ status: 'exito', message: 'MFA Desactivado' }).pipe(delay(200));
  }

  getApiTokens(): Observable<ApiToken[]> {
    return of(this.mockTokens).pipe(delay(150));
  }

  createApiToken(name: string, expiresInDays: number): Observable<ApiToken> {
    const rawToken = 'npm_' + Array.from({length: 24}, () => Math.floor(Math.random()*16).toString(16)).join('');
    const newToken: ApiToken = {
      id: 'tok_' + Date.now(),
      name,
      token: rawToken,
      token_prefix: rawToken.substring(0, 8),
      created_at: Date.now(),
      expires_at: Date.now() + (expiresInDays * 86400000)
    };
    this.mockTokens.push(newToken);
    return of(newToken).pipe(delay(300));
  }

  deleteApiToken(tokenId: string): Observable<{ status: string; message: string }> {
    this.mockTokens = this.mockTokens.filter(t => t.id !== tokenId);
    return of({ status: 'exito', message: 'API Token revocado' }).pipe(delay(200));
  }
}
