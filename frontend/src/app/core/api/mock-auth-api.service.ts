import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';
import { AuthApi, AuthResponse, User, ApiToken, MfaSetupData } from './auth-api';

@Injectable({
  providedIn: 'root'
})
export class MockAuthApiService extends AuthApi {
  private mockUser: User = {
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

  login(email: string, password: string, mfaCode?: string): Observable<AuthResponse> {
    const user: User = {
      id: 'usr_' + Math.random().toString(36).substr(2, 6),
      email: email,
      name: email.split('@')[0].replace('.', ' ').toUpperCase(),
      role: 'Instructor',
      avatarLetter: email[0].toUpperCase(),
      isVerified: true,
      mfaEnabled: false,
      createdAt: Date.now()
    };

    return of({
      status: 'exito',
      message: `Bienvenido de nuevo, ${user.name}`,
      access_token: 'mock_jwt_access_token_' + Date.now(),
      token_type: 'bearer',
      expires_in: 900,
      user
    }).pipe(delay(600));
  }

  loginMfa(email: string, mfaCode: string, mfaToken?: string): Observable<AuthResponse> {
    return this.login(email, 'password');
  }

  register(name: string, email: string, password: string, role?: string, organization?: string): Observable<AuthResponse> {
    const user: User = {
      id: 'usr_' + Math.random().toString(36).substr(2, 6),
      email: email,
      name: name,
      role: role || 'Instructor',
      organization: organization,
      avatarLetter: name[0].toUpperCase(),
      isVerified: true,
      mfaEnabled: false,
      createdAt: Date.now()
    };

    return of({
      status: 'exito',
      message: 'Cuenta registrada exitosamente',
      access_token: 'mock_jwt_access_token_' + Date.now(),
      token_type: 'bearer',
      expires_in: 900,
      user
    }).pipe(delay(700));
  }

  verifyEmail(email: string, code: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Correo verificado' }).pipe(delay(400));
  }

  resendVerification(email: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Código reenviado' }).pipe(delay(300));
  }

  forgotPassword(email: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Si la cuenta existe, se ha enviado un enlace de recuperación.' }).pipe(delay(500));
  }

  resetPassword(token: string, newPassword: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Contraseña restablecida exitosamente.' }).pipe(delay(600));
  }

  changePassword(currentPassword: string, newPassword: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Contraseña actualizada' }).pipe(delay(500));
  }

  sendMagicLink(email: string): Observable<AuthResponse> {
    return of({ status: 'exito', message: 'Enlace mágico enviado a su correo.' }).pipe(delay(800));
  }

  verifyMagicLink(token: string): Observable<AuthResponse> {
    return this.login('ana.martinez@empresa.com', 'pass');
  }

  refreshToken(): Observable<AuthResponse> {
    return of({
      status: 'exito',
      message: 'Sesión renovada',
      access_token: 'mock_jwt_access_token_refreshed_' + Date.now(),
      token_type: 'bearer',
      expires_in: 900,
      user: this.mockUser
    }).pipe(delay(300));
  }

  logout(): Observable<{ status: string; message: string }> {
    return of({ status: 'exito', message: 'Sesión cerrada' }).pipe(delay(200));
  }

  logoutAll(): Observable<{ status: string; message: string }> {
    return of({ status: 'exito', message: 'Todas las sesiones cerradas' }).pipe(delay(300));
  }

  getMe(): Observable<User> {
    return of(this.mockUser).pipe(delay(200));
  }

  setupMfa(): Observable<MfaSetupData> {
    return of({
      secret: 'JBSWY3DPEHPK3PXP',
      qr_svg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="180" height="180"><rect width="200" height="200" fill="#ffffff"/><rect x="20" y="20" width="50" height="50" fill="#0f172a"/><rect x="130" y="20" width="50" height="50" fill="#0f172a"/><rect x="20" y="130" width="50" height="50" fill="#0f172a"/></svg>`,
      backup_codes: ['9A8F-3C2B', '4E7D-1F9A', '8C3B-2A1E', '5F6E-7D8C', '1A2B-3C4D', '5E6F-7A8B', '9C0D-1E2F', '3A4B-5C6D']
    }).pipe(delay(400));
  }

  enableMfa(code: string): Observable<{ status: string; message: string }> {
    this.mockUser.mfaEnabled = true;
    return of({ status: 'exito', message: 'MFA Activado' }).pipe(delay(300));
  }

  disableMfa(password: string): Observable<{ status: string; message: string }> {
    this.mockUser.mfaEnabled = false;
    return of({ status: 'exito', message: 'MFA Desactivado' }).pipe(delay(300));
  }

  getApiTokens(): Observable<ApiToken[]> {
    return of(this.mockTokens).pipe(delay(200));
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
    return of(newToken).pipe(delay(400));
  }

  deleteApiToken(tokenId: string): Observable<{ status: string; message: string }> {
    this.mockTokens = this.mockTokens.filter(t => t.id !== tokenId);
    return of({ status: 'exito', message: 'API Token revocado' }).pipe(delay(300));
  }
}
