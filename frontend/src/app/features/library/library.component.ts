import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { StateService, RecentProject } from '../../core/services/state.service';
import { ExportService } from '../../core/services/export.service';
import { AdaptationResponse, AdaptationRequest } from '../../core/models/adaptation.model';
import { NUEVAMENTE_API, NuevaMenteApi } from '../../core/api/nuevamente-api';

interface ToastState {
  id: string;
  nombre: string;
  timeoutId?: any;
}

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="library-container">
      <!-- TOAST NOTIFICATION (aria-live="polite") -->
      <div 
        class="toast-notification" 
        *ngIf="toast()" 
        role="status" 
        aria-live="polite"
      >
        <div class="toast-content">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22D3EE" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          <span>"<strong>{{ toast()?.nombre }}</strong>" se movió a la papelera</span>
        </div>
        <button 
          type="button" 
          class="btn-undo-toast" 
          (click)="undoMoveToTrash(toast()!.id)"
          aria-label="Deshacer mover a la papelera"
        >
          🔄 Deshacer
        </button>
      </div>

      <div class="page-header">
        <div>
          <h1>Biblioteca de Paquetes Educativos</h1>
          <p>Historial completo de documentación adaptada y almacenada en Oracle Cloud Infrastructure.</p>
        </div>
      </div>

      <!-- Filters & Search Bar -->
      <div class="controls-bar glass-card">
        <div class="search-input-box">
          <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <input 
            type="text" 
            placeholder="Buscar por título de documento..."
            [value]="searchTerm()"
            (input)="updateSearch($event)"
            aria-label="Buscar por título de documento"
          />
        </div>

        <div class="filters-row">
          <select [value]="selectedPerfil()" (change)="updatePerfil($event)" aria-label="Filtrar por perfil">
            <option value="">Todos los perfiles</option>
            <option value="Principiante">Principiante</option>
            <option value="Desarrollador">Desarrollador</option>
            <option value="Lider Tecnico">Líder Técnico</option>
            <option value="Ejecutivo">Ejecutivo</option>
          </select>

          <select [value]="selectedFormato()" (change)="updateFormato($event)" aria-label="Filtrar por formato">
            <option value="">Todos los formatos</option>
            <option value="Flashcards">Flashcards</option>
            <option value="Quiz">Quiz</option>
            <option value="Tutorial">Tutorial</option>
            <option value="Resumen Ejecutivo">Resumen Ejecutivo</option>
            <option value="Guion de Clase">Guion de Clase</option>
          </select>
        </div>
      </div>

      <!-- BATCH ACTIONS FLOATING BAR -->
      <div class="batch-actions-bar glass-card" *ngIf="selectedIds().size > 0">
        <div class="batch-count-info">
          <span class="batch-badge">{{ selectedIds().size }}</span>
          <span>elemento(s) seleccionado(s)</span>
        </div>
        <div class="batch-buttons">
          <button 
            type="button" 
            class="btn-batch-trash" 
            (click)="moveBatchToTrash()"
            aria-label="Mover seleccionados a la papelera"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            Mover a la papelera
          </button>
          <button type="button" class="btn-batch-clear" (click)="clearSelection()">✕ Cancelar</button>
        </div>
      </div>

      <!-- Table of Documents -->
      <div class="table-card glass-card" *ngIf="filteredProjects().length > 0">
        <table class="library-table">
          <thead>
            <tr>
              <th class="th-checkbox">
                <input 
                  type="checkbox" 
                  [checked]="isAllSelected()" 
                  (change)="toggleSelectAll($event)"
                  aria-label="Seleccionar todos los documentos"
                />
              </th>
              <th>Documento</th>
              <th>Perfil</th>
              <th>Formato</th>
              <th>Anclaje RAG</th>
              <th>Estado OCI</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              *ngFor="let proj of filteredProjects()" 
              [class.row-selected]="selectedIds().has(proj.id)"
              [class.row-exiting]="exitingIds().has(proj.id)"
            >
              <td class="td-checkbox">
                <input 
                  type="checkbox" 
                  [checked]="selectedIds().has(proj.id)" 
                  (change)="toggleSelectProject(proj.id)"
                  [attr.aria-label]="'Seleccionar ' + proj.nombre"
                />
              </td>
              <td class="td-title">
                <strong>{{ proj.nombre }}</strong>
                <span class="doc-date">{{ proj.fecha }}</span>
              </td>
              <td><span class="badge-profile">{{ proj.perfil }}</span></td>
              <td><span class="badge-format">{{ proj.formato }}</span></td>
              <td>
                <span class="rag-score">
                  🛡️ {{ ((proj.response?.evaluacion_calidad?.anclaje_fuente_score || 0.98) * 100) | number:'1.0-0' }}%
                </span>
              </td>
              <td>
                <span class="badge-oci done">
                  Completado (OCI)
                </span>
              </td>
              <td class="td-actions">
                <button 
                  class="btn-action-primary" 
                  (click)="viewPdf(proj)" 
                  title="Visualizar PDF Didáctico"
                  [attr.aria-label]="'Visualizar PDF de ' + proj.nombre"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
                  PDF
                </button>

                <button 
                  class="btn-action-secondary" 
                  (click)="downloadMd(proj)" 
                  title="Descargar Markdown"
                  [attr.aria-label]="'Descargar Markdown de ' + proj.nombre"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  MD
                </button>

                <button 
                  class="btn-action-danger" 
                  (click)="moveToTrash(proj)" 
                  title="Mover a la papelera"
                  [attr.aria-label]="'Mover a la papelera ' + proj.nombre"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                  Mover a la papelera
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      <div class="empty-state glass-card" *ngIf="filteredProjects().length === 0">
        <div class="empty-icon-box">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="1.5"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
        </div>
        <h3>No se encontraron documentos en la biblioteca</h3>
        <p>Prueba ajustando los filtros de búsqueda o crea una nueva adaptación educativa en el Workspace.</p>
      </div>
    </div>
  `,
  styles: [`
    .library-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 1rem 0;
      position: relative;
    }

    .toast-notification {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      z-index: 1000;
      background: var(--bg-surface);
      border: 1px solid #4F46E5;
      padding: 0.85rem 1.25rem;
      border-radius: 14px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
      display: flex;
      align-items: center;
      gap: 1.25rem;
      animation: slideUp 0.3s ease-out;
    }

    @keyframes slideUp {
      from { transform: translateY(20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    .toast-content {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 0.9rem;
      color: var(--text-primary);
    }

    .btn-undo-toast {
      background: #4F46E5;
      color: #FFFFFF;
      border: none;
      padding: 0.4rem 0.85rem;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-undo-toast:hover {
      background: #4338CA;
    }

    .page-header {
      margin-bottom: 2rem;
    }

    .page-header h1 {
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 0.5rem;
    }

    .page-header p {
      color: var(--text-secondary);
      font-size: 1.05rem;
    }

    .controls-bar {
      padding: 1.25rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .search-input-box {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      background: var(--bg-app);
      padding: 0.6rem 1rem;
      border-radius: 10px;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
    }

    .search-input-box input {
      background: transparent;
      border: none;
      width: 100%;
      font-size: 0.95rem;
      color: var(--text-primary);
      outline: none;
    }

    .filters-row {
      display: flex;
      gap: 0.75rem;
    }

    .filters-row select {
      padding: 0.6rem 1rem;
      border-radius: 10px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-size: 0.9rem;
      outline: none;
    }

    .batch-actions-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.85rem 1.25rem;
      background: rgba(99, 102, 241, 0.08);
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 14px;
      margin-bottom: 1.5rem;
    }

    .batch-count-info {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 0.9rem;
      font-weight: 600;
    }

    .batch-badge {
      background: #4F46E5;
      color: #FFF;
      padding: 0.15rem 0.6rem;
      border-radius: 12px;
      font-size: 0.82rem;
      font-weight: 800;
    }

    .batch-buttons {
      display: flex;
      gap: 0.75rem;
    }

    .btn-batch-trash {
      background: #EF4444;
      color: #FFF;
      border: none;
      padding: 0.45rem 0.9rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .btn-batch-clear {
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      padding: 0.45rem 0.85rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
    }

    .table-card {
      padding: 1rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      overflow-x: auto;
    }

    .library-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }

    .library-table th {
      padding: 1rem;
      font-size: 0.78rem;
      font-weight: 800;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-subtle);
      letter-spacing: 0.05em;
    }

    .th-checkbox, .td-checkbox {
      width: 40px;
      text-align: center;
    }

    .library-table td {
      padding: 1.15rem 1rem;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 0.92rem;
      transition: opacity 0.25s, transform 0.25s;
    }

    .row-selected {
      background: rgba(99, 102, 241, 0.04);
    }

    .row-exiting {
      opacity: 0;
      transform: translateX(-15px);
    }

    .td-title {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }

    .doc-date {
      font-size: 0.78rem;
      color: var(--text-muted);
    }

    .badge-profile, .badge-format {
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      white-space: nowrap;
    }

    .rag-score {
      color: #10B981;
      font-weight: 700;
      white-space: nowrap;
    }

    .badge-oci {
      font-size: 0.75rem;
      font-weight: 800;
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      background: rgba(16, 185, 129, 0.15);
      color: #059669;
      white-space: nowrap;
      display: inline-block;
    }

    .td-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .btn-action-primary {
      background: #4F46E5;
      color: #ffffff;
      border: none;
      padding: 0.45rem 0.8rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: background 0.2s;
    }
    .btn-action-primary:hover {
      background: #4338CA;
    }

    .btn-action-secondary {
      background: var(--bg-app);
      color: var(--text-primary);
      border: 1px solid var(--border-subtle);
      padding: 0.45rem 0.75rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }

    .btn-action-danger {
      background: rgba(239, 68, 68, 0.12);
      color: #EF4444;
      border: 1px solid rgba(239, 68, 68, 0.3);
      padding: 0.45rem 0.85rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      transition: all 0.2s;
    }
    .btn-action-danger:hover {
      background: #EF4444;
      color: #ffffff;
      border-color: #EF4444;
    }

    .empty-state {
      padding: 4rem 2rem;
      text-align: center;
      border-radius: 20px;
    }

    .empty-icon-box {
      width: 72px;
      height: 72px;
      border-radius: 50%;
      background: rgba(99, 102, 241, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1.25rem auto;
    }
  `]
})
export class LibraryComponent implements OnInit {
  private api = inject<NuevaMenteApi>(NUEVAMENTE_API);
  private stateService = inject(StateService);
  private exportService = inject(ExportService);

  searchTerm = signal<string>('');
  selectedPerfil = signal<string>('');
  selectedFormato = signal<string>('');
  projectsList = signal<RecentProject[]>([]);
  selectedIds = signal<Set<string>>(new Set());
  exitingIds = signal<Set<string>>(new Set());
  toast = signal<ToastState | null>(null);

  ngOnInit(): void {
    this.refreshProjects();
  }

  private refreshProjects(): void {
    const list = this.stateService.getLibraryProjects();
    const isInitialized = localStorage.getItem('nuevamente_library_initialized');

    if (list.length === 0 && !isInitialized) {
      localStorage.setItem('nuevamente_library_initialized', 'true');
      const sampleRequest: AdaptationRequest = {
        documento_titulo: 'Guía Paso a Paso: MsJava',
        documento_contenido: 'MsJava Microservicios',
        perfil_destinatario: 'Desarrollador',
        formato_salida: 'Tutorial',
        nicho_sector: 'Fintech',
        nivel_detalle: 'Didactico'
      };

      const sampleResponse: AdaptationResponse = {
        status: 'exito',
        metadatos: {
          perfil_aplicado: 'Desarrollador',
          formato_generado: 'Tutorial',
          tiempo_estimado_estudio_minutos: 12,
          conceptos_clave: ['MsJava', 'Microservicios', 'Spring Boot']
        },
        contenido_adaptado: {
          titulo: 'Guía Paso a Paso: MsJava Microservicios',
          introduccion_contextualizada: 'Tutorial didáctico estructurado paso a paso a partir de MsJava, optimizado para Desarrollador en el sector Fintech.',
          items: [
            {
              paso: 1,
              titulo: 'MsJava: Fase 1',
              instruccion: 'Microservicios con Spring Boot. Esta etapa asegura la correcta aplicación del requerimiento en el entorno de Fintech.',
              ejemplo: '# Ejecución para MsJava\nrun-process --spec "MsJava" --profile desarrollador',
              advertencia: 'Asegúrate de validar la compatibilidad con el nivel Técnico antes de proceder.'
            },
            {
              paso: 2,
              titulo: 'Microservicios Spring: Fase 2',
              instruccion: 'Agenda del Curso. Esta etapa asegura la correcta aplicación del requerimiento en el entorno de Fintech.'
            },
            {
              paso: 3,
              titulo: 'Agenda: Fase 3',
              instruccion: '1 Spring Boot. Esta etapa asegura la correcta aplicación del requerimiento en el entorno de Fintech.',
              advertencia: 'Asegúrate de validar la compatibilidad con el nivel Técnico antes de proceder.'
            }
          ]
        },
        evaluacion_calidad: {
          anclaje_fuente_score: 0.98,
          claridad_pedagogica: 'Alta',
          observaciones: 'Fidelidad verificada con anclaje RAG en fuente original.'
        },
        almacenamiento_oci: {
          bucket: 'nuevamente-contenidos-educativos',
          objeto_id: 'msjava_tutorial_001.json',
          status_upload: 'completado'
        }
      };

      this.stateService.addProjectFromResponse(sampleRequest, sampleResponse);
      this.projectsList.set(this.stateService.getLibraryProjects());
    } else {
      this.projectsList.set([...list]);
    }
  }

  filteredProjects = computed(() => {
    const query = this.searchTerm().toLowerCase();
    const perf = this.selectedPerfil();
    const fmt = this.selectedFormato();

    return this.projectsList().filter(proj => {
      const matchQuery = proj.nombre.toLowerCase().includes(query);
      const matchPerf = !perf || proj.perfil.includes(perf);
      const matchFmt = !fmt || proj.formato.includes(fmt);
      return matchQuery && matchPerf && matchFmt;
    });
  });

  isAllSelected(): boolean {
    const list = this.filteredProjects();
    if (list.length === 0) return false;
    return list.every(p => this.selectedIds().has(p.id));
  }

  toggleSelectAll(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const current = new Set(this.selectedIds());
    if (checked) {
      this.filteredProjects().forEach(p => current.add(p.id));
    } else {
      this.filteredProjects().forEach(p => current.delete(p.id));
    }
    this.selectedIds.set(current);
  }

  toggleSelectProject(id: string): void {
    const current = new Set(this.selectedIds());
    if (current.has(id)) {
      current.delete(id);
    } else {
      current.add(id);
    }
    this.selectedIds.set(current);
  }

  clearSelection(): void {
    this.selectedIds.set(new Set());
  }

  updateSearch(event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.searchTerm.set(val);
  }

  updatePerfil(event: Event): void {
    const val = (event.target as HTMLSelectElement).value;
    this.selectedPerfil.set(val);
  }

  updateFormato(event: Event): void {
    const val = (event.target as HTMLSelectElement).value;
    this.selectedFormato.set(val);
  }

  viewPdf(proj: RecentProject): void {
    if (proj.response) {
      this.exportService.exportPdfDidactico(proj.response);
    }
  }

  downloadMd(proj: RecentProject): void {
    if (proj.response) {
      this.exportService.exportMarkdown(proj.response);
    }
  }

  moveToTrash(proj: RecentProject): void {
    // 1. Trigger row exit animation
    const exiting = new Set(this.exitingIds());
    exiting.add(proj.id);
    this.exitingIds.set(exiting);

    setTimeout(() => {
      // 2. Perform soft delete to trash
      this.stateService.moveToTrash(proj.id);
      
      const newExiting = new Set(this.exitingIds());
      newExiting.delete(proj.id);
      this.exitingIds.set(newExiting);

      // Remove from selected set if present
      const sel = new Set(this.selectedIds());
      sel.delete(proj.id);
      this.selectedIds.set(sel);

      this.projectsList.set([...this.stateService.getLibraryProjects()]);

      // 3. Show Toast notification (8s duration)
      if (this.toast()?.timeoutId) {
        clearTimeout(this.toast()!.timeoutId);
      }

      const timeoutId = setTimeout(() => {
        this.toast.set(null);
      }, 8000);

      this.toast.set({
        id: proj.id,
        nombre: proj.nombre,
        timeoutId
      });
    }, 250);
  }

  moveBatchToTrash(): void {
    const ids = Array.from(this.selectedIds());
    if (ids.length === 0) return;

    ids.forEach(id => this.stateService.moveToTrash(id));
    this.selectedIds.set(new Set());
    this.projectsList.set([...this.stateService.getLibraryProjects()]);

    if (this.toast()?.timeoutId) {
      clearTimeout(this.toast()!.timeoutId);
    }

    const timeoutId = setTimeout(() => {
      this.toast.set(null);
    }, 8000);

    this.toast.set({
      id: ids[0],
      nombre: `${ids.length} elementos`,
      timeoutId
    });
  }

  undoMoveToTrash(id: string): void {
    this.stateService.restoreFromTrash(id);
    if (this.toast()?.timeoutId) {
      clearTimeout(this.toast()!.timeoutId);
    }
    this.toast.set(null);
    this.projectsList.set([...this.stateService.getLibraryProjects()]);
  }
}
