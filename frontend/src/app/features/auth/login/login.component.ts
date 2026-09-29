import { Component, EventEmitter, Output, signal, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { I18nService, Language } from '../../../core/services/i18n.service';
import { AuthStore } from '../../../core/store/auth.store';
import { environment } from '../../../../environments/environment';

export type AuthMode = 'login' | 'register' | 'forgot' | 'magic_link' | 'mfa';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="login-split-screen">
      <!-- LEFT BRAND PANEL (50%) -->
      <div class="brand-panel">
        <div class="aurora-mesh"></div>
        <div class="grain-overlay"></div>
        
        <div class="brand-content">
          <!-- Logo Header -->
          <div class="brand-logo">
            <svg class="logo-icon" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M20 4L4 12L20 20L36 12L20 4Z" fill="url(#logo-grad-1)"/>
              <path d="M4 12V24L20 32V20L4 12Z" fill="url(#logo-grad-2)" fill-opacity="0.8"/>
              <path d="M36 12V24L20 32V20L36 12Z" fill="url(#logo-grad-3)" fill-opacity="0.9"/>
              <circle cx="20" cy="4" r="3" fill="#22D3EE"/>
              <circle cx="4" cy="12" r="3" fill="#6366F1"/>
              <circle cx="36" cy="12" r="3" fill="#A855F7"/>
              <circle cx="20" cy="32" r="3.5" fill="#22D3EE"/>
              <defs>
                <linearGradient id="logo-grad-1" x1="4" y1="4" x2="36" y2="20" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#4F46E5"/>
                  <stop offset="1" stop-color="#7C3AED"/>
                </linearGradient>
                <linearGradient id="logo-grad-2" x1="4" y1="12" x2="20" y2="32" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#6366F1"/>
                  <stop offset="1" stop-color="#22D3EE"/>
                </linearGradient>
                <linearGradient id="logo-grad-3" x1="36" y1="12" x2="20" y2="32" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#7C3AED"/>
                  <stop offset="1" stop-color="#4F46E5"/>
                </linearGradient>
              </defs>
            </svg>
            <span class="logo-text">NuevaMente</span>
          </div>

          <!-- Main Headlines -->
          <div class="text-block">
            <h1 class="accessible-title">Bienvenido de nuevo</h1>
            <p class="subtitle">
              De semanas de trabajo instruccional a minutos, con fidelidad total a la fuente original y anclaje RAG verificable.
            </p>
          </div>

          <!-- Floating Feature Badges (Lucide SVG Icons) -->
          <div class="floating-chips">
            <!-- RAG Chip (quote / file-search SVG) -->
            <span class="chip-item">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><circle cx="11.5" cy="14.5" r="2.5"/><path d="M13.25 16.25L15 18"/></svg>
              RAG con fuentes citadas
            </span>
            <!-- Perfiles Chip (users SVG) -->
            <span class="chip-item">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
              4 perfiles técnicos
            </span>
            <!-- Formatos Chip (layout-grid SVG) -->
            <span class="chip-item">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              5 formatos pedagógicos
            </span>
          </div>

          <!-- ANIMATED PIPELINE SVG -->
          <div class="pipeline-svg-container" [class.paused]="isAnimationPaused()">
            <button class="btn-pause-anim" (click)="toggleAnimation()">
              {{ isAnimationPaused() ? '▶ Reanudar' : '⏸ Pausar' }}
            </button>
            <svg viewBox="0 0 500 140" fill="none" class="pipeline-svg">
              <g class="svg-node doc-node">
                <rect x="20" y="35" width="70" height="70" rx="10" fill="rgba(255,255,255,0.08)" stroke="#6366F1" stroke-width="2"/>
                <path d="M35 50h40M35 65h30M35 80h20" stroke="#E0E7FF" stroke-width="2" stroke-linecap="round"/>
                <text x="55" y="122" text-anchor="middle" fill="#94A3B8" font-size="11" font-weight="600">Documento</text>
              </g>
              <path d="M95 70 H145" stroke="url(#flow1)" stroke-width="2" stroke-dasharray="4 4" class="animated-path"/>
              <g class="svg-node chunk-node">
                <rect x="150" y="45" width="50" height="50" rx="8" fill="rgba(34, 211, 238, 0.1)" stroke="#22D3EE" stroke-width="2"/>
                <circle cx="175" cy="70" r="10" stroke="#22D3EE" stroke-width="2"/>
                <text x="175" y="122" text-anchor="middle" fill="#94A3B8" font-size="11" font-weight="600">Chunking</text>
              </g>
              <path d="M205 70 H255" stroke="url(#flow2)" stroke-width="2" stroke-dasharray="4 4" class="animated-path"/>
              <g class="svg-node vector-node">
                <circle cx="290" cy="70" r="30" fill="rgba(124, 58, 237, 0.15)" stroke="#7C3AED" stroke-width="2"/>
                <circle cx="280" cy="65" r="4" fill="#22D3EE"/>
                <circle cx="298" cy="62" r="3" fill="#EC4899"/>
                <circle cx="290" cy="82" r="4" fill="#10B981"/>
                <text x="290" y="122" text-anchor="middle" fill="#94A3B8" font-size="11" font-weight="600">Vector Store</text>
              </g>
              <path d="M325 70 H375" stroke="url(#flow3)" stroke-width="2" stroke-dasharray="4 4" class="animated-path"/>
              <g class="svg-node card-node">
                <rect x="380" y="35" width="80" height="70" rx="10" fill="rgba(16, 185, 129, 0.15)" stroke="#10B981" stroke-width="2"/>
                <rect x="390" y="45" width="30" height="20" rx="4" fill="#EC4899"/>
                <rect x="425" y="45" width="25" height="20" rx="4" fill="#8B5CF6"/>
                <rect x="390" y="72" width="60" height="22" rx="4" fill="#3B82F6"/>
                <text x="420" y="122" text-anchor="middle" fill="#94A3B8" font-size="11" font-weight="600">Tarjetas IA</text>
              </g>
              <defs>
                <linearGradient id="flow1" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#6366F1"/><stop offset="100%" stop-color="#22D3EE"/></linearGradient>
                <linearGradient id="flow2" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#22D3EE"/><stop offset="100%" stop-color="#7C3AED"/></linearGradient>
                <linearGradient id="flow3" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#7C3AED"/><stop offset="100%" stop-color="#10B981"/></linearGradient>
              </defs>
            </svg>
          </div>

          <div class="brand-footer">
            <span class="oracle-tag">Powered by Oracle Cloud Infrastructure · ONE × Alura</span>
          </div>
        </div>
      </div>

      <!-- RIGHT FORM PANEL (50%) -->
      <div class="form-panel">
        <div class="top-controls">
          <div class="lang-selector">
            <button [class.active]="i18n.currentLang() === 'es'" (click)="setLang('es')">ES</button>
            <button [class.active]="i18n.currentLang() === 'en'" (click)="setLang('en')">EN</button>
            <button [class.active]="i18n.currentLang() === 'pt'" (click)="setLang('pt')">PT</button>
          </div>
        </div>

        <div class="glass-card auth-card">
          <!-- Auth Mode Navigation Tabs -->
          <div class="mode-tabs">
            <button class="tab-btn" [class.active]="mode() === 'login'" (click)="setMode('login')">Iniciar Sesión</button>
            <button class="tab-btn" [class.active]="mode() === 'register'" (click)="setMode('register')">Crear Cuenta</button>
            <button class="tab-btn" [class.active]="mode() === 'magic_link'" (click)="setMode('magic_link')">Magic Link</button>
          </div>

          <!-- DEMO QUICK-LOGIN BANNER (Shown ONLY if enableDemoLogin === true) -->
          <div class="demo-banner" *ngIf="showDemoLoginBanner" (click)="fillDemoCredentials()">
            <div class="demo-badge">DEMO QUICK-LOGIN</div>
            <div class="demo-info">
              <span><code>ana.martinez&#64;empresa.com</code> / <code>password123</code></span>
              <span class="demo-click-hint">⚡ Clic para autocompletar</span>
            </div>
          </div>

          <!-- Error Alert Banner -->
          <div class="alert-banner error-banner" *ngIf="authStore.error()">
            ⚠️ {{ authStore.error() }}
          </div>

          <!-- MODE 1: LOGIN FORM -->
          <div *ngIf="mode() === 'login'">
            <!-- SSO Providers -->
            <div class="sso-buttons">
              <button type="button" class="sso-btn" (click)="loginSso('Google')">
                <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#EA4335" d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.4 1 3.5 3.6 1.6 7.4l3.7 2.9C6.2 7.3 8.9 5 12 5z"/><path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.5h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.8z"/><path fill="#FBBC05" d="M5.3 14.8c-.2-.7-.4-1.5-.4-2.3s.2-1.6.4-2.3L1.6 7.4C.6 9.4 0 10.6 0 12s.6 2.6 1.6 4.6l3.7-2.8z"/><path fill="#34A853" d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3.1 0-5.8-2.3-6.7-5.3L1.6 16C3.5 19.8 7.4 23 12 23z"/></svg>
                Google
              </button>
              <button type="button" class="sso-btn" (click)="loginSso('GitHub')">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
                GitHub
              </button>
            </div>

            <div class="divider"><span>o continua con email</span></div>

            <form [formGroup]="loginForm" (ngSubmit)="onLoginSubmit()">
              <div class="form-group">
                <label for="login-email">Correo electrónico</label>
                <input id="login-email" type="email" formControlName="email" placeholder="nombre&#64;empresa.com"/>
              </div>

              <div class="form-group">
                <div class="label-row">
                  <label for="login-password">Contraseña</label>
                  <a href="javascript:void(0)" class="forgot-link" (click)="setMode('forgot')">¿Olvidaste tu contraseña?</a>
                </div>
                <div class="password-input-wrapper">
                  <input 
                    id="login-password" 
                    [type]="showPassword() ? 'text' : 'password'" 
                    formControlName="password" 
                    placeholder="••••••••"
                    (keyup)="checkCapsLock($event)"
                  />
                  <button type="button" class="btn-toggle-pw" (click)="togglePasswordVisibility()">
                    {{ showPassword() ? '👁️' : '🔒' }}
                  </button>
                </div>
                <div class="caps-lock-warning" *ngIf="isCapsLockOn()">⚠️ Bloq Mayús activado</div>
              </div>

              <button type="submit" class="btn-primary-submit" [disabled]="loginForm.invalid || authStore.isLoading()">
                <span *ngIf="!authStore.isLoading()">Iniciar Sesión →</span>
                <span *ngIf="authStore.isLoading()">Autenticando...</span>
              </button>
            </form>
          </div>

          <!-- MODE 2: REGISTER FORM -->
          <div *ngIf="mode() === 'register'">
            <form [formGroup]="registerForm" (ngSubmit)="onRegisterSubmit()">
              <div class="form-group">
                <label for="reg-name">Nombre completo</label>
                <input id="reg-name" type="text" formControlName="name" placeholder="Ej: Ana Martínez"/>
              </div>

              <div class="form-group">
                <label for="reg-email">Correo electrónico profesional</label>
                <input id="reg-email" type="email" formControlName="email" placeholder="nombre&#64;empresa.com"/>
              </div>

              <div class="form-group">
                <label for="reg-password">Contraseña</label>
                <div class="password-input-wrapper">
                  <input id="reg-password" [type]="showPassword() ? 'text' : 'password'" formControlName="password" (input)="evaluatePasswordStrength()" placeholder="Mínimo 6 caracteres"/>
                  <button type="button" class="btn-toggle-pw" (click)="togglePasswordVisibility()">
                    {{ showPassword() ? '👁️' : '🔒' }}
                  </button>
                </div>

                <!-- Password Strength Meter -->
                <div class="strength-meter-box" *ngIf="registerForm.get('password')?.value">
                  <div class="strength-bar-track">
                    <div class="strength-bar-fill" [style.width.%]="strengthScore() * 25" [ngClass]="strengthClass()"></div>
                  </div>
                  <span class="strength-label">Fortaleza: <strong>{{ strengthText() }}</strong></span>
                </div>
              </div>

              <div class="form-group">
                <label for="reg-role">Perfil / Rol (opcional)</label>
                <select id="reg-role" formControlName="role">
                  <option value="Instructor">Instructor / Diseñador Instruccional</option>
                  <option value="Dev">Desarrollador / Dev Lead</option>
                  <option value="Leader">Líder Técnico / Manager</option>
                  <option value="Otro">Otro</option>
                </select>
              </div>

              <div class="form-options">
                <label class="checkbox-label">
                  <input type="checkbox" formControlName="terms"/>
                  <span>Acepto los Términos y Política de Privacidad</span>
                </label>
              </div>

              <button type="submit" class="btn-primary-submit" [disabled]="registerForm.invalid || authStore.isLoading()">
                <span *ngIf="!authStore.isLoading()">Crear Cuenta Gratis →</span>
                <span *ngIf="authStore.isLoading()">Registrando...</span>
              </button>
            </form>
          </div>

          <!-- MODE 3: MAGIC LINK FORM -->
          <div *ngIf="mode() === 'magic_link'">
            <div class="info-box">
              <p>Te enviaremos un enlace de acceso instantáneo a tu correo electrónico sin contraseña.</p>
            </div>
            <form [formGroup]="magicLinkForm" (ngSubmit)="onMagicLinkSubmit()">
              <div class="form-group">
                <label for="magic-email">Correo electrónico</label>
                <input id="magic-email" type="email" formControlName="email" placeholder="nombre&#64;empresa.com"/>
              </div>

              <button type="submit" class="btn-primary-submit" [disabled]="magicLinkForm.invalid || isSendingMagicLink()">
                <span *ngIf="!isSendingMagicLink()">✨ Enviar enlace de acceso</span>
                <span *ngIf="isSendingMagicLink()">Enviando enlace...</span>
              </button>
            </form>
            <div class="success-banner" *ngIf="magicLinkSent()">
              ✅ ¡Enlace enviado! Revisa tu bandeja de entrada.
            </div>
          </div>

          <!-- MODE 4: FORGOT PASSWORD (USER ENUMERATION DEFENSE) -->
          <div *ngIf="mode() === 'forgot'">
            <div class="info-box">
              <p>Ingresa tu correo para recibir instrucciones de recuperación.</p>
            </div>
            <form [formGroup]="forgotForm" (ngSubmit)="onForgotSubmit()">
              <div class="form-group">
                <label for="forgot-email">Correo electrónico</label>
                <input id="forgot-email" type="email" formControlName="email" placeholder="nombre&#64;empresa.com"/>
              </div>

              <button type="submit" class="btn-primary-submit" [disabled]="forgotForm.invalid || isSubmittingForgot()">
                <span>Recuperar Contraseña →</span>
              </button>
            </form>
            <div class="success-banner" *ngIf="forgotSubmitted()">
              📩 Si la cuenta existe, hemos enviado un correo con las instrucciones.
            </div>
            <a href="javascript:void(0)" class="back-link" (click)="setMode('login')">← Volver al login</a>
          </div>

          <!-- MODE 5: MFA PROMPT -->
          <div *ngIf="mode() === 'mfa'">
            <div class="info-box">
              <p>Tu cuenta tiene activada la Autenticación de Dos Factores. Ingresa el código de 6 dígitos de tu aplicación TOTP.</p>
            </div>
            <form [formGroup]="mfaForm" (ngSubmit)="onMfaSubmit()">
              <div class="form-group">
                <label for="mfa-code">Código TOTP de 6 dígitos</label>
                <input id="mfa-code" type="text" formControlName="code" placeholder="123456" maxlength="6" class="mfa-code-input"/>
              </div>

              <button type="submit" class="btn-primary-submit" [disabled]="mfaForm.invalid || authStore.isLoading()">
                <span>Verificar y Entrar →</span>
              </button>
            </form>
          </div>

          <div class="security-badge-footer">
            🔒 Procesamiento de datos de alta seguridad en OCI Always Free
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .login-split-screen {
      display: flex;
      min-height: 100vh;
      background: #090D16;
      color: #F8FAFC;
    }

    .brand-panel {
      flex: 1;
      position: relative;
      background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 50%, #090D16 100%);
      padding: 4rem 3rem;
      display: flex;
      flex-direction: column;
      justify-content: center;
      overflow: hidden;
    }

    .aurora-mesh {
      position: absolute;
      top: -20%; left: -20%; width: 140%; height: 140%;
      background: radial-gradient(circle at 30% 30%, rgba(79, 70, 229, 0.25), transparent 50%),
                  radial-gradient(circle at 70% 70%, rgba(34, 211, 238, 0.2), transparent 50%);
      filter: blur(60px);
      pointer-events: none;
    }

    .grain-overlay {
      position: absolute; inset: 0;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.03'/%3E%3C/svg%3E");
      pointer-events: none;
    }

    .brand-content {
      position: relative; z-index: 10; max-width: 580px; margin: 0 auto;
    }

    .brand-logo {
      display: flex; align-items: center; gap: 0.85rem; margin-bottom: 2rem;
    }
    .logo-icon { width: 44px; height: 44px; }
    .logo-text { font-size: 1.85rem; font-weight: 800; color: #FFFFFF; }

    /* ACCESSIBLE HIGH-CONTRAST TITLE FIX */
    .accessible-title {
      font-size: 2.5rem;
      font-weight: 800;
      color: #FFFFFF !important;
      line-height: 1.2;
      margin-bottom: 1rem;
      text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5);
    }

    .subtitle {
      font-size: 1.05rem; color: #CBD5E1; line-height: 1.6; margin-bottom: 2rem;
    }

    .floating-chips {
      display: flex; flex-wrap: wrap; gap: 0.75rem; margin-bottom: 2rem;
    }
    .chip-item {
      display: inline-flex; align-items: center; gap: 0.5rem;
      padding: 0.5rem 1rem; border-radius: 20px;
      background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15);
      font-size: 0.88rem; color: #F1F5F9; backdrop-filter: blur(8px);
    }

    .pipeline-svg-container {
      position: relative; background: rgba(15, 23, 42, 0.6);
      border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px;
      padding: 1rem; margin-bottom: 2rem;
    }
    .btn-pause-anim {
      position: absolute; top: 10px; right: 12px;
      background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);
      color: #CBD5E1; font-size: 0.75rem; padding: 0.25rem 0.6rem; border-radius: 6px; cursor: pointer;
    }
    .pipeline-svg { width: 100%; height: auto; }
    .animated-path { animation: dashOffset 3s linear infinite; }
    .pipeline-svg-container.paused .animated-path { animation-play-state: paused; }
    @keyframes dashOffset { to { stroke-dashoffset: -24; } }

    .brand-footer { border-top: 1px solid rgba(255, 255, 255, 0.1); padding-top: 1rem; }
    .oracle-tag { font-size: 0.85rem; color: #94A3B8; font-weight: 600; }

    .form-panel {
      flex: 1; display: flex; flex-direction: column; justify-content: center;
      align-items: center; padding: 3rem 2rem; background: #090D16; position: relative;
    }
    .top-controls { position: absolute; top: 2rem; right: 2rem; }
    .lang-selector {
      display: flex; gap: 0.25rem; background: rgba(255, 255, 255, 0.05); padding: 0.25rem;
      border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .lang-selector button {
      background: transparent; border: none; color: #94A3B8; padding: 0.25rem 0.6rem;
      border-radius: 6px; font-size: 0.8rem; font-weight: 600; cursor: pointer;
    }
    .lang-selector button.active { background: #6366F1; color: #FFFFFF; }

    .auth-card {
      width: 100%; max-width: 440px; padding: 2.25rem;
      background: rgba(17, 24, 39, 0.9); border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 20px; box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
    }

    .mode-tabs {
      display: flex; gap: 0.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      margin-bottom: 1.5rem; padding-bottom: 0.5rem;
    }
    .tab-btn {
      background: transparent; border: none; color: #94A3B8; font-size: 0.9rem;
      font-weight: 600; padding: 0.5rem 0.75rem; cursor: pointer; border-radius: 6px;
    }
    .tab-btn.active { color: #FFFFFF; background: rgba(99, 102, 241, 0.2); }

    .demo-banner {
      background: linear-gradient(135deg, rgba(79, 70, 229, 0.2) 0%, rgba(34, 211, 238, 0.15) 100%);
      border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 10px;
      padding: 0.75rem 1rem; margin-bottom: 1.25rem; cursor: pointer;
    }
    .demo-badge { font-size: 0.7rem; font-weight: 800; color: #22D3EE; margin-bottom: 0.2rem; }
    .demo-info { display: flex; justify-content: space-between; font-size: 0.85rem; }
    .demo-info code { background: rgba(0, 0, 0, 0.3); padding: 0.1rem 0.4rem; border-radius: 4px; color: #E0E7FF; }

    .sso-buttons { display: flex; gap: 0.75rem; margin-bottom: 1.25rem; }
    .sso-btn {
      flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.5rem;
      padding: 0.65rem; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px; color: #F8FAFC; font-size: 0.88rem; font-weight: 600; cursor: pointer;
    }

    .divider { display: flex; align-items: center; margin: 1.25rem 0; color: #64748B; font-size: 0.8rem; }
    .divider::before, .divider::after { content: ''; flex: 1; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
    .divider span { padding: 0 0.75rem; }

    .form-group { margin-bottom: 1.25rem; }
    .form-group label { display: block; font-size: 0.85rem; font-weight: 600; color: #CBD5E1; margin-bottom: 0.4rem; }
    .label-row { display: flex; justify-content: space-between; align-items: center; }
    .forgot-link { font-size: 0.8rem; color: #818CF8; text-decoration: none; }

    input[type="email"], input[type="password"], input[type="text"], select {
      width: 100%; padding: 0.75rem 1rem; background: rgba(15, 23, 42, 0.8);
      border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 10px;
      color: #FFFFFF; font-size: 0.95rem; outline: none;
    }
    .mfa-code-input { font-size: 1.5rem; letter-spacing: 0.3em; text-align: center; font-weight: 700; }

    .password-input-wrapper { position: relative; }
    .btn-toggle-pw { position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: transparent; border: none; cursor: pointer; }
    .caps-lock-warning { margin-top: 0.35rem; font-size: 0.8rem; color: #F59E0B; }

    .strength-meter-box { margin-top: 0.5rem; }
    .strength-bar-track { height: 6px; background: rgba(255, 255, 255, 0.1); border-radius: 3px; overflow: hidden; margin-bottom: 0.3rem; }
    .strength-bar-fill { height: 100%; transition: width 0.3s; }
    .strength-weak { background: #EF4444; }
    .strength-medium { background: #F59E0B; }
    .strength-strong { background: #10B981; }
    .strength-awesome { background: #6366F1; }
    .strength-label { font-size: 0.78rem; color: #94A3B8; }

    .checkbox-label { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: #94A3B8; cursor: pointer; }

    .btn-primary-submit {
      width: 100%; padding: 0.85rem; background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
      border: none; border-radius: 10px; color: #FFFFFF; font-size: 1rem; font-weight: 700; cursor: pointer;
    }
    .btn-primary-submit:hover:not(:disabled) { box-shadow: 0 8px 20px rgba(79, 70, 229, 0.4); }
    .btn-primary-submit:disabled { opacity: 0.5; cursor: not-allowed; }

    .alert-banner { padding: 0.75rem 1rem; border-radius: 8px; font-size: 0.85rem; margin-bottom: 1.25rem; }
    .error-banner { background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); color: #FCA5A5; }
    .success-banner { background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.3); color: #6EE7B7; padding: 0.75rem; border-radius: 8px; margin-top: 1rem; font-size: 0.85rem; }

    .info-box { background: rgba(255, 255, 255, 0.05); padding: 0.75rem; border-radius: 8px; margin-bottom: 1.25rem; font-size: 0.88rem; color: #CBD5E1; }
    .back-link { display: block; margin-top: 1rem; text-align: center; color: #818CF8; font-size: 0.85rem; text-decoration: none; }
    .security-badge-footer { margin-top: 1.5rem; text-align: center; font-size: 0.78rem; color: #64748B; }

    @media (max-width: 960px) {
      .login-split-screen { flex-direction: column; }
      .brand-panel { padding: 3rem 1.5rem; }
      .form-panel { padding: 2rem 1.5rem; }
    }
  `]
})
export class LoginComponent implements OnInit {
  @Output() loginSuccess = new EventEmitter<{ email: string; name: string; token?: string }>();

  readonly i18n = inject(I18nService);
  readonly authStore = inject(AuthStore);
  private fb = inject(FormBuilder);

  showDemoLoginBanner = environment.enableDemoLogin;

  mode = signal<AuthMode>('login');
  showPassword = signal<boolean>(false);
  isCapsLockOn = signal<boolean>(false);
  isAnimationPaused = signal<boolean>(false);

  // Magic Link & Forgot states
  isSendingMagicLink = signal<boolean>(false);
  magicLinkSent = signal<boolean>(false);
  isSubmittingForgot = signal<boolean>(false);
  forgotSubmitted = signal<boolean>(false);

  // Password strength
  strengthScore = signal<number>(0);
  strengthClass = signal<string>('strength-weak');
  strengthText = signal<string>('Débil');

  loginForm = this.fb.group({
    email: ['ana.martinez@empresa.com', [Validators.required, Validators.email]],
    password: ['password123', [Validators.required, Validators.minLength(6)]]
  });

  registerForm = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    role: ['Instructor'],
    terms: [true, Validators.requiredTrue]
  });

  magicLinkForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]]
  });

  forgotForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]]
  });

  mfaForm = this.fb.group({
    code: ['', [Validators.required, Validators.minLength(6), Validators.maxLength(6)]]
  });

  ngOnInit() {
    if (this.authStore.isMfaRequired()) {
      this.mode.set('mfa');
    }
  }

  setMode(newMode: AuthMode): void {
    this.mode.set(newMode);
    this.authStore.error.set(null);
  }

  setLang(lang: Language): void {
    this.i18n.setLanguage(lang);
  }

  togglePasswordVisibility(): void {
    this.showPassword.update(v => !v);
  }

  checkCapsLock(event: KeyboardEvent): void {
    this.isCapsLockOn.set(event.getModifierState && event.getModifierState('CapsLock'));
  }

  toggleAnimation(): void {
    this.isAnimationPaused.update(v => !v);
  }

  fillDemoCredentials(): void {
    this.loginForm.patchValue({
      email: 'ana.martinez@empresa.com',
      password: 'password123'
    });
  }

  evaluatePasswordStrength(): void {
    const pw = this.registerForm.get('password')?.value || '';
    let score = 0;
    if (pw.length >= 6) score++;
    if (pw.length >= 10) score++;
    if (/[A-Z]/.test(pw) && /[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;

    this.strengthScore.set(score);
    if (score <= 1) {
      this.strengthClass.set('strength-weak');
      this.strengthText.set('Débil');
    } else if (score === 2) {
      this.strengthClass.set('strength-medium');
      this.strengthText.set('Media');
    } else if (score === 3) {
      this.strengthClass.set('strength-strong');
      this.strengthText.set('Fuerte');
    } else {
      this.strengthClass.set('strength-awesome');
      this.strengthText.set('Excelente');
    }
  }

  loginSso(provider: string): void {
    this.authStore.login(`usuario.${provider.toLowerCase()}@empresa.com`, 'password123');
  }

  onLoginSubmit(): void {
    if (this.loginForm.invalid) return;
    const { email, password } = this.loginForm.value;
    this.authStore.login(email!, password!);
  }

  onRegisterSubmit(): void {
    if (this.registerForm.invalid) return;
    const { name, email, password, role } = this.registerForm.value;
    this.authStore.register(name!, email!, password!, role!);
  }

  onMagicLinkSubmit(): void {
    if (this.magicLinkForm.invalid) return;
    this.isSendingMagicLink.set(true);
    this.authStore.getAuthApi().sendMagicLink(this.magicLinkForm.get('email')?.value!).subscribe({
      next: () => {
        this.isSendingMagicLink.set(false);
        this.magicLinkSent.set(true);
      },
      error: () => this.isSendingMagicLink.set(false)
    });
  }

  onForgotSubmit(): void {
    if (this.forgotForm.invalid) return;
    this.isSubmittingForgot.set(true);
    this.authStore.getAuthApi().forgotPassword(this.forgotForm.get('email')?.value!).subscribe({
      next: () => {
        this.isSubmittingForgot.set(false);
        this.forgotSubmitted.set(true);
      },
      error: () => this.isSubmittingForgot.set(false)
    });
  }

  onMfaSubmit(): void {
    if (this.mfaForm.invalid) return;
    this.authStore.loginMfa(this.mfaForm.get('code')?.value!);
  }
}
