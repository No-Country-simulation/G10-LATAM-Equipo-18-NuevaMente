import { Observable } from 'rxjs';

export interface User {
  id: string;
  email: string;
  name: string;
  role?: string;
  organization?: string;
  avatarLetter?: string;
  isVerified?: boolean;
  mfaEnabled?: boolean;
  createdAt?: number;
}

export interface AuthResponse {
  status: string;
  message: string;
  access_token?: string;
  token_type?: string;
  expires_in?: number;
  requires_mfa?: boolean;
  mfa_token?: string;
  user?: User;
}

export interface ApiToken {
  id: string;
  name: string;
  token?: string;
  token_prefix: string;
  created_at: number;
  expires_at?: number;
  last_used_at?: number;
}

export interface MfaSetupData {
  secret: string;
  qr_svg: string;
  backup_codes: string[];
}

export abstract class AuthApi {
  abstract login(email: string, password: string, mfaCode?: string): Observable<AuthResponse>;
  abstract loginMfa(email: string, mfaCode: string, mfaToken?: string): Observable<AuthResponse>;
  abstract register(name: string, email: string, password: string, role?: string, organization?: string): Observable<AuthResponse>;
  abstract verifyEmail(email: string, code: string): Observable<AuthResponse>;
  abstract resendVerification(email: string): Observable<AuthResponse>;
  abstract forgotPassword(email: string): Observable<AuthResponse>;
  abstract resetPassword(token: string, newPassword: string): Observable<AuthResponse>;
  abstract changePassword(currentPassword: string, newPassword: string): Observable<AuthResponse>;
  abstract sendMagicLink(email: string): Observable<AuthResponse>;
  abstract verifyMagicLink(token: string): Observable<AuthResponse>;
  abstract refreshToken(): Observable<AuthResponse>;
  abstract logout(): Observable<{ status: string; message: string }>;
  abstract logoutAll(): Observable<{ status: string; message: string }>;
  abstract getMe(): Observable<User>;
  abstract setupMfa(): Observable<MfaSetupData>;
  abstract enableMfa(code: string): Observable<{ status: string; message: string }>;
  abstract disableMfa(password: string): Observable<{ status: string; message: string }>;
  abstract getApiTokens(): Observable<ApiToken[]>;
  abstract createApiToken(name: string, expiresInDays: number): Observable<ApiToken>;
  abstract deleteApiToken(tokenId: string): Observable<{ status: string; message: string }>;
}
