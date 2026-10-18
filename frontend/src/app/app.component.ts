import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { ThemeService } from './core/services/theme.service';
import { I18nService } from './core/services/i18n.service';
import { AuthStore } from './core/store/auth.store';
import { StateService } from './core/services/state.service';
import { DocumentService } from './core/services/document.service';
import { PipelineStateService } from './core/services/pipeline-state.service';

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
    <!-- UNAUTHENTICATED OR PUBLIC AUTH ROUTE (Login / Register / Recover Pages) -->
    <div *ngIf="!authStore.isAuthenticated() || isAuthRoute()">
      <router-outlet></router-outlet>
    </div>

    <!-- AUTHENTICATED WORKSPACE SHELL (Sidebar + Header + Protected Content Router Outlet) -->
    <div *ngIf="authStore.isAuthenticated() && !isAuthRoute()" class="app-shell-layout">
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
            <svg class="nav-icon-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span class="nav-text" *ngIf="!isSidebarCollapsed()">Workspace</span>
          </a>

          <a 
            routerLink="/documents" 
            routerLinkActive="active" 
            class="nav-btn"
          >
            <svg class="nav-icon-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            <span class="nav-text" *ngIf="!isSidebarCollapsed()">Mis Documentos</span>
            <span class="nav-doc-badge" *ngIf="getActiveDocCount() > 0">{{ getActiveDocCount() }}</span>
          </a>

          <a 
            routerLink="/library" 
            routerLinkActive="active" 
            class="nav-btn"
          >
            <svg class="nav-icon-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
            <span class="nav-text" *ngIf="!isSidebarCollapsed()">Biblioteca</span>
          </a>

          <a 
            routerLink="/papelera" 
            routerLinkActive="active" 
            class="nav-btn nav-btn-trash"
          >
            <svg class="nav-icon-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            <span class="nav-text" *ngIf="!isSidebarCollapsed()">Papelera</span>
            <span class="nav-trash-badge" *ngIf="getTrashCount() > 0">{{ getTrashCount() }}</span>
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
        <!-- GLOBAL PIPELINE BANNER: announced from any view while a run is active -->
        <div class="pipeline-banner" *ngIf="pipeline.running() && !isAuthRoute() && !isProcessRoute()" (click)="goToProcessView()">
          <span class="banner-spinner" aria-hidden="true"></span>
          <span class="banner-label">
            {{ pipeline.mode() === 'ingest' ? 'Ingesta en curso' : 'Generación en curso' }}
          </span>
          <span class="banner-step" *ngIf="pipeline.activeStage() as stage">
            Paso {{ currentStepIndex() + 1 }}/{{ pipeline.stages().length }}: {{ stage.nombre }}
          </span>
          <span class="banner-time">{{ elapsedLabel() }}</span>
          <span class="banner-cta">Ver progreso →</span>
        </div>

        <!-- Finished notice when the result is waiting for the user -->
        <div class="pipeline-banner pipeline-banner-done" *ngIf="pipeline.finished() && !pipeline.running() && !isAuthRoute() && !isProcessRoute()" (click)="goToResultView()">
          <span class="banner-check" aria-hidden="true">✅</span>
          <span class="banner-label">Contenido educativo listo</span>
          <span class="banner-cta">Ver resultado →</span>
        </div>

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
      text-decoration: none; position: relative;
    }
    .nav-btn:hover { background: var(--bg-app); color: var(--text-primary); }
    .nav-btn.active { background: rgba(79, 70, 229, 0.1); color: #4F46E5; font-weight: 700; }
    .nav-icon-svg { flex-shrink: 0; }

    .nav-doc-badge {
      margin-left: auto;
      background: #4F46E5;
      color: #FFFFFF;
      font-size: 0.72rem;
      font-weight: 800;
      padding: 0.15rem 0.5rem;
      border-radius: 10px;
    }

    .nav-trash-badge {
      margin-left: auto;
      background: #EF4444;
      color: #FFFFFF;
      font-size: 0.72rem;
      font-weight: 800;
      padding: 0.15rem 0.5rem;
      border-radius: 10px;
    }

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

    /* Global pipeline banner (running / finished notices) */
    .pipeline-banner {
      position: sticky;
      top: 0;
      z-index: 300;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin: -1rem 0 1.5rem;
      padding: 0.7rem 1.1rem;
      border-radius: 12px;
      background: linear-gradient(90deg, rgba(79, 70, 229, 0.12), rgba(34, 211, 238, 0.08));
      border: 1px solid rgba(99, 102, 241, 0.35);
      cursor: pointer;
      font-size: 0.85rem;
    }
    .pipeline-banner-done {
      background: rgba(16, 185, 129, 0.1);
      border-color: rgba(16, 185, 129, 0.4);
    }
    .banner-label { font-weight: 800; color: var(--text-primary); }
    .banner-step { color: var(--text-secondary); }
    .banner-time {
      font-variant-numeric: tabular-nums;
      color: var(--text-muted);
      font-weight: 600;
    }
    .banner-cta { margin-left: auto; font-weight: 700; color: #6366F1; }
    .banner-check { font-size: 1rem; }
    .banner-spinner {
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 2px solid rgba(99, 102, 241, 0.3);
      border-top-color: #6366F1;
      animation: banner-spin 0.8s linear infinite;
      flex-shrink: 0;
    }
    @keyframes banner-spin { to { transform: rotate(360deg); } }

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
  private stateService = inject(StateService);
  readonly documentService = inject(DocumentService);
  readonly pipeline = inject(PipelineStateService);
  private router = inject(Router);

  isSidebarCollapsed = signal<boolean>(false);

  ngOnInit(): void {
    this.authStore.initSession();
  }

  getActiveDocCount(): number {
    return this.documentService.totalActiveCount();
  }

  getTrashCount(): number {
    return this.stateService.getTrashProjects().length;
  }

  isAuthRoute(): boolean {
    const url = this.router.url;
    return url.includes('/auth') || url.includes('/login') || url === '/terms' || url === '/privacy';
  }

  /** True while the dedicated process view is on screen (its own header says it all). */
  isProcessRoute(): boolean {
    return this.router.url.startsWith('/proceso');
  }

  /** Zero-based index of the active stage for the banner's "Paso X/Y". */
  currentStepIndex(): number {
    const stages = this.pipeline.stages();
    const idx = stages.findIndex(stage => stage.estado === 'activo');
    return idx >= 0 ? idx : stages.length - 1;
  }

  /** Elapsed run time as mm:ss for the global banner. */
  elapsedLabel(): string {
    const total = this.pipeline.elapsedSeconds();
    const minutes = Math.floor(total / 60).toString().padStart(2, '0');
    const seconds = (total % 60).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  }

  /** Opens the dedicated, restorable process view. */
  goToProcessView(): void {
    this.router.navigateByUrl('/proceso');
  }

  /** Opens the Workspace where the finished result is displayed. */
  goToResultView(): void {
    this.router.navigateByUrl('/workspace');
  }

  logout(): void {
    this.stateService.clearActiveAdaptation();
    this.documentService.clearWorkspaceSelection();
    this.authStore.logout();
  }
}
