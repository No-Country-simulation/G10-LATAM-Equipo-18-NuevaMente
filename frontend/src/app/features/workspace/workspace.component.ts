import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';

import { NuevaMenteApi, NUEVAMENTE_API } from '../../core/api/nuevamente-api';
import { AdaptationRequest, AdaptationResponse, PerfilDestinatario, FormatoSalida, NichoSector, NivelDetalle, RagFuente } from '../../core/models/adaptation.model';

import { PipelineProgressComponent } from './pipeline-progress.component';
import { FlashcardsRendererComponent } from './renderers/flashcards-renderer.component';
import { QuizRendererComponent } from './renderers/quiz-renderer.component';
import { TutorialRendererComponent } from './renderers/tutorial-renderer.component';
import { SummaryRendererComponent } from './renderers/summary-renderer.component';
import { ScriptRendererComponent } from './renderers/script-renderer.component';
import { QualityPanelComponent } from './quality-panel.component';
import { SourcesDrawerComponent } from './sources-drawer.component';
import { OciCardComponent } from './oci-card.component';
import { JsonViewerComponent } from './json-viewer.component';
import { ExportService } from '../../core/services/export.service';
import { StateService } from '../../core/services/state.service';

@Component({
  selector: 'app-workspace',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    PipelineProgressComponent,
    FlashcardsRendererComponent,
    QuizRendererComponent,
    TutorialRendererComponent,
    SummaryRendererComponent,
    ScriptRendererComponent,
    QualityPanelComponent,
    SourcesDrawerComponent,
    OciCardComponent,
    JsonViewerComponent
  ],
  template: `
    <div class="workspace-layout">
      <!-- HEADER / TITLE BAR -->
      <div class="workspace-header">
        <div>
          <span class="value-prop-tag">✨ PROCESAMIENTO RAG DE ALTA FIDELIDAD</span>
          <h2>Workspace de Adaptación Educativa</h2>
          <p class="value-prop-subtitle">De semanas de trabajo instruccional a minutos, con fidelidad total a la fuente.</p>
        </div>

        <!-- Quick Presets -->
        <div class="presets-row">
          <span class="presets-label">Presets Rápidos:</span>
          <button class="preset-btn" (click)="applyPreset('beginner-flashcards')">⚡ Demo Principiante · Flashcards</button>
          <button class="preset-btn" (click)="applyPreset('leader-summary')">📊 Demo Líder · Resumen Ejecutivo</button>
          <button class="preset-btn" (click)="applyPreset('dev-quiz')">🎯 Demo Dev · Quiz Fintech</button>
        </div>
      </div>

      <!-- ZONE 1: INPUT FORM PANEL -->
      <div class="glass-card input-zone-card" *ngIf="!isPipelineRunning() && !currentResponse()">
        <form [formGroup]="adaptForm" (ngSubmit)="runPipeline()">
          <!-- Document Title -->
          <div class="form-group">
            <label for="doc-title">Título de la Documentación Técnica</label>
            <input 
              id="doc-title" 
              type="text" 
              formControlName="documento_titulo" 
              placeholder="Ej. Introducción a la Arquitectura de Redes VCN en OCI"
            />
          </div>

          <!-- Document Input Tabs (Upload vs Text) -->
          <div class="input-tabs-wrapper">
            <div class="tabs-header">
              <button 
                type="button" 
                class="tab-btn" 
                [class.active]="activeTab() === 'upload'"
                (click)="activeTab.set('upload')"
              >
                📁 Cargar Documento (PDF / MD / TXT)
              </button>
              <button 
                type="button" 
                class="tab-btn" 
                [class.active]="activeTab() === 'text'"
                (click)="activeTab.set('text')"
              >
                📝 Pegar Texto Plano
              </button>
            </div>

            <!-- Tab 1: Dropzone Upload -->
            <div class="tab-content" *ngIf="activeTab() === 'upload'">
              <div 
                class="dropzone" 
                [class.dragover]="isDragging()"
                (dragover)="onDragOver($event)"
                (dragleave)="onDragLeave($event)"
                (drop)="onDrop($event)"
                (click)="fileInput.click()"
              >
                <input #fileInput type="file" (change)="onFileSelected($event)" accept=".pdf,.md,.txt" style="display:none;"/>
                <div class="dropzone-content" *ngIf="!uploadedFile()">
                  <span class="drop-icon">☁️</span>
                  <p><strong>Arrastra tu archivo aquí</strong> o haz clic para explorar</p>
                  <span class="drop-hint">Soporta PDF, Markdown (.md) y Texto (.txt) hasta 15MB</span>
                </div>

                <div class="file-preview" *ngIf="uploadedFile()">
                  <span class="file-icon">📄</span>
                  <div class="file-info">
                    <strong>{{ uploadedFile()?.name }}</strong>
                    <span>{{ (uploadedFile()?.size || 0) / 1024 | number:'1.0-0' }} KB · Extracción local lista</span>
                  </div>
                  <button type="button" class="btn-remove-file" (click)="$event.stopPropagation(); removeFile()">✕</button>
                </div>
              </div>
            </div>

            <!-- Tab 2: Textarea -->
            <div class="tab-content" *ngIf="activeTab() === 'text'">
              <textarea 
                formControlName="documento_contenido"
                rows="6"
                placeholder="Pega aquí el contenido de la especificación técnica..."
              ></textarea>
              <div class="char-count">
                {{ (adaptForm.get('documento_contenido')?.value || '').length }} caracteres
              </div>
            </div>
          </div>

          <!-- Visual Selector Cards: Perfil del Destinatario (4) -->
          <div class="selectors-section">
            <label class="section-title">1. Perfil del Destinatario (4 Opciones)</label>
            <div class="cards-selector-grid">
              <div 
                *ngFor="let p of perfiles" 
                class="option-card"
                [class.selected]="adaptForm.get('perfil_destinatario')?.value === p.value"
                (click)="selectPerfil(p.value)"
              >
                <span class="card-icon">{{ p.icon }}</span>
                <div class="card-text">
                  <strong>{{ p.label }}</strong>
                  <p>{{ p.desc }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Visual Selector Cards: Formato Pedagógico (5) -->
          <div class="selectors-section">
            <label class="section-title">2. Formato Pedagógico de Salida (5 Opciones)</label>
            <div class="cards-selector-grid formats-grid">
              <div 
                *ngFor="let f of formatos" 
                class="option-card"
                [class.selected]="adaptForm.get('formato_salida')?.value === f.value"
                (click)="selectFormato(f.value)"
              >
                <span class="card-icon">{{ f.icon }}</span>
                <div class="card-text">
                  <strong>{{ f.label }}</strong>
                  <p>{{ f.desc }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- Sector Nicho & Nivel de Detalle Row -->
          <div class="form-row-dual">
            <!-- Sector Chips (4) -->
            <div class="form-group flex-1">
              <label>3. Nicho / Sector Industrial</label>
              <div class="chips-selector">
                <button 
                  type="button" 
                  *ngFor="let s of sectores" 
                  class="chip-select"
                  [class.active]="adaptForm.get('nicho_sector')?.value === s"
                  (click)="adaptForm.patchValue({ nicho_sector: s })"
                >
                  {{ s }}
                </button>
              </div>
            </div>

            <!-- Segmented Control: Nivel de Detalle (4) -->
            <div class="form-group flex-1">
              <label>4. Nivel de Detalle Pedagógico</label>
              <div class="segmented-control">
                <button 
                  type="button" 
                  *ngFor="let d of niveles" 
                  class="seg-btn"
                  [class.active]="adaptForm.get('nivel_detalle')?.value === d"
                  (click)="adaptForm.patchValue({ nivel_detalle: d })"
                >
                  {{ d }}
                </button>
              </div>
            </div>
          </div>

          <!-- Live Configuration Summary Chips & Primary CTA -->
          <div class="submit-bar">
            <div class="summary-chips">
              <span class="summary-chip">👤 {{ adaptForm.get('perfil_destinatario')?.value }}</span>
              <span class="summary-chip">🎯 {{ adaptForm.get('formato_salida')?.value }}</span>
              <span class="summary-chip">🏢 {{ adaptForm.get('nicho_sector')?.value }}</span>
              <span class="summary-chip">📐 {{ adaptForm.get('nivel_detalle')?.value }}</span>
            </div>

            <button 
              type="submit" 
              class="btn-cta-generate" 
              [disabled]="adaptForm.invalid"
            >
              ⚡ Generar Contenido Educativo →
            </button>
          </div>
        </form>
      </div>

      <!-- ZONE 2: PIPELINE PROGRESS STEPPER -->
      <app-pipeline-progress 
        *ngIf="isPipelineRunning()" 
        (cancelPipeline)="cancelPipeline()"
        (pipelineFinished)="onPipelineFinished()"
      ></app-pipeline-progress>

      <!-- ZONE 3: RESULT VIEWER -->
      <div class="result-viewer-container" *ngIf="currentResponse() && !isPipelineRunning()">
        <!-- Top Controls & Export Bar -->
        <div class="result-action-bar glass-card">
          <button class="btn-back" (click)="resetForm()">← Crear Nueva Adaptación</button>
          
          <div class="export-actions">
            <button class="btn-exp" (click)="exportMarkdown()">📝 Exportar Markdown</button>
            <button class="btn-exp" (click)="exportPdf()">📄 Exportar PDF Didáctico</button>
            <button class="btn-exp" *ngIf="currentResponse()?.metadatos?.formato_generado === 'Flashcards'" (click)="exportAnki()">🎴 Exportar Anki (CSV)</button>
          </div>
        </div>

        <!-- Result Header -->
        <div class="result-header glass-card">
          <div class="header-tags">
            <span class="tag-profile">{{ currentResponse()?.metadatos?.perfil_aplicado }}</span>
            <span class="tag-format">{{ currentResponse()?.metadatos?.formato_generado }}</span>
            <span class="tag-time">⏱️ {{ currentResponse()?.metadatos?.tiempo_estimado_estudio_minutos }} min estudio</span>
          </div>

          <h2>{{ currentResponse()?.contenido_adaptado?.titulo }}</h2>
          <p class="introduccion">{{ currentResponse()?.contenido_adaptado?.introduccion_contextualizada }}</p>

          <!-- Concept Tags Cloud -->
          <div class="concepts-row">
            <span class="c-label">Conceptos Clave:</span>
            <span class="c-tag" *ngFor="let c of currentResponse()?.metadatos?.conceptos_clave">{{ c }}</span>
          </div>
        </div>

        <!-- Renderers via Switch by Format -->
        <div class="renderer-wrapper">
          <ng-container [ngSwitch]="currentResponse()?.metadatos?.formato_generado">
            <!-- Flashcards -->
            <app-flashcards-renderer 
              *ngSwitchCase="'Flashcards'" 
              [items]="getTypedItems()"
            ></app-flashcards-renderer>

            <!-- Quiz -->
            <app-quiz-renderer 
              *ngSwitchCase="'Quiz'" 
              [items]="getTypedItems()"
            ></app-quiz-renderer>

            <!-- Tutorial -->
            <app-tutorial-renderer 
              *ngSwitchCase="'Tutorial'" 
              [items]="getTypedItems()"
            ></app-tutorial-renderer>

            <!-- Resumen Ejecutivo -->
            <app-summary-renderer 
              *ngSwitchCase="'Resumen Ejecutivo'" 
              [items]="getTypedItems()"
            ></app-summary-renderer>

            <!-- Guion de Clase -->
            <app-script-renderer 
              *ngSwitchCase="'Guion de Clase'" 
              [items]="getTypedItems()"
            ></app-script-renderer>

            <!-- Fallback Default -->
            <app-tutorial-renderer 
              *ngSwitchDefault 
              [items]="getTypedItems()"
            ></app-tutorial-renderer>
          </ng-container>
        </div>

        <!-- Panels Row (Quality Panel + OCI Card) -->
        <div class="panels-grid">
          <app-quality-panel [evaluacion]="currentResponse()?.evaluacion_calidad"></app-quality-panel>
          <app-oci-card [oci]="currentResponse()?.almacenamiento_oci"></app-oci-card>
        </div>

        <!-- JSON Viewer Tab -->
        <div class="json-section">
          <app-json-viewer [data]="currentResponse()"></app-json-viewer>
        </div>
      </div>

      <!-- RAG Sources Drawer Modal -->
      <app-sources-drawer 
        [isOpen]="isSourcesDrawerOpen()" 
        [fuente]="selectedFuente()"
        (closeDrawer)="isSourcesDrawerOpen.set(false)"
      ></app-sources-drawer>
    </div>
  `,
  styles: [`
    .workspace-layout {
      max-width: 1100px;
      margin: 0 auto;
    }

    .workspace-header {
      margin-bottom: 2rem;
    }

    .value-prop-tag {
      font-size: 0.75rem;
      font-weight: 800;
      color: #22D3EE;
      letter-spacing: 0.05em;
      margin-bottom: 0.4rem;
      display: block;
    }

    .workspace-header h2 {
      font-size: 2rem;
      font-weight: 800;
      margin-bottom: 0.35rem;
    }

    .value-prop-subtitle {
      color: var(--text-secondary);
      font-size: 1rem;
      margin-bottom: 1.25rem;
    }

    .presets-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      flex-wrap: wrap;
    }

    .presets-label {
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--text-muted);
    }

    .preset-btn {
      padding: 0.4rem 0.85rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .preset-btn:hover {
      border-color: #6366F1;
      background: rgba(99, 102, 241, 0.08);
    }

    .input-zone-card {
      padding: 2rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      margin-bottom: 2rem;
    }

    .form-group {
      margin-bottom: 1.5rem;
    }

    .form-group label {
      display: block;
      font-size: 0.88rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      color: var(--text-primary);
    }

    input[type="text"], textarea {
      width: 100%;
      padding: 0.85rem 1rem;
      border-radius: 12px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-size: 0.95rem;
      outline: none;
    }

    .input-tabs-wrapper {
      margin-bottom: 2rem;
    }

    .tabs-header {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 0.75rem;
    }

    .tab-btn {
      padding: 0.5rem 1rem;
      border-radius: 8px;
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
    }

    .tab-btn.active {
      background: #4F46E5;
      color: #FFFFFF;
      border-color: #4F46E5;
    }

    .dropzone {
      border: 2px dashed var(--border-subtle);
      border-radius: 16px;
      padding: 2.5rem 1.5rem;
      text-align: center;
      cursor: pointer;
      background: var(--bg-app);
      transition: border-color 0.2s;
    }

    .dropzone.dragover {
      border-color: #22D3EE;
      background: rgba(34, 211, 238, 0.05);
    }

    .drop-icon {
      font-size: 2.5rem;
      display: block;
      margin-bottom: 0.5rem;
    }

    .drop-hint {
      font-size: 0.8rem;
      color: var(--text-muted);
      display: block;
      margin-top: 0.25rem;
    }

    .file-preview {
      display: flex;
      align-items: center;
      gap: 1rem;
      justify-content: center;
    }

    .btn-remove-file {
      background: transparent;
      border: none;
      color: #EF4444;
      font-weight: 800;
      cursor: pointer;
    }

    .char-count {
      font-size: 0.78rem;
      color: var(--text-muted);
      text-align: right;
      margin-top: 0.35rem;
    }

    .selectors-section {
      margin-bottom: 2rem;
    }

    .section-title {
      display: block;
      font-size: 0.95rem;
      font-weight: 800;
      margin-bottom: 0.85rem;
      color: var(--text-primary);
    }

    .cards-selector-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 0.85rem;
    }

    .formats-grid {
      grid-template-columns: repeat(5, 1fr);
    }

    .option-card {
      padding: 1rem;
      border-radius: 12px;
      background: var(--bg-app);
      border: 1.5px solid var(--border-subtle);
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      transition: all 0.2s;
    }

    .option-card:hover {
      border-color: #6366F1;
      transform: translateY(-2px);
    }

    .option-card.selected {
      border-color: #4F46E5;
      background: rgba(79, 70, 229, 0.08);
      box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15);
    }

    .card-icon {
      font-size: 1.5rem;
    }

    .card-text strong {
      font-size: 0.88rem;
      display: block;
      color: var(--text-primary);
    }

    .card-text p {
      font-size: 0.75rem;
      color: var(--text-muted);
      margin-top: 0.2rem;
      line-height: 1.3;
    }

    .form-row-dual {
      display: flex;
      gap: 1.5rem;
      margin-bottom: 2rem;
    }

    .flex-1 { flex: 1; }

    .chips-selector {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .chip-select {
      padding: 0.4rem 0.85rem;
      border-radius: 20px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
    }

    .chip-select.active {
      background: #4F46E5;
      color: #FFFFFF;
      border-color: #4F46E5;
    }

    .segmented-control {
      display: flex;
      background: var(--bg-app);
      padding: 0.25rem;
      border-radius: 10px;
      border: 1px solid var(--border-subtle);
    }

    .seg-btn {
      flex: 1;
      padding: 0.4rem 0.5rem;
      border: none;
      background: transparent;
      color: var(--text-secondary);
      font-size: 0.8rem;
      font-weight: 600;
      border-radius: 8px;
      cursor: pointer;
    }

    .seg-btn.active {
      background: var(--bg-surface);
      color: var(--text-primary);
      box-shadow: var(--shadow-sm);
    }

    .submit-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border-subtle);
    }

    .summary-chips {
      display: flex;
      gap: 0.5rem;
    }

    .summary-chip {
      font-size: 0.8rem;
      padding: 0.3rem 0.65rem;
      border-radius: 6px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
    }

    .btn-cta-generate {
      padding: 0.85rem 1.75rem;
      border-radius: 12px;
      background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
      border: none;
      color: #FFFFFF;
      font-size: 1rem;
      font-weight: 800;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
    }

    .btn-cta-generate:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    /* RESULT VIEWER */
    .result-action-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1rem 1.5rem;
      border-radius: 14px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      margin-bottom: 1.5rem;
    }

    .btn-back {
      background: transparent;
      border: 1px solid var(--border-subtle);
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      color: var(--text-primary);
    }

    .export-actions {
      display: flex;
      gap: 0.6rem;
    }

    .btn-exp {
      padding: 0.5rem 0.85rem;
      border-radius: 8px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
    }

    .result-header {
      padding: 2rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      margin-bottom: 2rem;
    }

    .header-tags {
      display: flex;
      gap: 0.6rem;
      margin-bottom: 1rem;
    }

    .tag-profile, .tag-format, .tag-time {
      font-size: 0.78rem;
      font-weight: 800;
      padding: 0.25rem 0.65rem;
      border-radius: 6px;
    }
    .tag-profile { background: rgba(59, 130, 246, 0.12); color: #2563EB; }
    .tag-format { background: rgba(139, 92, 246, 0.12); color: #7C3AED; }
    .tag-time { background: var(--bg-app); color: var(--text-secondary); }

    .result-header h2 {
      font-size: 1.85rem;
      margin-bottom: 0.75rem;
    }

    .introduccion {
      font-size: 1.05rem;
      color: var(--text-secondary);
      line-height: 1.6;
      margin-bottom: 1.5rem;
    }

    .concepts-row {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex-wrap: wrap;
    }

    .c-label {
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--text-muted);
    }

    .c-tag {
      font-size: 0.78rem;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      background: rgba(34, 211, 238, 0.1);
      color: #0284C7;
      font-weight: 600;
    }

    .renderer-wrapper {
      margin-bottom: 2rem;
    }

    .panels-grid {
      display: grid;
      grid-template-columns: 1.5fr 1fr;
      gap: 1.5rem;
      margin-bottom: 2rem;
    }

    @media (max-width: 900px) {
      .cards-selector-grid, .formats-grid { grid-template-columns: 1fr 1fr; }
      .form-row-dual { flex-direction: column; }
      .panels-grid { grid-template-columns: 1fr; }
    }
  `]
})
export class WorkspaceComponent {
  private api = inject<NuevaMenteApi>(NUEVAMENTE_API);
  private fb = inject(FormBuilder);
  private exportService = inject(ExportService);
  private stateService = inject(StateService);

  activeTab = signal<'upload' | 'text'>('text');
  isDragging = signal<boolean>(false);
  uploadedFile = signal<File | null>(null);

  isPipelineRunning = signal<boolean>(false);
  currentResponse = signal<AdaptationResponse | null>(null);

  isSourcesDrawerOpen = signal<boolean>(false);
  selectedFuente = signal<RagFuente | undefined>(undefined);

  perfiles = [
    { value: 'Principiante', label: 'Principiante', icon: '🌱', desc: 'Explicaciones didácticas y analogías sencillas' },
    { value: 'Desarrollador', label: 'Desarrollador', icon: '💻', desc: 'Enfoque en código, APIs y CLI' },
    { value: 'Lider Tecnico', label: 'Líder Técnico', icon: '🏛️', desc: 'Arquitectura, patrones y escalabilidad' },
    { value: 'Ejecutivo', label: 'Ejecutivo', icon: '💼', desc: 'Resumen TL;DR e impacto de negocio' }
  ];

  formatos = [
    { value: 'Flashcards', label: 'Flashcards', icon: '🎴', desc: 'Repaso activo con tarjetas 3D' },
    { value: 'Quiz', label: 'Quiz', icon: '🎯', desc: 'Evaluación con justificaciones' },
    { value: 'Tutorial', label: 'Tutorial', icon: '📘', desc: 'Paso a paso con comandos CLI' },
    { value: 'Resumen Ejecutivo', label: 'Resumen', icon: '📊', desc: 'Impacto de negocio y KPIs' },
    { value: 'Guion de Clase', label: 'Guion Video', icon: '🎙️', desc: 'Escenas cronometradas para clase' }
  ];

  sectores: NichoSector[] = ['Fintech', 'Salud', 'E-commerce', 'General'];
  niveles: NivelDetalle[] = ['Didactico', 'Conciso', 'Tecnico', 'Exhaustivo'];

  adaptForm = this.fb.group({
    documento_titulo: ['Introducción a la Arquitectura de Redes VCN en OCI', [Validators.required]],
    documento_contenido: ['Una Virtual Cloud Network (VCN) en Oracle Cloud Infrastructure es una red privada definida por software...', [Validators.required]],
    perfil_destinatario: ['Desarrollador' as PerfilDestinatario, [Validators.required]],
    formato_salida: ['Tutorial' as FormatoSalida, [Validators.required]],
    nicho_sector: ['Fintech' as NichoSector, [Validators.required]],
    nivel_detalle: ['Tecnico' as NivelDetalle, [Validators.required]]
  });

  selectPerfil(val: string): void {
    this.adaptForm.patchValue({ perfil_destinatario: val as PerfilDestinatario });
  }

  selectFormato(val: string): void {
    this.adaptForm.patchValue({ formato_salida: val as FormatoSalida });
  }

  applyPreset(preset: 'beginner-flashcards' | 'leader-summary' | 'dev-quiz'): void {
    this.activeTab.set('text');
    if (preset === 'beginner-flashcards') {
      this.adaptForm.patchValue({
        documento_titulo: 'Conceptos Básicos de VCN en OCI',
        documento_contenido: 'Una VCN es una red privada en la nube. Permite organizar servidores en subredes públicas y privadas.',
        perfil_destinatario: 'Principiante',
        formato_salida: 'Flashcards',
        nicho_sector: 'General',
        nivel_detalle: 'Didactico'
      });
    } else if (preset === 'leader-summary') {
      this.adaptForm.patchValue({
        documento_titulo: 'Estrategia de Redes Privadas & Seguridad OCI',
        documento_contenido: 'Las redes VCN permiten aislamiento corporativo y reducción de riesgos ante auditorías PCI-DSS.',
        perfil_destinatario: 'Ejecutivo',
        formato_salida: 'Resumen Ejecutivo',
        nicho_sector: 'Fintech',
        nivel_detalle: 'Conciso'
      });
    } else if (preset === 'dev-quiz') {
      this.adaptForm.patchValue({
        documento_titulo: 'Configuración Avanzada de Network Security Groups',
        documento_contenido: 'Los NSGs aplican reglas a nivel de VNIC individual sin alterar la subred completa.',
        perfil_destinatario: 'Desarrollador',
        formato_salida: 'Quiz',
        nicho_sector: 'E-commerce',
        nivel_detalle: 'Tecnico'
      });
    }
  }

  onDragOver(e: DragEvent): void {
    e.preventDefault();
    this.isDragging.set(true);
  }

  onDragLeave(e: DragEvent): void {
    e.preventDefault();
    this.isDragging.set(false);
  }

  onDrop(e: DragEvent): void {
    e.preventDefault();
    this.isDragging.set(false);
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      this.handleFile(e.dataTransfer.files[0]);
    }
  }

  onFileSelected(e: Event): void {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  handleFile(file: File): void {
    this.uploadedFile.set(file);
    const cleanTitle = file.name.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
    const formattedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);
    this.adaptForm.patchValue({ documento_titulo: formattedTitle });
    
    const isTextFile = file.name.endsWith('.txt') || file.name.endsWith('.md') || file.name.endsWith('.json') || file.name.endsWith('.csv') || file.type.startsWith('text/');
    
    if (isTextFile) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = (e.target?.result as string) || '';
        this.adaptForm.patchValue({ documento_contenido: this.sanitizeTechnicalText(text) });
      };
      reader.readAsText(file);
    } else {
      // PDF document parsing via API (PyMuPDF / PyPDF)
      this.api.parsePdf(file).subscribe({
        next: (res) => {
          if (res && res.texto_extraido) {
            const cleanText = this.sanitizeTechnicalText(res.texto_extraido);
            this.adaptForm.patchValue({ documento_contenido: cleanText });
          }
        },
        error: () => {
          // Fallback context based on file title if offline
          const fallbackText = `Documento Técnico: ${formattedTitle}\nCurso de Microservicios con Spring Boot 3 y 4. Arquitectura de Microservicios, APIs REST, Spring Data JPA, Spring Cloud Gateway, Resilience4j Circuit Breakers, Apache Kafka, Observabilidad y Kubernetes.`;
          this.adaptForm.patchValue({ documento_contenido: fallbackText });
        }
      });
    }
  }

  private sanitizeTechnicalText(text: string): string {
    if (!text) return '';
    return text
      .replace(/[^\x20-\x7E\xA0-\xFFáéíóúÁÉÍÓÚñÑ\n\r\t]/g, ' ')
      .replace(/[^\S\r\n]{2,}/g, ' ')
      .trim();
  }

  removeFile(): void {
    this.uploadedFile.set(null);
  }

  runPipeline(): void {
    if (this.adaptForm.invalid) return;
    this.isPipelineRunning.set(true);
    this.currentResponse.set(null);
  }

  cancelPipeline(): void {
    this.isPipelineRunning.set(false);
  }

  onPipelineFinished(): void {
    const req = this.adaptForm.value as AdaptationRequest;
    this.api.adaptContent(req).subscribe(res => {
      this.currentResponse.set(res);
      this.isPipelineRunning.set(false);
      localStorage.setItem('nuevamente_library_initialized', 'true');
      this.stateService.addProjectFromResponse(req, res);
    });
  }

  resetForm(): void {
    this.currentResponse.set(null);
    this.isPipelineRunning.set(false);
  }

  getTypedItems(): any[] {
    return this.currentResponse()?.contenido_adaptado?.items || [];
  }

  exportMarkdown(): void {
    if (this.currentResponse()) {
      this.exportService.exportMarkdown(this.currentResponse()!);
    }
  }

  exportPdf(): void {
    if (this.currentResponse()) {
      this.exportService.exportPdfDidactico(this.currentResponse()!);
    }
  }

  exportAnki(): void {
    if (this.currentResponse()) {
      this.exportService.exportAnkiCsv(this.currentResponse()!);
    }
  }
}
