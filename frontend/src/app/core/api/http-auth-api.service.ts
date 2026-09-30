import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthApi, AuthResponse, User, ApiToken, MfaSetupData } from './auth-api';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class HttpAuthApiService extends AuthApi {
  private baseUrl = `${environment.apiUrl || 'http://localhost:8000'}/api/v1/auth`;

  constructor(private http: HttpClient) {
    super();
  }

  login(email: string, password: string, mfaCode?: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/login`, { email, password, mfa_code: mfaCode }, { withCredentials: true });
  }

  startOAuth(provider: string): Observable<AuthResponse> {
    return this.http.get<AuthResponse>(`${this.baseUrl}/oauth/${provider.toLowerCase()}`);
  }

  loginMfa(email: string, mfaCode: string, mfaToken?: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/login/mfa`, { email, mfa_code: mfaCode, mfa_token: mfaToken }, { withCredentials: true });
  }

  register(name: string, email: string, password: string, role?: string, organization?: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/register`, { name, email, password, role, organization, terms_accepted: true }, { withCredentials: true });
  }

  verifyEmail(email: string, code: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/verify-email`, { email, code });
  }

  resendVerification(email: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/resend-verification`, { email });
  }

  forgotPassword(email: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/forgot-password`, { email });
  }

  resetPassword(token: string, newPassword: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/reset-password`, { token, new_password: newPassword });
  }

  changePassword(currentPassword: string, newPassword: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/change-password`, { current_password: currentPassword, new_password: newPassword });
  }

  sendMagicLink(email: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/magic-link`, { email });
  }

  verifyMagicLink(token: string): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/magic-link/verify`, { token }, { withCredentials: true });
  }

  refreshToken(): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.baseUrl}/refresh`, {}, { withCredentials: true });
  }

  logout(): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.baseUrl}/logout`, {}, { withCredentials: true });
  }

  logoutAll(): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.baseUrl}/logout-all`, {}, { withCredentials: true });
  }

  getMe(): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}/me`);
  }

  setupMfa(): Observable<MfaSetupData> {
    return this.http.post<MfaSetupData>(`${this.baseUrl}/mfa/setup`, {});
  }

  enableMfa(code: string): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.baseUrl}/mfa/enable`, { code });
  }

  disableMfa(password: string): Observable<{ status: string; message: string }> {
    return this.http.post<{ status: string; message: string }>(`${this.baseUrl}/mfa/disable`, { password });
  }

  getApiTokens(): Observable<ApiToken[]> {
    return this.http.get<ApiToken[]>(`${this.baseUrl}/api-tokens`);
  }

  createApiToken(name: string, expiresInDays: number): Observable<ApiToken> {
    return this.http.post<ApiToken>(`${this.baseUrl}/api-tokens`, { name, expires_in_days: expiresInDays });
  }

  deleteApiToken(tokenId: string): Observable<{ status: string; message: string }> {
    return this.http.delete<{ status: string; message: string }>(`${this.baseUrl}/api-tokens/${tokenId}`);
  }
}
