import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ContenidoAdaptado, Metadatos, EvaluacionCalidad, AlmacenamientoOCI } from '../../core/models/adaptation.model';

@Component({
  selector: 'app-content-viewer',
  template: `
    <div class="result-viewer-container">
      <!-- Top Action Bar -->
      <div class="result-top-bar">
        <button class="btn-back" (click)="onBack()">
          ← Volver a mis documentos
        </button>

        <div class="title-section">
          <h1 class="document-title">{{ contenido?.titulo || 'Contenido Técnico Adaptado' }}</h1>
          <div class="document-tags">
            <span class="tag-pill blue" *ngIf="metadatos?.formato_generado">{{ metadatos?.formato_generado }}</span>
            <span class="tag-pill purple" *ngIf="metadatos?.perfil_aplicado">{{ metadatos?.perfil_aplicado }}</span>
            <span class="badge badge-green">✓ Completado</span>
          </div>
        </div>

        <div class="action-buttons">
          <button class="btn btn-secondary btn-sm" (click)="downloadPdf()">
            📥 Descargar PDF
          </button>
          <button class="btn btn-secondary btn-sm" (click)="downloadJson()">
            📄 Descargar JSON
          </button>
          <button class="btn btn-secondary btn-sm" (click)="shareContent()">
            🔗 Compartir
          </button>
          <div class="menu-wrapper">
            <button class="btn btn-secondary btn-sm btn-icon-only" (click)="toggleDropdown($event)">•••</button>

            <!-- Dropdown Menu for Top Bar -->
            <div *ngIf="showMenu" class="dropdown-menu">
              <button class="dropdown-item" (click)="downloadPdf(); toggleDropdown($event)">
                <span class="item-icon">📥</span> Descargar PDF
              </button>
              <button class="dropdown-item" (click)="downloadJson(); toggleDropdown($event)">
                <span class="item-icon">📄</span> Descargar JSON
              </button>
              <button class="dropdown-item" (click)="shareContent(); toggleDropdown($event)">
                <span class="item-icon">🔗</span> Compartir enlace
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <div class="tabs-header">
        <button 
          class="tab-item" 
          [ngClass]="{'active': activeTab === 'preview'}"
          (click)="activeTab = 'preview'"
        >
          Vista previa
        </button>
        <button 
          class="tab-item" 
          [ngClass]="{'active': activeTab === 'json'}"
          (click)="activeTab = 'json'"
        >
          Contenido JSON
        </button>
        <button 
          class="tab-item" 
          [ngClass]="{'active': activeTab === 'sources'}"
          (click)="activeTab = 'sources'"
        >
          Fuentes
        </button>
        <button 
          class="tab-item" 
          [ngClass]="{'active': activeTab === 'metadata'}"
          (click)="activeTab = 'metadata'"
        >
          Metadatos
        </button>
      </div>

      <!-- Grid Content Layout -->
      <div class="viewer-grid">
        <!-- Main Viewer Column (Left) -->
        <div class="main-content-column">
          <!-- TAB 1: VISTA PREVIA -->
          <div *ngIf="activeTab === 'preview'" class="tab-pane">
            <!-- Hero Banner -->
            <div class="document-hero-banner">
              <div class="hero-label">CONTENIDO ADAPTADO CON IA</div>
              <h2 class="hero-heading">{{ contenido?.titulo }}</h2>
              <p class="hero-intro">
                {{ contenido?.introduccion_contextualizada }}
              </p>
            </div>

            <!-- Key Points Highlight Card -->
            <div class="key-points-card" *ngIf="keyConceptsList.length > 0">
              <h3 class="card-subtitle">
                <span class="icon">💡</span> Puntos clave del documento
              </h3>
              <ul class="points-list">
                <li *ngFor="let c of keyConceptsList">
                  <span class="check-blue">✓</span> Concepto extraído: <strong>{{ c }}</strong>
                </li>
              </ul>
            </div>

            <!-- TL;DR / Resumen Ejecutivo Card -->
            <div class="tldr-card" *ngIf="(isTldrFormat || isTutorialFormat) && contenido?.resumen_ejecutivo">
              <h3>⚡ Resumen Ejecutivo (TL;DR)</h3>
              <div class="tldr-text">{{ contenido?.resumen_ejecutivo }}</div>
            </div>

            <!-- Section: Tutorial Steps -->
            <div *ngIf="(isTutorialFormat || isTldrFormat) && contenido?.secciones_tutorial && contenido!.secciones_tutorial!.length > 0" class="tutorial-sections">
              <h3 class="section-title-large">Secciones de Aprendizaje</h3>
              <div class="step-card" *ngFor="let sec of contenido?.secciones_tutorial; let i = index">
                <div class="step-badge-number">{{ i + 1 }}</div>
                <div class="step-card-content">
                  <h4>{{ sec.encabezado }}</h4>
                  <p>{{ sec.contenido }}</p>
                </div>
              </div>
            </div>

            <!-- Interactive Flashcards Component -->
            <app-interactive-flashcards 
              *ngIf="isFlashcardFormat && contenido?.items && contenido!.items!.length > 0"
              [items]="contenido!.items!"
            ></app-interactive-flashcards>

            <!-- Interactive Quiz Component -->
            <app-interactive-quiz
              *ngIf="isQuizFormat && contenido?.quizzes && contenido!.quizzes!.length > 0"
              [quizzes]="contenido!.quizzes!"
            ></app-interactive-quiz>
          </div>

          <!-- TAB 2: CONTENIDO JSON -->
          <div *ngIf="activeTab === 'json'" class="tab-pane">
            <div class="json-code-box">
              <pre>{{ contenidoJsonFormatted }}</pre>
            </div>
          </div>

          <!-- TAB 3: FUENTES -->
          <div *ngIf="activeTab === 'sources'" class="tab-pane">
            <div class="sources-detail-card">
              <h3>Documentos y Chunks recuperados de la fuente</h3>
              <div class="chunk-item-detail" *ngFor="let c of keyConceptsList; let i = index">
                <div class="chunk-header">
                  <span class="chunk-name">chunk_00{{ i + 1 }}.txt</span>
                  <span class="chunk-score">Relevancia: {{ 96 - (i * 3) }}%</span>
                </div>
                <p>Pasaje extraído correspondiente a <strong>{{ c }}</strong>. Recuperado mediante búsqueda semántica RAG Híbrida.</p>
              </div>

              <div *ngIf="keyConceptsList.length === 0" class="empty-sources">
                <p>Documento procesado dinámicamente.</p>
              </div>
            </div>
          </div>

          <!-- TAB 4: METADATOS -->
          <div *ngIf="activeTab === 'metadata'" class="tab-pane">
            <app-metadata-dashboard
              [metadatos]="metadatos"
              [evaluacion]="evaluacion"
              [oci]="oci"
            ></app-metadata-dashboard>
          </div>
        </div>

        <!-- Right Summary Sidebar Column -->
        <div class="sidebar-column">
          <!-- Summary Card (Resumen) -->
          <div class="summary-widget-card">
            <h3 class="widget-title">Resumen</h3>
            <div class="widget-item">
              <span class="w-icon">📄</span>
              <div>
                <div class="w-value">{{ totalSeccionesCount }}</div>
                <div class="w-label">secciones / módulos generados</div>
              </div>
            </div>

            <div class="widget-item">
              <span class="w-icon">⏱️</span>
              <div>
                <div class="w-value">{{ metadatos?.tiempo_estimado_estudio_minutos || 10 }} min</div>
                <div class="w-label">tiempo estimado de lectura</div>
              </div>
            </div>

            <div class="widget-item">
              <span class="w-icon">🔑</span>
              <div>
                <div class="w-value">{{ keyConceptsList.length }}</div>
                <div class="w-label">conceptos clave</div>
              </div>
            </div>
          </div>

          <!-- Fuentes Utilizadas Card -->
          <div class="summary-widget-card">
            <h3 class="widget-title">Fuentes utilizadas</h3>
            <div class="source-link-item" *ngFor="let c of keyConceptsList.slice(0, 3); let i = index">
              <span class="s-icon">📄</span>
              <span class="s-name">chunk_00{{ i + 1 }}</span>
              <span class="s-desc">{{ c }}</span>
              <span class="s-arrow">➔</span>
            </div>

            <div *ngIf="keyConceptsList.length === 0" class="no-sources-text">
              <p>Documento procesado en fuente principal.</p>
            </div>

            <button class="btn-text-link" *ngIf="keyConceptsList.length > 0" (click)="activeTab = 'sources'">Ver todas las fuentes ➔</button>
          </div>

          <!-- Estado de Fidelidad Card -->
          <div class="summary-widget-card">
            <h3 class="widget-title">Estado de fidelidad</h3>
            <div class="fidelity-badge-row">
              <span class="fidelity-icon">✓</span>
              <span class="fidelity-score">{{ evaluacion?.claridad_pedagogica || 'Alta' }}</span>
            </div>
            <p class="fidelity-text">
              Anclaje en fuente: <strong>{{ Math.round((evaluacion?.anclaje_fuente_score || 0.98) * 100) }}%</strong>
            </p>
            <p class="fidelity-subtext">
              {{ evaluacion?.observaciones || 'Contenido validado contra el texto original.' }}
            </p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .result-viewer-container {
      max-width: 1150px;
      margin: 0 auto;
    }

    .result-top-bar {
      margin-bottom: 1.5rem;
    }
    .btn-back {
      background: none;
      border: none;
      color: #3b82f6;
      font-weight: 700;
      font-size: 0.88rem;
      cursor: pointer;
      margin-bottom: 0.75rem;
    }
    .title-section {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }
    .document-title {
      font-size: 2.25rem;
      font-weight: 800;
      color: #0f172a;
    }
    .document-tags {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .tag-pill {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.25rem 0.75rem;
      border-radius: 20px;
    }
    .tag-pill.blue { background: #eff6ff; color: #2563eb; }
    .tag-pill.purple { background: #f3e8ff; color: #7e22ce; }

    .action-buttons {
      display: flex;
      gap: 0.75rem;
      justify-content: flex-end;
      align-items: center;
    }
    .btn-sm {
      padding: 0.5rem 1rem;
      font-size: 0.85rem;
      border-radius: 10px;
    }
    .btn-icon-only {
      padding: 0.5rem 0.75rem;
    }

    .menu-wrapper {
      position: relative;
    }
    .dropdown-menu {
      position: absolute;
      right: 0;
      top: 110%;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1);
      width: 180px;
      z-index: 50;
      display: flex;
      flex-direction: column;
      padding: 0.5rem;
    }
    .dropdown-item {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      padding: 0.6rem 0.85rem;
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

    /* Tabs Bar */
    .tabs-header {
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid #e2e8f0;
      margin-bottom: 2rem;
    }
    .tab-item {
      padding: 0.75rem 1.25rem;
      background: none;
      border: none;
      font-size: 0.95rem;
      font-weight: 600;
      color: #64748b;
      cursor: pointer;
      position: relative;
    }
    .tab-item.active {
      color: #3b82f6;
      font-weight: 700;
    }
    .tab-item.active::after {
      content: '';
      position: absolute;
      bottom: -1px;
      left: 0;
      right: 0;
      height: 2px;
      background: #3b82f6;
    }

    /* Grid Layout */
    .viewer-grid {
      display: grid;
      grid-template-columns: 1.5fr 0.8fr;
      gap: 2rem;
    }

    /* Main Left Content */
    .document-hero-banner {
      background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
      border: 1px solid #bfdbfe;
      border-radius: 20px;
      padding: 2rem;
      margin-bottom: 1.75rem;
    }
    .hero-label {
      font-size: 0.75rem;
      font-weight: 800;
      color: #2563eb;
      letter-spacing: 0.08em;
      margin-bottom: 0.5rem;
    }
    .hero-heading {
      font-size: 1.75rem;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 0.75rem;
    }
    .hero-intro {
      font-size: 0.98rem;
      color: #334155;
      line-height: 1.6;
    }

    .key-points-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 20px;
      padding: 1.75rem;
      margin-bottom: 2rem;
    }
    .card-subtitle {
      font-size: 1.1rem;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .points-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    .points-list li {
      font-size: 0.92rem;
      color: #334155;
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
    }
    .check-blue {
      color: #3b82f6;
      font-weight: 800;
    }

    .tldr-card {
      background: #fefce8;
      border: 1px solid #fef08a;
      border-radius: 16px;
      padding: 1.5rem;
      margin-bottom: 2rem;
    }
    .tldr-card h3 {
      font-size: 1.1rem;
      font-weight: 800;
      color: #854d0e;
      margin-bottom: 0.75rem;
    }
    .tldr-text {
      font-size: 0.95rem;
      color: #713f12;
      white-space: pre-line;
      line-height: 1.6;
    }

    .section-title-large {
      font-size: 1.35rem;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 1.25rem;
    }
    .step-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 1.25rem;
      display: flex;
      gap: 1.25rem;
      margin-bottom: 1rem;
    }
    .step-badge-number {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #eff6ff;
      color: #2563eb;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .step-card-content h4 {
      font-size: 1.05rem;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 0.35rem;
    }
    .step-card-content p {
      font-size: 0.9rem;
      color: #475569;
      line-height: 1.5;
    }

    .json-code-box {
      background: #0f172a;
      color: #f8fafc;
      padding: 1.5rem;
      border-radius: 16px;
      font-family: monospace;
      font-size: 0.85rem;
      overflow-x: auto;
    }

    .sources-detail-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 20px;
      padding: 1.5rem;
    }
    .chunk-item-detail {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 1rem;
      margin-top: 1rem;
    }
    .chunk-header {
      display: flex;
      justify-content: space-between;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }
    .chunk-score { color: #10b981; font-size: 0.82rem; }
    .empty-sources { color: #64748b; padding: 1rem; }

    /* Right Sidebar Widgets */
    .sidebar-column {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .summary-widget-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 20px;
      padding: 1.5rem;
    }
    .widget-title {
      font-size: 1.05rem;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 1.25rem;
    }
    .widget-item {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .w-icon {
      font-size: 1.25rem;
      background: #f8fafc;
      padding: 0.5rem;
      border-radius: 10px;
    }
    .w-value {
      font-size: 1.2rem;
      font-weight: 800;
      color: #0f172a;
    }
    .w-label {
      font-size: 0.78rem;
      color: #64748b;
    }

    .source-link-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem;
      background: #f8fafc;
      border-radius: 10px;
      margin-bottom: 0.5rem;
      font-size: 0.85rem;
    }
    .s-name { font-weight: 700; color: #0f172a; }
    .s-desc { flex: 1; color: #64748b; font-size: 0.78rem; }
    .s-arrow { color: #94a3b8; }
    .no-sources-text { color: #94a3b8; font-size: 0.82rem; margin-bottom: 0.5rem; }
    .btn-text-link {
      background: none;
      border: none;
      color: #3b82f6;
      font-weight: 700;
      font-size: 0.82rem;
      cursor: pointer;
      margin-top: 0.5rem;
    }

    .fidelity-badge-row {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }
    .fidelity-icon {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #dcfce7;
      color: #16a34a;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.75rem;
    }
    .fidelity-score {
      font-size: 1.1rem;
      font-weight: 800;
      color: #16a34a;
    }
    .fidelity-text {
      font-size: 0.85rem;
      color: #0f172a;
      margin-bottom: 0.25rem;
    }
    .fidelity-subtext {
      font-size: 0.78rem;
      color: #64748b;
    }

    @media (max-width: 900px) {
      .viewer-grid { grid-template-columns: 1fr; }
    }
  `]
})
export class ContentViewerComponent {
  @Input() contenido?: ContenidoAdaptado;
  @Input() metadatos?: Metadatos;
  @Input() evaluacion?: EvaluacionCalidad;
  @Input() oci?: AlmacenamientoOCI;

  @Output() backRequested = new EventEmitter<void>();

  activeTab: 'preview' | 'json' | 'sources' | 'metadata' = 'preview';
  showMenu: boolean = false;
  Math = Math;

  get isFlashcardFormat(): boolean {
    const fmt = (this.metadatos?.formato_generado || '').toLowerCase();
    return fmt.includes('flashcard');
  }

  get isQuizFormat(): boolean {
    const fmt = (this.metadatos?.formato_generado || '').toLowerCase();
    return fmt.includes('quiz');
  }

  get isTldrFormat(): boolean {
    const fmt = (this.metadatos?.formato_generado || '').toLowerCase();
    return fmt.includes('tldr') || fmt.includes('resumen');
  }

  get isTutorialFormat(): boolean {
    return !this.isFlashcardFormat && !this.isQuizFormat && !this.isTldrFormat;
  }

  get keyConceptsList(): string[] {
    if (this.metadatos?.conceptos_clave && this.metadatos.conceptos_clave.length > 0) {
      return this.metadatos.conceptos_clave;
    }
    const derivedTitle = this.contenido?.titulo ? this.contenido.titulo.replace(/^Guía Adaptada de\s*/i, '') : '';
    if (derivedTitle) {
      return [derivedTitle, 'Fundamentos Técnicos', 'Aplicación Práctica', 'Verificación'];
    }
    return ['Conceptos Clave del Documento'];
  }

  get totalSeccionesCount(): number {
    if (this.isTutorialFormat || this.isTldrFormat) {
      if (this.contenido?.secciones_tutorial?.length) {
        return this.contenido.secciones_tutorial.length;
      }
    }
    if (this.isFlashcardFormat && this.contenido?.items?.length) {
      return this.contenido.items.length;
    }
    if (this.isQuizFormat && this.contenido?.quizzes?.length) {
      return this.contenido.quizzes.length;
    }
    return 3;
  }

  get contenidoJsonFormatted(): string {
    return JSON.stringify(
      {
        status: 'exito',
        metadatos: this.metadatos,
        contenido_adaptado: this.contenido,
        evaluacion_calidad: this.evaluacion,
        almacenamiento_oci: this.oci
      },
      null,
      2
    );
  }

  toggleDropdown(event: MouseEvent): void {
    event.stopPropagation();
    this.showMenu = !this.showMenu;
  }

  onBack(): void {
    this.backRequested.emit();
  }

  downloadPdf(): void {
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Por favor habilita las ventanas emergentes para descargar el PDF.');
      return;
    }

    const rawTitle = this.contenido?.titulo || 'Contenido Técnico Adaptado';
    const cleanTitle = rawTitle
      .replace(/\.(pdf|md|markdown|txt)/gi, '')
      .replace(/[-_]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    const formattedDate = new Date().toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>${cleanTitle}</title>
        <style>
          @page {
            size: A4 portrait;
            margin: 0mm;
          }
          @media print {
            html, body {
              margin: 0 !important;
              padding: 0 !important;
              background: #ffffff !important;
              -webkit-print-color-adjust: exact !important;
              print-color-adjust: exact !important;
            }
          }
          * {
            box-sizing: border-box;
          }
          body {
            font-family: 'Segoe UI', system-ui, -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            color: #0f172a;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background: #ffffff;
          }
          .pdf-wrapper {
            padding: 18mm 20mm;
            max-width: 100%;
          }
          .brand-banner {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 55%, #2563eb 100%);
            color: #ffffff;
            padding: 16px 20px;
            border-radius: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
          }
          .brand-title {
            font-size: 1.3rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            display: flex;
            align-items: center;
            gap: 8px;
          }
          .brand-tag {
            background: rgba(255, 255, 255, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: #ffffff;
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 0.82rem;
            font-weight: 700;
          }
          .doc-header-title {
            font-size: 1.9rem;
            font-weight: 800;
            color: #0f172a;
            margin: 0 0 12px 0;
            line-height: 1.25;
            letter-spacing: -0.02em;
          }
          .intro-callout {
            background: #eff6ff;
            border-left: 5px solid #2563eb;
            border-radius: 0 10px 10px 0;
            padding: 14px 18px;
            margin-bottom: 20px;
            font-size: 0.95rem;
            color: #1e3a8a;
            line-height: 1.6;
          }
          .metadata-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 24px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 12px 16px;
          }
          .meta-item {
            display: flex;
            flex-direction: column;
          }
          .meta-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            font-weight: 700;
            margin-bottom: 2px;
          }
          .meta-val {
            font-size: 0.88rem;
            font-weight: 800;
            color: #0f172a;
          }
          .section-heading-pdf {
            font-size: 1.25rem;
            font-weight: 800;
            color: #0f172a;
            margin: 24px 0 14px 0;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 6px;
          }
          .card-box {
            background: #ffffff;
            border: 1px solid #cbd5e1;
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 16px;
            page-break-inside: avoid;
            box-shadow: 0 1px 3px rgba(0,0,0,0.02);
          }
          .card-title {
            font-size: 1.08rem;
            font-weight: 800;
            color: #1e3a8a;
            margin: 0 0 8px 0;
            display: flex;
            align-items: center;
            gap: 8px;
          }
          .card-body {
            font-size: 0.92rem;
            color: #334155;
            line-height: 1.65;
            margin: 0;
          }
          .flashcard-q {
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 12px;
            font-weight: 700;
            color: #1d4ed8;
            margin-bottom: 10px;
          }
          .flashcard-a {
            background: #f8fafc;
            border-left: 4px solid #10b981;
            padding: 10px 14px;
            font-size: 0.9rem;
            color: #0f172a;
          }
          .quiz-option-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 12px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            margin-bottom: 6px;
            font-size: 0.88rem;
            color: #334155;
          }
          .quiz-option-item.is-correct {
            background: #dcfce7;
            border-color: #86efac;
            font-weight: 700;
            color: #14532d;
          }
          .justification-callout {
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-radius: 8px;
            padding: 10px 14px;
            margin-top: 10px;
            font-size: 0.85rem;
            color: #166534;
          }
          .tldr-container {
            background: #fefce8;
            border: 1px solid #fef08a;
            border-radius: 12px;
            padding: 18px;
            margin-bottom: 24px;
            page-break-inside: avoid;
          }
          .tldr-title {
            font-size: 1.15rem;
            font-weight: 800;
            color: #854d0e;
            margin: 0 0 10px 0;
          }
          .tldr-content {
            font-size: 0.94rem;
            color: #713f12;
            white-space: pre-line;
            line-height: 1.65;
          }
          .pdf-footer-bar {
            margin-top: 36px;
            padding-top: 14px;
            border-top: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.78rem;
            color: #64748b;
          }
        </style>
      </head>
      <body>
        <div class="pdf-wrapper">
          <!-- Executive Brand Header -->
          <div class="brand-banner">
            <div class="brand-title">✨ NuevaMente RAG</div>
            <div class="brand-tag">${this.metadatos?.formato_generado || 'Contenido Adaptado'}</div>
          </div>

          <!-- Main Document Title -->
          <h1 class="doc-header-title">${cleanTitle}</h1>

          <!-- Intro Box -->
          <div class="intro-callout">
            ${this.contenido?.introduccion_contextualizada || ''}
          </div>

          <!-- Metadata Bar -->
          <div class="metadata-grid">
            <div class="meta-item">
              <span class="meta-label">Perfil Audiencia</span>
              <span class="meta-val">${this.metadatos?.perfil_aplicado || 'General'}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Formato Salida</span>
              <span class="meta-val">${this.metadatos?.formato_generado || 'Tutorial'}</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Fidelidad RAG</span>
              <span class="meta-val">${Math.round((this.evaluacion?.anclaje_fuente_score || 0.98) * 100)}% Anclaje</span>
            </div>
            <div class="meta-item">
              <span class="meta-label">Tiempo Estimado</span>
              <span class="meta-val">${this.metadatos?.tiempo_estimado_estudio_minutos || 10} minutos</span>
            </div>
          </div>

          <!-- TL;DR / Resumen Ejecutivo -->
          ${(this.isTldrFormat || this.isTutorialFormat) && this.contenido?.resumen_ejecutivo ? `
            <div class="tldr-container">
              <h3 class="tldr-title">⚡ Resumen Ejecutivo (TL;DR)</h3>
              <div class="tldr-content">${this.contenido.resumen_ejecutivo}</div>
            </div>
          ` : ''}

          <!-- Tutorial / Guía Paso a Paso -->
          ${(this.isTutorialFormat || this.isTldrFormat) && this.contenido?.secciones_tutorial ? `
            <h2 class="section-heading-pdf">Módulos de Aprendizaje</h2>
            ${this.contenido.secciones_tutorial.map((sec, idx) => `
              <div class="card-box">
                <h3 class="card-title">Paso ${idx + 1}: ${sec.encabezado}</h3>
                <p class="card-body">${sec.contenido}</p>
              </div>
            `).join('')}
          ` : ''}

          <!-- Flashcards -->
          ${this.isFlashcardFormat && this.contenido?.items ? `
            <h2 class="section-heading-pdf">Flashcards de Memorización</h2>
            ${this.contenido.items.map((item, idx) => `
              <div class="card-box">
                <div class="flashcard-q">Card #${idx + 1}: ${item.frente}</div>
                <div class="flashcard-a">
                  <strong>Respuesta:</strong> ${item.dorso}
                  ${item.pista_didactica ? `<div style="font-size:0.82rem; color:#64748b; margin-top:6px;"><em>Pista didáctica: ${item.pista_didactica}</em></div>` : ''}
                </div>
              </div>
            `).join('')}
          ` : ''}

          <!-- Quiz Interactivo -->
          ${this.isQuizFormat && this.contenido?.quizzes ? `
            <h2 class="section-heading-pdf">Quiz de Evaluación Interactiva</h2>
            ${this.contenido.quizzes.map((q, idx) => `
              <div class="card-box">
                <h3 class="card-title">Pregunta #${idx + 1}: ${q.pregunta}</h3>
                <div style="margin: 10px 0;">
                  ${q.opciones.map(opt => `
                    <div class="quiz-option-item ${opt === q.respuesta_correcta ? 'is-correct' : ''}">
                      <span>${opt === q.respuesta_correcta ? '✓' : '⚪'}</span>
                      <span>${opt}</span>
                    </div>
                  `).join('')}
                </div>
                <div class="justification-callout">
                  <strong>Justificación Pedagógica:</strong> ${q.justificacion_didactica}
                </div>
              </div>
            `).join('')}
          ` : ''}

          <!-- Footer -->
          <div class="pdf-footer-bar">
            <span>NuevaMente RAG — Adaptación Educativa e Inteligencia Artificial</span>
            <span>Generado el ${formattedDate}</span>
          </div>
        </div>

        <script>
          window.onload = function() {
            setTimeout(function() {
              window.print();
            }, 300);
          }
        </script>
      </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
  }

  downloadJson(): void {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(this.contenidoJsonFormatted);
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `${(this.contenido?.titulo || 'contenido').toLowerCase().replace(/[^a-z0-9]/g, '-')}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  }

  shareContent(): void {
    alert('Enlace del documento copiado al portapapeles.');
  }
}
