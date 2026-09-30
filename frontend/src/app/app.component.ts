import { Component, OnInit, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { ThemeService } from './core/services/theme.service';
import { I18nService } from './core/services/i18n.service';
import { AuthStore } from './core/store/auth.store';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    RouterOutlet,
    RouterLink,
    RouterLinkActive
  ],
  template: `
    <!-- UNAUTHENTICATED PUBLIC ROUTER OUTLET (Login / Register / Recover Pages) -->
    <div *ngIf="!authStore.isAuthenticated()">
      <router-outlet></router-outlet>
    </div>

    <!-- AUTHENTICATED WORKSPACE SHELL (Sidebar + Header + Protected Content Router Outlet) -->
    <div *ngIf="authStore.isAuthenticated()" class="app-shell-layout">
      <!-- Left Sidebar Navigation -->
      <aside class="sidebar-shell" [class.collapsed]="isSidebarCollapsed()">
        <div class="sidebar-brand" routerLink="/workspace">
          <svg class="brand-isotype" viewBox="0 0 40 40" fill="none">
            <path d="M20 4L4 12L20 20L36 12L20 4Z" fill="url(#brand-grad-1)"/>
            <path d="M4 12V24L20 32V20L4 12Z" fill="url(#brand-grad-2)"/>
            <path d="M36 12V24L20 32V20L36 12Z" fill="url(#brand-grad-3)"/>
            <defs>
              <linearGradient id="brand-grad-1" x1="4" y1="4" x2="36" y2="20"><stop stop-color="#4F46E5"/><stop offset="1" stop-color="#7C3AED"/></linearGradient>
              <linearGradient id="brand-grad-2" x1="4" y1="12" x2="20" y2="32"><stop stop-color="#6366F1"/><stop offset="1" stop-color="#22D3EE"/></linearGradient>
              <linearGradient id="brand-grad-3" x1="36" y1="12" x2="20" y2="32"><stop stop-color="#7C3AED"/><stop offset="1" stop-color="#4F46E5"/></linearGradient>
            </defs>
          </svg>
          <span class="brand-title" *ngIf="!isSidebarCollapsed()">NuevaMente</span>
        </div>

        <!-- Nav Items -->
        <nav class="sidebar-nav">
          <a 
            routerLink="/workspace" 
            routerLinkActive="active" 
            class="nav-btn"
          >
            <span class="nav-icon">⚡</span>
            <span class="nav-text" *ngIf="!isSidebarCollapsed()">Workspace</span>
          </a>

          <a 
            routerLink="/library" 
            routerLinkActive="active" 
            class="nav-btn"
          >
            <span class="nav-icon">📚</span>
            <span class="nav-text" *ngIf="!isSidebarCollapsed()">Biblioteca</span>
          </a>
        </nav>

        <!-- Sidebar Footer (User Profile & Theme Toggle) -->
        <div class="sidebar-footer">
          <!-- Theme Toggle -->
          <button class="nav-btn theme-toggle-btn" (click)="themeService.toggleTheme()">
            <span class="nav-icon">{{ themeService.theme() === 'dark' ? '☀️' : '🌙' }}</span>
            <span class="nav-text" *ngIf="!isSidebarCollapsed()">
              Modo {{ themeService.theme() === 'dark' ? 'Claro' : 'Oscuro' }}
            </span>
          </button>

          <!-- User Badge & Logout -->
          <div class="user-badge-row" *ngIf="!isSidebarCollapsed() && authStore.user()">
            <div class="user-avatar">{{ authStore.user()?.avatarLetter || 'U' }}</div>
            <div class="user-info">
              <span class="u-name">{{ authStore.user()?.name }}</span>
              <span class="u-role">{{ authStore.user()?.role || 'Instructor' }}</span>
            </div>
          </div>

          <button class="nav-btn logout-btn" (click)="logout()">
            <span class="nav-icon">🚪</span>
            <span class="nav-text" *ngIf="!isSidebarCollapsed()">Cerrar Sesión</span>
          </button>
        </div>
      </aside>

      <!-- Main Content Area with Protected Router Outlet -->
      <main class="main-content-area">
        <router-outlet></router-outlet>
      </main>

      <!-- FLOATING SESSION EXPIRED MODAL -->
      <div class="session-modal-overlay" *ngIf="authStore.showSessionExpiredModal()">
        <div class="session-modal-card">
          <h3>⚠️ Tu sesión ha expirado</h3>
          <p>Para proteger tus cambios en edición, reingresa a tu cuenta sin perder el avance de tu trabajo.</p>
          <button class="btn-primary-modal" (click)="authStore.logout()">Re-iniciar sesión</button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .app-shell-layout {
      display: flex;
      min-height: 100vh;
      background: var(--bg-app);
      color: var(--text-primary);
    }

    .sidebar-shell {
      width: 250px;
      background: var(--bg-surface);
      border-right: 1px solid var(--border-subtle);
      padding: 1.5rem 1rem;
      display: flex;
      flex-direction: column;
      position: fixed;
      top: 0; bottom: 0; left: 0;
      z-index: 100;
      transition: width 0.3s;
    }

    .sidebar-brand {
      display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem; margin-bottom: 2rem; cursor: pointer;
    }

    .brand-isotype { width: 32px; height: 32px; flex-shrink: 0; }
    .brand-title { font-size: 1.35rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading); }

    .sidebar-nav { display: flex; flex-direction: column; gap: 0.4rem; flex: 1; }

    .nav-btn {
      display: flex; align-items: center; gap: 0.85rem; padding: 0.75rem 1rem;
      border-radius: 12px; background: transparent; border: none; color: var(--text-secondary);
      font-size: 0.92rem; font-weight: 600; cursor: pointer; width: 100%; text-align: left; transition: all 0.2s;
      text-decoration: none;
    }
    .nav-btn:hover { background: var(--bg-app); color: var(--text-primary); }
    .nav-btn.active { background: rgba(79, 70, 229, 0.1); color: #4F46E5; font-weight: 700; }

    .sidebar-footer { border-top: 1px solid var(--border-subtle); padding-top: 1rem; display: flex; flex-direction: column; gap: 0.5rem; }

    .user-badge-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem; }
    .user-avatar {
      width: 34px; height: 34px; border-radius: 50%; background: #4F46E5; color: #FFFFFF;
      font-weight: 800; display: flex; align-items: center; justify-content: center; font-size: 0.88rem;
    }
    .user-info { display: flex; flex-direction: column; }
    .u-name { font-size: 0.88rem; font-weight: 700; color: var(--text-primary); }
    .u-role { font-size: 0.72rem; color: var(--text-muted); }

    .logout-btn { color: var(--color-error); }
    .logout-btn:hover { background: rgba(239, 68, 68, 0.1); }

    .main-content-area { flex: 1; margin-left: 250px; padding: 2.5rem; min-height: 100vh; }

    .session-modal-overlay {
      position: fixed; inset: 0; background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(6px);
      z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 1.5rem;
    }
    .session-modal-card {
      background: var(--bg-surface); border: 1px solid var(--border-subtle);
      border-radius: 16px; padding: 2rem; max-width: 400px; width: 100%; text-align: center;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    }
    .session-modal-card h3 { font-size: 1.25rem; margin-bottom: 0.5rem; }
    .session-modal-card p { font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 1.5rem; }
    .btn-primary-modal {
      width: 100%; padding: 0.75rem; background: #4F46E5; color: #FFF; border: none; border-radius: 10px; font-weight: 700; cursor: pointer;
    }

    @media (max-width: 900px) {
      .sidebar-shell { width: 70px; padding: 1rem 0.4rem; }
      .main-content-area { margin-left: 70px; padding: 1.5rem; }
    }
  `]
})
export class AppComponent implements OnInit {
  readonly themeService = inject(ThemeService);
  readonly i18n = inject(I18nService);
  readonly authStore = inject(AuthStore);
  private router = inject(Router);

  isSidebarCollapsed = signal<boolean>(false);

  ngOnInit(): void {
    this.authStore.initSession();
  }

  logout(): void {
    this.authStore.logout();
  }
}
