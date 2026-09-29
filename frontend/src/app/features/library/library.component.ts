import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { StateService, RecentProject } from '../../core/services/state.service';
import { ExportService } from '../../core/services/export.service';
import { AdaptationResponse, AdaptationRequest } from '../../core/models/adaptation.model';

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="library-container">
      <div class="page-header">
        <h1>Biblioteca de Paquetes Educativos</h1>
        <p>Historial completo de documentación adaptada y almacenada en Oracle Cloud Infrastructure.</p>
      </div>

      <!-- Filters & Search Bar -->
      <div class="controls-bar glass-card">
        <div class="search-input-box">
          <span class="search-icon">🔍</span>
          <input 
            type="text" 
            placeholder="Buscar por título de documento..."
            [value]="searchTerm()"
            (input)="updateSearch($event)"
          />
        </div>

        <div class="filters-row">
          <select [value]="selectedPerfil()" (change)="updatePerfil($event)">
            <option value="">Todos los perfiles</option>
            <option value="Principiante">Principiante</option>
            <option value="Desarrollador">Desarrollador</option>
            <option value="Lider Tecnico">Líder Técnico</option>
            <option value="Ejecutivo">Ejecutivo</option>
          </select>

          <select [value]="selectedFormato()" (change)="updateFormato($event)">
            <option value="">Todos los formatos</option>
            <option value="Flashcards">Flashcards</option>
            <option value="Quiz">Quiz</option>
            <option value="Tutorial">Tutorial</option>
            <option value="Resumen Ejecutivo">Resumen Ejecutivo</option>
            <option value="Guion de Clase">Guion de Clase</option>
          </select>
        </div>
      </div>

      <!-- Table of Documents -->
      <div class="table-card glass-card" *ngIf="filteredProjects().length > 0">
        <table class="library-table">
          <thead>
            <tr>
              <th>Documento</th>
              <th>Perfil</th>
              <th>Formato</th>
              <th>Anclaje RAG</th>
              <th>Estado OCI</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let proj of filteredProjects()">
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
                <button class="btn-action-primary" (click)="viewPdf(proj)" title="Visualizar PDF Didáctico">
                  👁️ Visualizar PDF
                </button>
                <button class="btn-action-secondary" (click)="downloadMd(proj)" title="Descargar Markdown">
                  📥 MD
                </button>
                <button class="btn-action-icon" (click)="deleteDoc(proj.id)" title="Eliminar de Biblioteca">
                  🗑️
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      <div class="empty-state glass-card" *ngIf="filteredProjects().length === 0">
        <span class="empty-icon">📂</span>
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
      margin-bottom: 2rem;
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

    .library-table td {
      padding: 1.15rem 1rem;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 0.92rem;
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
    }

    .rag-score {
      color: #10B981;
      font-weight: 700;
    }

    .badge-oci {
      font-size: 0.75rem;
      font-weight: 800;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      background: rgba(16, 185, 129, 0.15);
      color: #059669;
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
      padding: 0.4rem 0.8rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-action-primary:hover {
      background: #4338CA;
    }

    .btn-action-secondary {
      background: var(--bg-app);
      color: var(--text-primary);
      border: 1px solid var(--border-subtle);
      padding: 0.4rem 0.7rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
    }

    .btn-action-icon {
      background: transparent;
      border: none;
      cursor: pointer;
      font-size: 1rem;
      padding: 0.4rem;
    }

    .empty-state {
      padding: 4rem 2rem;
      text-align: center;
      border-radius: 20px;
    }

    .empty-icon {
      font-size: 3rem;
      display: block;
      margin-bottom: 1rem;
    }
  `]
})
export class LibraryComponent implements OnInit {
  private stateService = inject(StateService);
  private exportService = inject(ExportService);

  searchTerm = signal<string>('');
  selectedPerfil = signal<string>('');
  selectedFormato = signal<string>('');
  projectsList = signal<RecentProject[]>([]);

  ngOnInit(): void {
    this.refreshProjects();
  }

  private refreshProjects(): void {
    const list = this.stateService.getProjects();
    if (list.length === 0) {
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
      this.projectsList.set(this.stateService.getProjects());
    } else {
      this.projectsList.set(list);
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

  deleteDoc(id: string): void {
    this.stateService.deleteProject(id);
    this.projectsList.set(this.stateService.getProjects());
  }
}
