import { Component, Input, Output, EventEmitter } from '@angular/core';
import { RecentProject, UserMetrics } from '../../core/services/state.service';

@Component({
  selector: 'app-dashboard',
  template: `
    <div class="dashboard-container">
      <!-- Welcome Banner (Shown only when showHeaderAndActions is true) -->
      <div class="welcome-header" *ngIf="showHeaderAndActions">
        <div class="welcome-tag">BIENVENIDO DE NUEVO</div>
        <h1 class="welcome-title">Hola, {{ userName }}</h1>
        <p class="welcome-sub">Transforma documentación técnica en experiencias de aprendizaje.</p>
      </div>

      <!-- Metric Cards Grid (Shown only when showHeaderAndActions is true) -->
      <div class="metrics-grid" *ngIf="showHeaderAndActions">
        <div class="metric-card">
          <div class="metric-icon-wrapper icon-blue">📄</div>
          <div class="metric-info">
            <span class="metric-label">Documentos</span>
            <div class="metric-value-row">
              <span class="metric-value">{{ metrics?.documentos || 0 }}</span>
              <span class="metric-trend text-blue" *ngIf="(metrics?.documentos || 0) > 0">+{{ metrics?.documentos }} esta semana</span>
              <span class="metric-trend text-muted" *ngIf="(metrics?.documentos || 0) === 0">Sin actividad</span>
            </div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-wrapper icon-purple">⚡</div>
          <div class="metric-info">
            <span class="metric-label">Contenidos generados</span>
            <div class="metric-value-row">
              <span class="metric-value">{{ metrics?.contenidos || 0 }}</span>
              <span class="metric-trend text-purple" *ngIf="(metrics?.contenidos || 0) > 0">+{{ metrics?.contenidos }} esta semana</span>
              <span class="metric-trend text-muted" *ngIf="(metrics?.contenidos || 0) === 0">Sin actividad</span>
            </div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-wrapper icon-green">🧠</div>
          <div class="metric-info">
            <span class="metric-label">Ejecuciones RAG</span>
            <div class="metric-value-row">
              <span class="metric-value">{{ metrics?.ejecucionesRag || 0 }}</span>
              <span class="metric-trend text-green" *ngIf="(metrics?.ejecucionesRag || 0) > 0">+{{ metrics?.ejecucionesRag }} esta semana</span>
              <span class="metric-trend text-muted" *ngIf="(metrics?.ejecucionesRag || 0) === 0">Sin actividad</span>
            </div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon-wrapper icon-amber">☁️</div>
          <div class="metric-info">
            <span class="metric-label">Fuentes almacenadas</span>
            <div class="metric-value-row">
              <span class="metric-value">{{ metrics?.fuentes || 0 }}</span>
              <span class="metric-trend text-amber" *ngIf="(metrics?.fuentes || 0) > 0">+{{ metrics?.fuentes }} esta semana</span>
              <span class="metric-trend text-muted" *ngIf="(metrics?.fuentes || 0) === 0">Sin actividad</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions Grid (Shown only when showHeaderAndActions is true) -->
      <div class="quick-actions-section" *ngIf="showHeaderAndActions">
        <h2 class="section-title">Acciones rápidas</h2>
        <p class="section-sub">Comienza a crear, organizar y aprender.</p>

        <div class="actions-grid">
          <div class="action-card" (click)="onCreateNew(1)">
            <div class="action-icon icon-blue">📤</div>
            <div class="action-content">
              <h3>Subir documento</h3>
              <p>PDF, TXT, DOCX, MD...</p>
            </div>
            <span class="action-arrow">➔</span>
          </div>

          <div class="action-card" (click)="onCreateNew(2)">
            <div class="action-icon icon-purple">📄</div>
            <div class="action-content">
              <h3>Crear contenido</h3>
              <p>Genera experiencias de aprendizaje</p>
            </div>
            <span class="action-arrow">➔</span>
          </div>

          <div class="action-card" (click)="onViewHistory()">
            <div class="action-icon icon-green">🕒</div>
            <div class="action-content">
              <h3>Ver historial</h3>
              <p>Revisa tus actividades recientes</p>
            </div>
            <span class="action-arrow">➔</span>
          </div>
        </div>
      </div>

      <!-- Recent Projects Table Section (ALWAYS shown) -->
      <div class="recent-projects-section">
        <div class="table-header">
          <div>
            <h2 class="section-title">{{ showHeaderAndActions ? 'Proyectos recientes' : 'Documentos y contenidos' }}</h2>
            <p class="section-sub">Tus documentos y contenidos más recientes.</p>
          </div>
          <button class="btn-link" *ngIf="showHeaderAndActions && recentProjects && recentProjects.length > 0" (click)="onViewHistory()">Ver todos ➔</button>
        </div>

        <!-- Table View if projects exist -->
        <div class="table-card" *ngIf="recentProjects && recentProjects.length > 0">
          <table class="data-table">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Perfil</th>
                <th>Formato</th>
                <th>Estado</th>
                <th>Fecha</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let item of recentProjects" (click)="onSelectProject(item)">
                <td class="col-name">
                  <div class="project-name-box">
                    <div class="format-badge-icon" [ngClass]="item.formato.toLowerCase()">
                      {{ item.typeIcon }}
                    </div>
                    <div>
                      <div class="project-title">{{ item.nombre }}</div>
                      <div class="project-sub">{{ item.descripcion }}</div>
                    </div>
                  </div>
                </td>
                <td>
                  <span class="tag-pill">{{ item.perfil }}</span>
                </td>
                <td>
                  <span class="format-tag">{{ item.formato }}</span>
                </td>
                <td>
                  <span class="badge" [ngClass]="{
                    'badge-green': item.estado === 'Completado',
                    'badge-blue': item.estado === 'En proceso',
                    'badge-yellow': item.estado === 'Pendiente'
                  }">
                    {{ item.estado }}
                  </span>
                </td>
                <td class="col-date">{{ item.fecha }}</td>
                <td class="col-actions" (click)="$event.stopPropagation()">
                  <div class="action-menu-wrapper">
                    <button class="btn-dots" (click)="toggleRowMenu(item.id, $event)">•••</button>

                    <!-- Context Dropdown Menu for Row -->
                    <div *ngIf="activeMenuId === item.id" class="row-dropdown-menu">
                      <button class="dropdown-item" (click)="onSelectProject(item); closeMenu($event)">
                        <span class="item-icon">👁️</span> Visualizar
                      </button>
                      <button class="dropdown-item" (click)="onDownloadProjectPdf(item); closeMenu($event)">
                        <span class="item-icon">📥</span> Descargar PDF
                      </button>
                      <button class="dropdown-item" (click)="onDownloadProjectJson(item); closeMenu($event)">
                        <span class="item-icon">📄</span> Descargar JSON
                      </button>
                      <div class="dropdown-divider"></div>
                      <button class="dropdown-item text-danger" (click)="onDeleteProject(item.id); closeMenu($event)">
                        <span class="item-icon">🗑️</span> Eliminar
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Empty State Card if no projects exist -->
        <div class="empty-state-card" *ngIf="!recentProjects || recentProjects.length === 0">
          <div class="empty-icon-circle">📂</div>
          <h3>Aún no tienes proyectos procesados</h3>
          <p>Comienza subiendo tu primer documento técnico (PDF, MD, TXT) para generar experiencias de aprendizaje adaptadas.</p>
          <button class="btn btn-primary btn-empty-action" (click)="onCreateNew(1)">
            ➕ Subir mi primer documento
          </button>
        </div>
      </div>

      <!-- Footer Quote -->
      <div class="dashboard-footer-quote" *ngIf="showHeaderAndActions">
        <div class="quote-text">DEL CONOCIMIENTO TÉCNICO A UN MAYOR POTENCIAL HUMANO.</div>
        <div class="quote-sub">MISMA INFORMACIÓN, MÁS APRENDIZAJE.</div>
      </div>
    </div>
  `,
  styles: [`
    .dashboard-container {
      display: flex;
      flex-direction: column;
      gap: 2.5rem;
    }

    .welcome-tag {
      font-size: 0.75rem;
      font-weight: 700;
      color: #3b82f6;
      letter-spacing: 0.08em;
      margin-bottom: 0.25rem;
    }
    .welcome-title {
      font-size: 2.25rem;
      font-weight: 800;
      color: #0f172a;
      letter-spacing: -0.02em;
    }
    .welcome-sub {
      font-size: 1rem;
      color: #64748b;
    }

    /* Metrics Grid */
    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1.25rem;
    }
    .metric-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 1.25rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
      transition: transform 0.2s;
    }
    .metric-card:hover {
      transform: translateY(-2px);
    }
    .metric-icon-wrapper {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
    }
    .icon-blue { background: #eff6ff; color: #3b82f6; }
    .icon-purple { background: #f3e8ff; color: #a855f7; }
    .icon-green { background: #ecfdf5; color: #10b981; }
    .icon-amber { background: #fffbeb; color: #f59e0b; }

    .metric-info {
      display: flex;
      flex-direction: column;
    }
    .metric-label {
      font-size: 0.78rem;
      color: #64748b;
      font-weight: 600;
    }
    .metric-value-row {
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
    }
    .metric-value {
      font-size: 1.65rem;
      font-weight: 800;
      color: #0f172a;
    }
    .metric-trend {
      font-size: 0.72rem;
      font-weight: 700;
    }
    .text-blue { color: #3b82f6; }
    .text-purple { color: #a855f7; }
    .text-green { color: #10b981; }
    .text-amber { color: #f59e0b; }
    .text-muted { color: #94a3b8; }

    /* Quick Actions */
    .section-title {
      font-size: 1.35rem;
      font-weight: 800;
      color: #0f172a;
    }
    .section-sub {
      font-size: 0.85rem;
      color: #64748b;
      margin-bottom: 1rem;
    }
    .actions-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1.25rem;
    }
    .action-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 1.25rem;
      display: flex;
      align-items: center;
      gap: 1rem;
      cursor: pointer;
      transition: all 0.2s;
    }
    .action-card:hover {
      border-color: #bfdbfe;
      box-shadow: 0 8px 20px -4px rgba(59, 130, 246, 0.1);
      transform: translateY(-2px);
    }
    .action-icon {
      width: 42px;
      height: 42px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
    }
    .action-content {
      flex: 1;
    }
    .action-content h3 {
      font-size: 0.95rem;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 0.15rem;
    }
    .action-content p {
      font-size: 0.78rem;
      color: #64748b;
    }
    .action-arrow {
      font-size: 1rem;
      color: #94a3b8;
    }
    .action-card:hover .action-arrow {
      color: #3b82f6;
      transform: translateX(3px);
    }

    /* Table Section */
    .table-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
      margin-bottom: 0.75rem;
    }
    .btn-link {
      background: none;
      border: none;
      color: #3b82f6;
      font-weight: 700;
      font-size: 0.85rem;
      cursor: pointer;
    }
    .table-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      overflow: visible;
      box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }
    .data-table th {
      background: #f8fafc;
      padding: 0.85rem 1.25rem;
      font-size: 0.75rem;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid #e2e8f0;
    }
    .data-table td {
      padding: 1rem 1.25rem;
      border-bottom: 1px solid #f1f5f9;
      font-size: 0.88rem;
      position: relative;
    }
    .data-table tr:hover {
      background: #f8fafc;
      cursor: pointer;
    }
    .project-name-box {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .format-badge-icon {
      width: 34px;
      height: 34px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: 800;
      background: #eff6ff;
      color: #2563eb;
    }

    .project-title {
      font-weight: 700;
      color: #0f172a;
    }
    .project-sub {
      font-size: 0.75rem;
      color: #94a3b8;
    }
    .tag-pill {
      font-size: 0.75rem;
      color: #475569;
      background: #f1f5f9;
      padding: 0.2rem 0.6rem;
      border-radius: 6px;
      font-weight: 600;
    }
    .format-tag {
      font-size: 0.75rem;
      font-weight: 700;
      color: #64748b;
    }
    .col-date {
      color: #64748b;
      font-size: 0.82rem;
    }

    .action-menu-wrapper {
      position: relative;
      display: inline-block;
    }
    .btn-dots {
      background: #f1f5f9;
      border: 1px solid #cbd5e1;
      color: #475569;
      font-size: 0.9rem;
      padding: 0.3rem 0.6rem;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-dots:hover {
      background: #e2e8f0;
      color: #0f172a;
    }

    .row-dropdown-menu {
      position: absolute;
      right: 0;
      top: 100%;
      margin-top: 0.25rem;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.15);
      width: 170px;
      z-index: 1000;
      padding: 0.4rem;
    }
    .dropdown-item {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      padding: 0.55rem 0.75rem;
      background: transparent;
      border: none;
      font-size: 0.85rem;
      font-weight: 600;
      color: #334155;
      cursor: pointer;
      border-radius: 8px;
      width: 100%;
      text-align: left;
    }
    .dropdown-item:hover {
      background: #f1f5f9;
      color: #0f172a;
    }
    .dropdown-item.text-danger {
      color: #dc2626;
    }
    .dropdown-item.text-danger:hover {
      background: #fee2e2;
    }
    .dropdown-divider {
      height: 1px;
      background: #e2e8f0;
      margin: 0.3rem 0;
    }

    /* Empty State Card */
    .empty-state-card {
      background: #ffffff;
      border: 1px dashed #cbd5e1;
      border-radius: 16px;
      padding: 3rem 2rem;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;
    }
    .empty-icon-circle {
      width: 60px;
      height: 60px;
      border-radius: 50%;
      background: #eff6ff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.75rem;
    }
    .empty-state-card h3 {
      font-size: 1.15rem;
      font-weight: 700;
      color: #0f172a;
    }
    .empty-state-card p {
      font-size: 0.9rem;
      color: #64748b;
      max-width: 480px;
      line-height: 1.5;
    }
    .btn-empty-action {
      margin-top: 0.75rem;
      padding: 0.75rem 1.5rem;
      border-radius: 10px;
    }

    .dashboard-footer-quote {
      margin-top: 1rem;
      padding-top: 2rem;
      border-top: 1px solid #e2e8f0;
      display: flex;
      justify-content: space-between;
      color: #94a3b8;
      font-size: 0.75rem;
      font-weight: 800;
      letter-spacing: 0.05em;
    }

    @media (max-width: 1024px) {
      .metrics-grid { grid-template-columns: repeat(2, 1fr); }
      .actions-grid { grid-template-columns: 1fr; }
    }
  `]
})
export class DashboardComponent {
  @Input() userName: string = 'Fernando';
  @Input() metrics?: UserMetrics;
  @Input() recentProjects: RecentProject[] = [];
  @Input() showHeaderAndActions: boolean = true;

  @Output() navigateToCreate = new EventEmitter<number>();
  @Output() navigateToHistory = new EventEmitter<void>();
  @Output() selectProject = new EventEmitter<RecentProject>();
  @Output() deleteProject = new EventEmitter<string>();

  activeMenuId: string | null = null;

  toggleRowMenu(id: string, event: MouseEvent): void {
    event.stopPropagation();
    if (this.activeMenuId === id) {
      this.activeMenuId = null;
    } else {
      this.activeMenuId = id;
    }
  }

  closeMenu(event: MouseEvent): void {
    event.stopPropagation();
    this.activeMenuId = null;
  }

  onCreateNew(step: number): void {
    this.navigateToCreate.emit(step);
  }

  onViewHistory(): void {
    this.navigateToHistory.emit();
  }

  onSelectProject(project: RecentProject): void {
    this.selectProject.emit(project);
  }

  onDeleteProject(id: string): void {
    this.deleteProject.emit(id);
  }

  onDownloadProjectPdf(project: RecentProject): void {
    const title = project.nombre;
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Habilita las ventanas emergentes para descargar el PDF.');
      return;
    }
    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>${title}</title>
        <style>
          body { font-family: sans-serif; padding: 2rem; color: #0f172a; line-height: 1.6; }
          h1 { color: #2563eb; }
          .card { background: #f8fafc; border: 1px solid #cbd5e1; padding: 1rem; margin-bottom: 1rem; border-radius: 8px; }
        </style>
      </head>
      <body>
        <h1>${title}</h1>
        <p><strong>Perfil:</strong> ${project.perfil}</p>
        <p><strong>Estado:</strong> ${project.estado}</p>
        <p><strong>Fecha:</strong> ${project.fecha}</p>
        <div class="card">
          <p>${project.response?.contenido_adaptado?.introduccion_contextualizada || 'Contenido adaptado generado con IA.'}</p>
        </div>
        <script>window.onload = function() { window.print(); }</script>
      </body>
      </html>
    `;
    printWindow.document.write(htmlContent);
    printWindow.document.close();
  }

  onDownloadProjectJson(project: RecentProject): void {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(project.response || project, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${project.nombre.toLowerCase().replace(/[^a-z0-9]/g, '-')}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  }
}
