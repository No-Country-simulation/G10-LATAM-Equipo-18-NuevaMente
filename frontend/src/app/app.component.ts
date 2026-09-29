import { Component, OnInit } from '@angular/core';
import { StateService, RecentProject, UserMetrics, UserProfile } from './core/services/state.service';
import { AdaptationRequest, AdaptationResponse } from './core/models/adaptation.model';

export type ActiveView = 'login' | 'dashboard' | 'create' | 'documents' | 'history' | 'settings';

@Component({
  selector: 'app-root',
  template: `
    <!-- VIEW 1: LANDING & LOGIN (Full Screen) -->
    <app-landing-login 
      *ngIf="activeView === 'login'"
      (loginSuccess)="onLoginSuccess($event)"
    ></app-landing-login>

    <!-- VIEW 2-6: DASHBOARD & APP SHELL (Sidebar + Top Bar + Main) -->
    <div *ngIf="activeView !== 'login'" class="app-layout">
      <!-- Left Sidebar Navigation -->
      <aside class="sidebar">
        <div class="sidebar-brand" (click)="navigate('dashboard')">
          <span class="brand-icon">🎓</span>
          <span class="brand-text">NuevaMente</span>
        </div>

        <nav class="sidebar-nav">
          <button 
            class="nav-item" 
            [ngClass]="{'active': activeView === 'dashboard'}"
            (click)="navigate('dashboard')"
          >
            <span class="nav-icon">🏠</span>
            <span class="nav-label">Inicio</span>
          </button>

          <button 
            class="nav-item" 
            [ngClass]="{'active': activeView === 'create'}"
            (click)="startCreate(1)"
          >
            <span class="nav-icon">📄</span>
            <span class="nav-label">Nuevo contenido</span>
          </button>

          <button 
            class="nav-item" 
            [ngClass]="{'active': activeView === 'documents'}"
            (click)="navigate('documents')"
          >
            <span class="nav-icon">📁</span>
            <span class="nav-label">Mis documentos</span>
          </button>

          <button 
            class="nav-item" 
            [ngClass]="{'active': activeView === 'history'}"
            (click)="navigate('history')"
          >
            <span class="nav-icon">🕒</span>
            <span class="nav-label">Historial</span>
          </button>

          <button 
            class="nav-item" 
            [ngClass]="{'active': activeView === 'settings'}"
            (click)="navigate('settings')"
          >
            <span class="nav-icon">⚙️</span>
            <span class="nav-label">Configuración</span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <button class="nav-item btn-logout" (click)="logout()">
            <span class="nav-icon">🚪</span>
            <span class="nav-label">Cerrar sesión</span>
          </button>
        </div>
      </aside>

      <!-- Main Workspace Area -->
      <div class="main-workspace">
        <!-- Top Navigation Header -->
        <header class="app-topbar">
          <div class="search-box">
            <span class="search-icon">🔍</span>
            <input 
              type="text" 
              class="search-input" 
              placeholder="Buscar documentos, contenidos..." 
            />
          </div>

          <div class="topbar-actions">
            <button class="icon-btn notification-btn">
              <span class="bell-icon">🔔</span>
              <span class="notification-badge" *ngIf="metrics.documentos > 0"></span>
            </button>

            <div class="user-profile-badge">
              <div class="avatar-circle">{{ userProfile.avatarLetter }}</div>
              <span class="user-name">{{ userProfile.name }}</span>
            </div>
          </div>
        </header>

        <!-- Dynamic Main Content View -->
        <main class="page-content">
          <!-- DASHBOARD VIEW -->
          <app-dashboard 
            *ngIf="activeView === 'dashboard'"
            [userName]="userProfile.name"
            [metrics]="metrics"
            [recentProjects]="recentProjects"
            [showHeaderAndActions]="true"
            (navigateToCreate)="startCreate($event)"
            (navigateToHistory)="navigate('history')"
            (selectProject)="onSelectProject($event)"
            (deleteProject)="onDeleteProject($event)"
          ></app-dashboard>

          <!-- STEPPER CREATION FLOW -->
          <app-stepper-creation
            *ngIf="activeView === 'create'"
            [initialStep]="creationStep"
            (completed)="onDocumentCompleted($event)"
          ></app-stepper-creation>

          <!-- MIS DOCUMENTOS VIEW (Only Projects Table shown) -->
          <div *ngIf="activeView === 'documents'" class="simple-page-view">
            <div class="page-header">
              <h1>Mis documentos</h1>
              <p>Gestiona todos tus contenidos técnicos adaptados.</p>
            </div>
            <app-dashboard 
              [userName]="userProfile.name"
              [metrics]="metrics"
              [recentProjects]="recentProjects"
              [showHeaderAndActions]="false"
              (navigateToCreate)="startCreate($event)"
              (navigateToHistory)="navigate('history')"
              (selectProject)="onSelectProject($event)"
              (deleteProject)="onDeleteProject($event)"
            ></app-dashboard>
          </div>

          <!-- HISTORIAL VIEW (Only Projects Table shown) -->
          <div *ngIf="activeView === 'history'" class="simple-page-view">
            <div class="page-header">
              <h1>Historial de ejecuciones</h1>
              <p>Registro completo de ejecuciones Graph RAG y búsquedas híbridas.</p>
            </div>
            <app-dashboard 
              [userName]="userProfile.name"
              [metrics]="metrics"
              [recentProjects]="recentProjects"
              [showHeaderAndActions]="false"
              (navigateToCreate)="startCreate($event)"
              (navigateToHistory)="navigate('history')"
              (selectProject)="onSelectProject($event)"
              (deleteProject)="onDeleteProject($event)"
            ></app-dashboard>
          </div>

          <!-- CONFIGURACIÓN VIEW -->
          <div *ngIf="activeView === 'settings'" class="simple-page-view card-box">
            <h1 class="page-title">Configuración del sistema</h1>
            <div class="form-group" style="margin-top: 1.5rem;">
              <label>Usuario actual</label>
              <input type="text" class="form-control" [value]="userProfile.name + ' (' + userProfile.email + ')'" readonly />
            </div>

            <div class="form-group">
              <label>API Key de Google Gemini</label>
              <input type="password" class="form-control" value="AIzaSyXXXXXXXXXXXXXXXXXX" />
            </div>

            <div class="form-group">
              <label>Bucket OCI Object Storage (Documentos)</label>
              <input type="text" class="form-control" value="nuevamente-documentos-fuente" />
            </div>

            <div class="form-group">
              <label>Bucket OCI Object Storage (Artefactos JSON)</label>
              <input type="text" class="form-control" value="nuevamente-contenidos-educativos" />
            </div>

            <button class="btn btn-primary" style="margin-top: 1rem;">Guardar cambios</button>
          </div>
        </main>
      </div>
    </div>
  `,
  styles: [`
    .app-layout {
      display: flex;
      min-height: 100vh;
      background: #f8fafc;
    }

    /* Sidebar Styling */
    .sidebar {
      width: 260px;
      background: #ffffff;
      border-right: 1px solid #e2e8f0;
      display: flex;
      flex-direction: column;
      padding: 1.5rem 1rem;
      position: fixed;
      top: 0;
      bottom: 0;
      left: 0;
      z-index: 100;
    }
    .sidebar-brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.5rem 0.75rem;
      margin-bottom: 2rem;
      cursor: pointer;
    }
    .brand-icon {
      font-size: 1.75rem;
    }
    .brand-text {
      font-size: 1.35rem;
      font-weight: 800;
      color: #0f172a;
    }

    .sidebar-nav {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      flex: 1;
    }
    .nav-item {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      padding: 0.75rem 1rem;
      border-radius: 12px;
      background: transparent;
      border: none;
      color: #64748b;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      width: 100%;
      text-align: left;
      transition: all 0.2s;
    }
    .nav-item:hover {
      background: #f1f5f9;
      color: #0f172a;
    }
    .nav-item.active {
      background: #eff6ff;
      color: #2563eb;
      font-weight: 700;
    }
    .nav-icon {
      font-size: 1.15rem;
    }

    .sidebar-footer {
      border-top: 1px solid #e2e8f0;
      padding-top: 1rem;
    }
    .btn-logout {
      color: #ef4444;
    }
    .btn-logout:hover {
      background: #fee2e2;
      color: #dc2626;
    }

    /* Main Workspace */
    .main-workspace {
      flex: 1;
      margin-left: 260px;
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }

    /* Top Bar */
    .app-topbar {
      height: 70px;
      background: #ffffff;
      border-bottom: 1px solid #e2e8f0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 2.5rem;
      position: sticky;
      top: 0;
      z-index: 90;
    }
    .search-box {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: #f1f5f9;
      border-radius: 12px;
      padding: 0.5rem 1rem;
      width: 380px;
    }
    .search-icon {
      font-size: 0.9rem;
      color: #94a3b8;
    }
    .search-input {
      background: transparent;
      border: none;
      width: 100%;
      font-size: 0.88rem;
      color: #0f172a;
    }

    .topbar-actions {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }
    .icon-btn {
      background: #f1f5f9;
      border: none;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
      cursor: pointer;
    }
    .notification-badge {
      position: absolute;
      top: 8px;
      right: 8px;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #ef4444;
    }

    .user-profile-badge {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      cursor: pointer;
    }
    .avatar-circle {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: #eff6ff;
      color: #2563eb;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.95rem;
      border: 1px solid #bfdbfe;
    }
    .user-name {
      font-weight: 700;
      font-size: 0.95rem;
      color: #0f172a;
    }

    .page-content {
      padding: 2.5rem;
      flex: 1;
    }

    .simple-page-view {
      max-width: 1100px;
      margin: 0 auto;
    }
    .page-header {
      margin-bottom: 2rem;
    }
    .page-header h1 {
      font-size: 2rem;
      font-weight: 800;
    }
    .page-header p {
      color: #64748b;
    }

    @media (max-width: 900px) {
      .sidebar { width: 80px; padding: 1rem 0.5rem; }
      .brand-text, .nav-label { display: none; }
      .main-workspace { margin-left: 80px; }
      .search-box { width: 200px; }
    }
  `]
})
export class AppComponent implements OnInit {
  activeView: ActiveView = 'login';
  creationStep: number = 1;

  constructor(private stateService: StateService) {}

  ngOnInit(): void {
    if (this.userProfile.isLoggedIn) {
      this.activeView = 'dashboard';
    } else {
      this.activeView = 'login';
    }
  }

  get userProfile(): UserProfile {
    return this.stateService.getUser();
  }

  get metrics(): UserMetrics {
    return this.stateService.getMetrics();
  }

  get recentProjects(): RecentProject[] {
    return this.stateService.getProjects();
  }

  onLoginSuccess(event: { email: string; name: string; token?: string }): void {
    this.stateService.setUser(event.email, event.name, event.token);
    this.activeView = 'dashboard';
  }

  logout(): void {
    this.stateService.logoutUser();
    this.activeView = 'login';
  }

  navigate(view: ActiveView): void {
    this.activeView = view;
  }

  startCreate(step: number = 1): void {
    this.creationStep = step;
    this.activeView = 'create';
  }

  onDocumentCompleted(event: { request: AdaptationRequest; response: AdaptationResponse }): void {
    this.stateService.addProjectFromResponse(event.request, event.response);
  }

  onSelectProject(project: RecentProject): void {
    this.creationStep = 4;
    this.activeView = 'create';
  }

  onDeleteProject(id: string): void {
    this.stateService.deleteProject(id);
  }
}
