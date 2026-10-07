import { Component, signal, computed, inject, ViewChild, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { toSignal } from '@angular/core/rxjs-interop';

import { NuevaMenteApi, NUEVAMENTE_API } from '../../core/api/nuevamente-api';
import { AdaptationRequest, AdaptationResponse, PerfilDestinatario, FormatoSalida, NichoSector, NivelDetalle, NivelCantidad, RagFuente } from '../../core/models/adaptation.model';
import { CONTENT_QUANTITY_CONFIG, getQuantityHintText, getTargetItemCount } from '../../core/config/content-quantity.config';

import { PipelineProgressComponent } from './pipeline-progress.component';
import { GenerationLoaderComponent } from './generation-loader.component';
import { FlashcardsRendererComponent } from './renderers/flashcards-renderer.component';
import { QuizRendererComponent } from './renderers/quiz-renderer.component';
import { TutorialRendererComponent } from './renderers/tutorial-renderer.component';
import { SummaryRendererComponent } from './renderers/summary-renderer.component';
import { ScriptRendererComponent } from './renderers/script-renderer.component';
import { SelloConfianzaComponent } from './sello-confianza.component';
import { SourcesDrawerComponent } from './sources-drawer.component';
import { JsonDrawerComponent } from './json-drawer.component';
import { ExportService } from '../../core/services/export.service';
import { StateService } from '../../core/services/state.service';
import { DocumentService } from '../../core/services/document.service';
import { AppDocument } from '../../core/models/document.model';

@Component({
  selector: 'app-workspace',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    PipelineProgressComponent,
    GenerationLoaderComponent,
    FlashcardsRendererComponent,
    QuizRendererComponent,
    TutorialRendererComponent,
    SummaryRendererComponent,
    ScriptRendererComponent,
    SelloConfianzaComponent,
    SourcesDrawerComponent,
    JsonDrawerComponent
  ],
  template: `
    <div class="workspace-layout">
      <!-- HERO & PRESETS (Only visible when no result is currently shown) -->
      <div class="workspace-header" *ngIf="!currentResponse() && !isPipelineRunning()">
        <div>
          <span class="value-prop-tag">✨ PROCESAMIENTO RAG DE ALTA FIDELIDAD</span>
          <h2>Workspace de Adaptación Educativa</h2>
          <p class="value-prop-subtitle">De semanas de trabajo instruccional a minutos, con fidelidad total a la fuente.</p>
        </div>

        <!-- Quick Presets -->
        <div class="presets-row">
          <span class="presets-label">Presets Rápidos:</span>
          <button type="button" class="preset-btn" (click)="applyPreset('beginner-flashcards')">⚡ Demo Principiante · Flashcards (20)</button>
          <button type="button" class="preset-btn" (click)="applyPreset('leader-summary')">📊 Demo Líder · Resumen (5)</button>
          <button type="button" class="preset-btn" (click)="applyPreset('dev-quiz')">🎯 Demo Dev · Quiz (10)</button>
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

          <!-- Document Input Tabs (Upload vs Text vs From Mis Documentos) -->
          <div class="input-tabs-wrapper">
            <div class="tabs-header">
              <button 
                type="button" 
                class="tab-btn" 
                [class.active]="activeTab() === 'upload'"
                (click)="activeTab.set('upload')"
              >
                📂 Cargar Documento (PDF / MD / TXT)
              </button>
              <button 
                type="button" 
                class="tab-btn" 
                [class.active]="activeTab() === 'text'"
                (click)="activeTab.set('text')"
              >
                📝 Pegar Texto Plano
              </button>
              <button 
                type="button" 
                class="tab-btn" 
                [class.active]="activeTab() === 'from_documents'"
                (click)="activeTab.set('from_documents')"
              >
                📚 Desde Mis Documentos
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
                  <span class="drop-hint">Soporta PDF, Markdown (.md) y Texto (.txt) hasta 20MB</span>
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

            <!-- Tab 3: From Mis Documentos Selector -->
            <div class="tab-content" *ngIf="activeTab() === 'from_documents'">
              <!-- Selected Document Card -->
              <div class="selected-document-card" *ngIf="selectedWorkspaceDoc()">
                <div class="selected-doc-icon">
                  <span *ngIf="selectedWorkspaceDoc()?.type === 'pdf'">📕</span>
                  <span *ngIf="selectedWorkspaceDoc()?.type === 'md'">📘</span>
                  <span *ngIf="selectedWorkspaceDoc()?.type === 'txt'">📄</span>
                </div>
                <div class="selected-doc-info">
                  <div class="doc-badge-row">
                    <span class="type-pill">{{ selectedWorkspaceDoc()?.type?.toUpperCase() }}</span>
                    <span class="status-ready">✓ Listo para procesamiento RAG</span>
                  </div>
                  <strong>{{ selectedWorkspaceDoc()?.name }}</strong>
                  <span class="doc-meta-text">{{ formatSize(selectedWorkspaceDoc()?.size || 0) }} · Cargado el {{ formatDate(selectedWorkspaceDoc()?.uploadDate || '') }}</span>
                </div>
                <button type="button" class="btn-clear-doc" (click)="clearSelectedWorkspaceDoc()">✕ Cambiar</button>
              </div>

              <!-- Interactive Document Picker Grid -->
              <div class="document-picker-wrapper" *ngIf="!selectedWorkspaceDoc()">
                <div class="picker-search-bar">
                  <input 
                    type="text" 
                    placeholder="Buscar documento en tu almacén por nombre o etiqueta..." 
                    [value]="pickerSearchQuery()"
                    (input)="onPickerSearch($event)"
                  />
                  <select [value]="pickerTypeFilter()" (change)="onPickerTypeChange($event)">
                    <option value="all">Todos (.pdf, .md, .txt)</option>
                    <option value="pdf">PDF (.pdf)</option>
                    <option value="md">Markdown (.md)</option>
                    <option value="txt">Texto (.txt)</option>
                  </select>
                </div>

                <div class="picker-grid" *ngIf="pickerDocuments().length > 0">
                  <div 
                    class="picker-item-card" 
                    *ngFor="let doc of pickerDocuments()"
                    (click)="selectDocFromPicker(doc)"
                  >
                    <div class="picker-item-top">
                      <span class="type-pill" [ngClass]="doc.type">{{ doc.type.toUpperCase() }}</span>
                      <span class="item-size">{{ formatSize(doc.size) }}</span>
                    </div>
                    <h4 class="picker-item-title">{{ doc.name }}</h4>
                    <button type="button" class="btn-select-doc">
                      ✅ Seleccionar
                    </button>
                  </div>
                </div>

                <div class="picker-empty" *ngIf="pickerDocuments().length === 0">
                  <p>No hay documentos disponibles en el almacén con este filtro.</p>
                  <button type="button" class="btn-nav-docs" (click)="navigateToDocuments()">
                    📂 Ir a Mis Documentos para subir archivos
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Selector 1: Perfil del Destinatario (4) -->
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

          <!-- Selector 2: Formato Pedagógico (5) -->
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

          <!-- Selector 3: Cantidad de Contenido (Breve / Estándar / Amplio / Exhaustivo / Personalizado) -->
          <div class="selectors-section">
            <label class="section-title">3. Cantidad de Contenido a Generar</label>
            <div class="segmented-control quantity-segmented">
              <button 
                type="button" 
                *ngFor="let q of nivelesCantidad" 
                class="seg-btn"
                [class.active]="adaptForm.get('nivel_cantidad')?.value === q"
                (click)="selectNivelCantidad(q)"
              >
                {{ q }}
              </button>
            </div>

            <!-- Dynamic hint under quantity selector -->
            <div class="quantity-hint-box">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
              <span>{{ currentQuantityHint() }}</span>
            </div>

            <!-- Custom Quantity Slider (Only when Personalizado is active) -->
            <div class="custom-slider-box" *ngIf="adaptForm.get('nivel_cantidad')?.value === 'Personalizado'">
              <label for="custom-qty-slider">Cantidad exacta: <strong>{{ adaptForm.get('cantidad_objetivo')?.value }} elementos</strong></label>
              <input 
                id="custom-qty-slider" 
                type="range" 
                [min]="currentCustomRange().min" 
                [max]="currentCustomRange().max" 
                [value]="adaptForm.get('cantidad_objetivo')?.value"
                (input)="onCustomQuantityChange($event)"
              />
              <div class="slider-labels">
                <span>{{ currentCustomRange().min }}</span>
                <span>{{ currentCustomRange().max }}</span>
              </div>
            </div>
          </div>

          <!-- Selector 4 & 5 Dual Row (Nicho + Nivel Detalle) -->
          <div class="form-row-dual">
            <!-- Chips: Nicho Sector (4) -->
            <div class="form-group flex-1">
              <label>4. Nicho / Sector de Aplicación</label>
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
              <label>5. Nivel de Detalle Pedagógico</label>
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
              <span class="summary-chip">📊 {{ adaptForm.get('nivel_cantidad')?.value }} ({{ effectiveTargetCount() }})</span>
              <span class="summary-chip">🏢 {{ adaptForm.get('nicho_sector')?.value }}</span>
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

      <!-- ZONE 2: GENERATION LOADER -->
      <app-generation-loader 
        #loaderComp
        *ngIf="isPipelineRunning()" 
        [params]="getGenerationParams()"
        (cancel)="cancelPipeline()"
        (retry)="runPipeline()"
      ></app-generation-loader>

      <!-- ZONE 3: RESULT VIEWER -->
      <div class="result-viewer-container" *ngIf="currentResponse() && !isPipelineRunning()">
        <!-- STICKY ACTION BAR -->
        <div class="sticky-action-bar glass-card">
          <div class="bar-left">
            <button type="button" class="btn-back" (click)="resetForm()">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
              <span>Nueva adaptación</span>
            </button>
            
            <a class="saved-badge" (click)="navigateToLibrary()" role="button" tabindex="0">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              <span>Guardado en tu biblioteca</span>
            </a>
          </div>

          <div class="bar-right">
            <!-- EXPORT DROPDOWN -->
            <div class="export-dropdown-wrapper">
              <button 
                type="button" 
                class="btn-export-trigger"
                (click)="toggleExportMenu()"
                [attr.aria-expanded]="isExportMenuOpen()"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                <span>Exportar como... ▼</span>
              </button>

              <div class="export-menu" *ngIf="isExportMenuOpen()">
                <button 
                  type="button" 
                  class="menu-item" 
                  (click)="exportPdf(); closeExportMenu()"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#4F46E5" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  <span>PDF Didáctico</span>
                </button>
                <button 
                  type="button" 
                  class="menu-item" 
                  (click)="exportMarkdown(); closeExportMenu()"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#7C3AED" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M12 18v-6"/><path d="m9 15 3 3 3-3"/></svg>
                  <span>Markdown (.md)</span>
                </button>
                <button 
                  type="button" 
                  class="menu-item" 
                  (click)="exportAnki(); closeExportMenu()"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 3k-4 4-4-4"/></svg>
                  <span>Anki (CSV)</span>
                </button>
              </div>
            </div>

            <!-- JSON DATA BUTTON -->
            <button type="button" class="btn-json" (click)="isJsonDrawerOpen.set(true)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
              <span>Datos JSON</span>
            </button>
          </div>
        </div>

        <!-- AMICABLE QUANTITY WARNING NOTICE (If items_generados < items_solicitados) -->
        <div class="quantity-warning-banner glass-card" *ngIf="hasQuantityCapNotice()">
          <div class="warning-icon-box">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#D97706" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </div>
          <div class="warning-text">
            <strong>Aviso de capacidad del documento:</strong>
            <p>{{ quantityCapNoticeText() }}</p>
          </div>
        </div>

        <!-- PROTAGONIST CONTENT HEADER CARD -->
        <div class="result-header glass-card">
          <div class="meta-chips-row">
            <span class="meta-chip chip-profile">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
              {{ currentResponse()?.metadatos?.perfil_aplicado }}
            </span>
            <span class="meta-chip chip-format">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
              {{ currentResponse()?.metadatos?.formato_generado }} ({{ getTypedItems().length }} items)
            </span>
            <span class="meta-chip chip-nicho">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>
              {{ currentResponse()?.metadatos?.nicho_sector }}
            </span>
            <span class="meta-chip chip-time">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              {{ formattedStudyTime() }}
            </span>
          </div>

          <h2>{{ currentResponse()?.contenido_adaptado?.titulo }}</h2>
          <p class="introduccion">{{ currentResponse()?.contenido_adaptado?.introduccion_contextualizada }}</p>

          <!-- KEY CONCEPTS CLOUD ("Lo que aprenderás") -->
          <div class="concepts-section" *ngIf="allConcepts().length > 0">
            <span class="concepts-label">Lo que aprenderás:</span>
            <div class="concepts-cloud">
              <span class="c-chip" *ngFor="let c of visibleConcepts()">{{ c }}</span>
              <button 
                type="button" 
                class="btn-expand-concepts" 
                *ngIf="allConcepts().length > 6"
                (click)="isConceptsExpanded.set(!isConceptsExpanded())"
              >
                {{ isConceptsExpanded() ? 'Ver menos' : '+' + hiddenConceptsCount() + ' más' }}
              </button>
            </div>
          </div>
        </div>

        <!-- SELLO DE CONFIANZA -->
        <app-sello-confianza [evaluacion]="currentResponse()?.evaluacion_calidad"></app-sello-confianza>

        <!-- RENDERERS SWITCH BY FORMAT -->
        <div class="renderer-wrapper">
          <ng-container [ngSwitch]="currentResponse()?.metadatos?.formato_generado">
            <app-flashcards-renderer *ngSwitchCase="'Flashcards'" [items]="getTypedItems()"></app-flashcards-renderer>
            <app-quiz-renderer *ngSwitchCase="'Quiz'" [items]="getTypedItems()"></app-quiz-renderer>
            <app-tutorial-renderer *ngSwitchCase="'Tutorial'" [items]="getTypedItems()"></app-tutorial-renderer>
            <app-summary-renderer *ngSwitchCase="'Resumen Ejecutivo'" [items]="getTypedItems()"></app-summary-renderer>
            <app-script-renderer *ngSwitchCase="'Guion de Clase'" [items]="getTypedItems()"></app-script-renderer>
            <app-tutorial-renderer *ngSwitchDefault [items]="getTypedItems()"></app-tutorial-renderer>
          </ng-container>
        </div>

        <!-- FINAL ACTIONS BLOCK ("¿Qué quieres hacer ahora?") -->
        <div class="next-actions-card glass-card">
          <h3>¿Qué quieres hacer ahora?</h3>
          <p class="next-actions-desc">Aprovecha este contenido para generar nuevos formatos o ajustar la adaptación.</p>
          
          <div class="quick-prefill-grid">
            <button type="button" class="btn-prefill-action" (click)="quickPrefillFormat('Quiz')">
              <span class="action-icon">🎯</span>
              <div class="action-text">
                <strong>Crear Quiz de evaluación</strong>
                <span>Pon a prueba los conocimientos de este tema</span>
              </div>
            </button>

            <button type="button" class="btn-prefill-action" (click)="quickPrefillFormat('Flashcards')">
              <span class="action-icon">🎴</span>
              <div class="action-text">
                <strong>Generar Flashcards</strong>
                <span>Crea tarjetas de memoria para repasar</span>
              </div>
            </button>

            <button type="button" class="btn-prefill-action" (click)="quickPrefillProfile('Principiante')">
              <span class="action-icon">🌱</span>
              <div class="action-text">
                <strong>Explicar a Principiantes</strong>
                <span>Adapta el tono con explicaciones sencillas</span>
              </div>
            </button>
          </div>

          <!-- FEEDBACK BAR -->
          <div class="feedback-subcard">
            <div class="feedback-row" *ngIf="!feedbackSubmitted()">
              <span class="feedback-label">¿Te resultó útil esta adaptación?</span>
              <div class="feedback-btns">
                <button type="button" class="btn-vote" [class.active]="userVote() === 'up'" (click)="submitFeedback('up')">
                  👍 Útil
                </button>
                <button type="button" class="btn-vote" [class.active]="userVote() === 'down'" (click)="submitFeedback('down')">
                  👎 Mejorable
                </button>
              </div>
            </div>

            <div class="feedback-thanks" *ngIf="feedbackSubmitted()">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
              <span>¡Gracias por tus comentarios! Nos ayudan a mejorar la precisión.</span>
            </div>
          </div>
        </div>
      </div>

      <!-- DRAWERS -->
      <app-sources-drawer 
        *ngIf="isSourcesDrawerOpen()"
        [fuentes]="currentResponse()?.evaluacion_calidad?.fuentes_consultadas || []"
        [selectedFuente]="selectedFuente()"
        (close)="isSourcesDrawerOpen.set(false)"
      ></app-sources-drawer>

      <app-json-drawer 
        *ngIf="isJsonDrawerOpen()"
        [data]="currentResponse()"
        (close)="isJsonDrawerOpen.set(false)"
      ></app-json-drawer>
    </div>
  `,
  styles: [`
    .workspace-layout { max-width: 1200px; margin: 0 auto; display: flex; flex-direction: column; gap: 2rem; }
    .workspace-header h2 { font-size: 2.2rem; font-weight: 800; margin-bottom: 0.4rem; color: var(--text-primary); }
    .value-prop-tag { font-size: 0.75rem; font-weight: 800; color: #6366F1; letter-spacing: 0.08em; margin-bottom: 0.25rem; display: block; }
    .value-prop-subtitle { color: var(--text-secondary); font-size: 1.05rem; margin-bottom: 1.25rem; }

    .presets-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; }
    .presets-label { font-size: 0.82rem; font-weight: 700; color: var(--text-muted); }
    .preset-btn { background: var(--bg-surface); border: 1px solid var(--border-subtle); padding: 0.4rem 0.85rem; border-radius: 20px; font-size: 0.82rem; font-weight: 600; color: var(--text-primary); cursor: pointer; transition: all 0.2s; }
    .preset-btn:hover { border-color: #6366F1; color: #6366F1; transform: translateY(-1px); }

    .input-zone-card { padding: 2rem; border-radius: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04); }
    .form-group { margin-bottom: 1.75rem; }
    .form-group label { display: block; font-size: 0.92rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--text-primary); }
    .form-group input[type="text"], textarea { width: 100%; padding: 0.85rem 1rem; border-radius: 12px; border: 1px solid var(--border-subtle); background: var(--bg-app); color: var(--text-primary); font-size: 0.95rem; outline: none; transition: border-color 0.2s; }
    .form-group input[type="text"]:focus, textarea:focus { border-color: #6366F1; }

    .input-tabs-wrapper { margin-bottom: 2rem; }
    .tabs-header { display: flex; gap: 0.5rem; border-bottom: 1px solid var(--border-subtle); margin-bottom: 1rem; }
    .tab-btn { padding: 0.65rem 1.25rem; border: none; background: transparent; border-bottom: 2px solid transparent; color: var(--text-secondary); font-size: 0.9rem; font-weight: 700; cursor: pointer; transition: all 0.2s; }
    .tab-btn.active { color: #4F46E5; border-bottom-color: #4F46E5; }

    .dropzone { padding: 2.5rem 1.5rem; border: 2px dashed #818CF8; border-radius: 16px; text-align: center; cursor: pointer; transition: all 0.2s; background: var(--bg-app); }
    .dropzone.dragover { border-color: #4F46E5; background: rgba(79, 70, 229, 0.08); }
    .drop-icon { font-size: 2.5rem; display: block; margin-bottom: 0.5rem; }
    .drop-hint { font-size: 0.8rem; color: var(--text-muted); display: block; margin-top: 0.25rem; }
    .file-preview { display: flex; align-items: center; gap: 1rem; justify-content: center; }
    .btn-remove-file { background: transparent; border: none; color: #EF4444; font-weight: 800; cursor: pointer; }
    .char-count { font-size: 0.78rem; color: var(--text-muted); text-align: right; margin-top: 0.35rem; }

    /* FROM MIS DOCUMENTOS STYLES */
    .selected-document-card {
      display: flex; align-items: center; gap: 1.25rem; padding: 1.25rem;
      border-radius: 16px; background: rgba(99, 102, 241, 0.06); border: 1.5px solid #6366F1;
    }
    .selected-doc-icon { font-size: 2.2rem; }
    .selected-doc-info { flex: 1; display: flex; flex-direction: column; gap: 0.25rem; }
    .doc-badge-row { display: flex; align-items: center; gap: 0.6rem; }
    .type-pill { font-size: 0.72rem; font-weight: 800; padding: 0.15rem 0.5rem; border-radius: 6px; background: #4F46E5; color: #FFF; }
    .type-pill.pdf { background: #EF4444; }
    .type-pill.md { background: #7C3AED; }
    .type-pill.txt { background: #0891B2; }
    .status-ready { font-size: 0.78rem; color: #10B981; font-weight: 700; }
    .selected-doc-info strong { font-size: 1.05rem; color: var(--text-primary); }
    .doc-meta-text { font-size: 0.8rem; color: var(--text-muted); }
    .btn-clear-doc { background: transparent; border: 1px solid var(--border-subtle); padding: 0.45rem 0.85rem; border-radius: 10px; font-size: 0.82rem; font-weight: 700; color: var(--text-secondary); cursor: pointer; }
    .btn-clear-doc:hover { background: var(--bg-surface); color: #EF4444; border-color: #EF4444; }

    .document-picker-wrapper { background: var(--bg-app); border-radius: 16px; padding: 1.25rem; border: 1px solid var(--border-subtle); }
    .picker-search-bar { display: flex; gap: 0.75rem; margin-bottom: 1.25rem; }
    .picker-search-bar input { flex: 1; padding: 0.6rem 1rem; border-radius: 10px; border: 1px solid var(--border-subtle); background: var(--bg-surface); color: var(--text-primary); font-size: 0.9rem; outline: none; }
    .picker-search-bar select { padding: 0.6rem 1rem; border-radius: 10px; border: 1px solid var(--border-subtle); background: var(--bg-surface); color: var(--text-primary); font-size: 0.9rem; outline: none; }

    .picker-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
    .picker-item-card { background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 14px; padding: 1rem; cursor: pointer; display: flex; flex-direction: column; justify-content: space-between; transition: all 0.2s; }
    .picker-item-card:hover { border-color: #6366F1; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(99, 102, 241, 0.12); }
    .picker-item-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
    .item-size { font-size: 0.75rem; color: var(--text-muted); }
    .picker-item-title { font-size: 0.95rem; font-weight: 700; margin-bottom: 0.85rem; line-height: 1.35; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .btn-select-doc { background: #4F46E5; color: #FFF; border: none; padding: 0.45rem; border-radius: 8px; font-size: 0.82rem; font-weight: 700; cursor: pointer; width: 100%; }

    .picker-empty { text-align: center; padding: 2rem; color: var(--text-muted); }
    .btn-nav-docs { margin-top: 0.75rem; background: #4F46E5; color: #FFF; border: none; padding: 0.55rem 1.15rem; border-radius: 10px; font-weight: 700; cursor: pointer; font-size: 0.85rem; }

    .selectors-section { margin-bottom: 2rem; }
    .section-title { display: block; font-size: 0.95rem; font-weight: 800; margin-bottom: 0.85rem; color: var(--text-primary); }

    .cards-selector-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.85rem; }
    .formats-grid { grid-template-columns: repeat(5, 1fr); }
    .option-card { padding: 1rem; border-radius: 12px; background: var(--bg-app); border: 1.5px solid var(--border-subtle); cursor: pointer; display: flex; flex-direction: column; gap: 0.5rem; transition: all 0.2s; }
    .option-card:hover { border-color: #6366F1; transform: translateY(-2px); }
    .option-card.selected { border-color: #4F46E5; background: rgba(79, 70, 229, 0.08); box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15); }
    .card-icon { font-size: 1.5rem; }
    .card-text strong { font-size: 0.88rem; display: block; color: var(--text-primary); }
    .card-text p { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem; line-height: 1.3; }

    .segmented-control { display: flex; background: var(--bg-app); padding: 0.25rem; border-radius: 10px; border: 1px solid var(--border-subtle); }
    .seg-btn { flex: 1; padding: 0.45rem 0.6rem; border: none; background: transparent; color: var(--text-secondary); font-size: 0.82rem; font-weight: 700; border-radius: 8px; cursor: pointer; }
    .seg-btn.active { background: var(--bg-surface); color: var(--text-primary); box-shadow: var(--shadow-sm); }

    .quantity-hint-box { display: flex; align-items: center; gap: 0.4rem; font-size: 0.82rem; color: #6366F1; font-weight: 600; margin-top: 0.5rem; }
    .custom-slider-box { margin-top: 0.85rem; padding: 1rem; border-radius: 12px; background: var(--bg-app); border: 1px solid var(--border-subtle); }
    .custom-slider-box label { font-size: 0.85rem; color: var(--text-primary); display: block; margin-bottom: 0.5rem; }
    .custom-slider-box input[type="range"] { width: 100%; accent-color: #6366F1; cursor: pointer; }
    .slider-labels { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--text-muted); margin-top: 0.2rem; }

    .form-row-dual { display: flex; gap: 1.5rem; margin-bottom: 2rem; }
    .flex-1 { flex: 1; }

    .chips-selector { display: flex; flex-wrap: wrap; gap: 0.5rem; }
    .chip-select { padding: 0.4rem 0.85rem; border-radius: 20px; background: var(--bg-app); border: 1px solid var(--border-subtle); color: var(--text-secondary); font-size: 0.85rem; font-weight: 600; cursor: pointer; }
    .chip-select.active { background: #4F46E5; color: #FFFFFF; border-color: #4F46E5; }

    .submit-bar { display: flex; justify-content: space-between; align-items: center; padding-top: 1.5rem; border-top: 1px solid var(--border-subtle); }
    .summary-chips { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .summary-chip { font-size: 0.8rem; padding: 0.3rem 0.65rem; border-radius: 6px; background: var(--bg-app); border: 1px solid var(--border-subtle); color: var(--text-secondary); }

    .btn-cta-generate { padding: 0.85rem 1.75rem; border-radius: 12px; background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); border: none; color: #FFFFFF; font-size: 1rem; font-weight: 800; cursor: pointer; box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3); }
    .btn-cta-generate:disabled { opacity: 0.5; cursor: not-allowed; }

    /* RESULT VIEWER STICKY ACTION BAR & WARNING BANNER */
    .result-viewer-container { display: flex; flex-direction: column; gap: 1.5rem; }

    .sticky-action-bar { position: sticky; top: 1rem; z-index: 50; display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 1.25rem; border-radius: 16px; background: rgba(255, 255, 255, 0.85); backdrop-filter: blur(12px); border: 1px solid var(--border-subtle); box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05); }
    :host-context(.dark) .sticky-action-bar { background: rgba(30, 41, 59, 0.85); }

    .bar-left { display: flex; align-items: center; gap: 1rem; }
    .btn-back { display: inline-flex; align-items: center; gap: 0.4rem; background: transparent; border: 1px solid var(--border-subtle); padding: 0.45rem 0.85rem; border-radius: 10px; font-size: 0.85rem; font-weight: 700; cursor: pointer; color: var(--text-primary); transition: all 0.2s; }
    .btn-back:hover { background: var(--bg-app); border-color: #6366F1; color: #6366F1; }
    .saved-badge { display: inline-flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; font-weight: 700; color: #059669; background: rgba(16, 185, 129, 0.12); padding: 0.35rem 0.75rem; border-radius: 20px; text-decoration: none; cursor: pointer; }

    .bar-right { display: flex; align-items: center; gap: 0.75rem; }
    .export-dropdown-wrapper { position: relative; }
    .btn-export-trigger { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1rem; border-radius: 10px; background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%); border: none; color: #FFFFFF; font-size: 0.85rem; font-weight: 700; cursor: pointer; box-shadow: 0 2px 8px rgba(79, 70, 229, 0.25); }
    .export-menu { position: absolute; top: calc(100% + 0.5rem); right: 0; width: 200px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 0.5rem; display: flex; flex-direction: column; gap: 0.25rem; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15); z-index: 60; }
    .menu-item { display: flex; align-items: center; gap: 0.6rem; width: 100%; padding: 0.5rem 0.75rem; border-radius: 8px; border: none; background: transparent; color: var(--text-primary); font-size: 0.85rem; font-weight: 600; cursor: pointer; text-align: left; }
    .menu-item:hover { background: var(--bg-app); }
    .btn-json { display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.5rem 0.85rem; border-radius: 10px; background: var(--bg-app); border: 1px solid var(--border-subtle); color: var(--text-secondary); font-size: 0.85rem; font-weight: 600; cursor: pointer; }

    .quantity-warning-banner { display: flex; align-items: flex-start; gap: 0.85rem; padding: 1rem 1.25rem; border-radius: 14px; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); color: var(--text-primary); }
    .warning-icon-box { margin-top: 0.1rem; }
    .warning-text strong { font-size: 0.88rem; color: #D97706; display: block; margin-bottom: 0.2rem; }
    .warning-text p { font-size: 0.85rem; color: var(--text-secondary); margin: 0; }

    .result-header { padding: 2rem; border-radius: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); }
    .meta-chips-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1rem; }
    .meta-chip { display: inline-flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; font-weight: 800; padding: 0.25rem 0.65rem; border-radius: 8px; }
    .chip-profile { background: rgba(99, 102, 241, 0.12); color: #6366F1; }
    .chip-format { background: rgba(236, 72, 153, 0.12); color: #EC4899; }
    .chip-nicho { background: rgba(16, 185, 129, 0.12); color: #10B981; }
    .chip-time { background: var(--bg-app); color: var(--text-secondary); border: 1px solid var(--border-subtle); }

    .result-header h2 { font-size: 1.85rem; font-weight: 800; margin-bottom: 0.75rem; color: var(--text-primary); line-height: 1.3; }
    .introduccion { font-size: 1.05rem; color: var(--text-secondary); line-height: 1.6; margin-bottom: 1.5rem; }
    .concepts-section { padding-top: 1rem; border-top: 1px solid var(--border-subtle); }
    .concepts-label { font-size: 0.8rem; font-weight: 800; color: var(--text-muted); display: block; margin-bottom: 0.6rem; }
    .concepts-cloud { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
    .c-chip { font-size: 0.8rem; padding: 0.25rem 0.65rem; border-radius: 20px; background: rgba(34, 211, 238, 0.1); color: #0284C7; font-weight: 700; }
    .btn-expand-concepts { background: transparent; border: none; color: #6366F1; font-size: 0.8rem; font-weight: 700; cursor: pointer; padding: 0.25rem 0.5rem; }

    .next-actions-card { padding: 2rem; border-radius: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); }
    .next-actions-card h3 { font-size: 1.25rem; font-weight: 800; margin-bottom: 0.35rem; color: var(--text-primary); }
    .next-actions-desc { font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 1.25rem; }
    .quick-prefill-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
    .btn-prefill-action { display: flex; align-items: center; gap: 0.85rem; padding: 1rem; border-radius: 14px; background: var(--bg-app); border: 1px solid var(--border-subtle); cursor: pointer; text-align: left; transition: all 0.2s; }
    .btn-prefill-action:hover { border-color: #6366F1; transform: translateY(-2px); }
    .action-icon { font-size: 1.5rem; }
    .action-text strong { font-size: 0.88rem; display: block; color: var(--text-primary); }
    .action-text span { font-size: 0.75rem; color: var(--text-muted); }

    .feedback-subcard { padding: 1rem 1.25rem; border-radius: 12px; background: var(--bg-app); border: 1px solid var(--border-subtle); }
    .feedback-row { display: flex; justify-content: space-between; align-items: center; }
    .feedback-label { font-size: 0.88rem; font-weight: 700; color: var(--text-secondary); }
    .feedback-btns { display: flex; gap: 0.5rem; }
    .btn-vote { padding: 0.4rem 0.85rem; border-radius: 8px; background: var(--bg-surface); border: 1px solid var(--border-subtle); color: var(--text-primary); font-size: 0.82rem; font-weight: 700; cursor: pointer; }
    .btn-vote.active { background: rgba(99, 102, 241, 0.15); border-color: #6366F1; color: #6366F1; }
    .feedback-thanks { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: #059669; font-weight: 700; }

    @media (max-width: 768px) {
      .cards-selector-grid, .formats-grid { grid-template-columns: 1fr 1fr; }
      .form-row-dual { flex-direction: column; }
      .sticky-action-bar { flex-direction: column; gap: 0.75rem; align-items: stretch; }
      .bar-left, .bar-right { justify-content: space-between; }
    }
  `]
})
export class WorkspaceComponent implements OnInit {
  private api = inject<NuevaMenteApi>(NUEVAMENTE_API);
  private fb = inject(FormBuilder);
  private exportService = inject(ExportService);
  private stateService = inject(StateService);
  readonly documentService = inject(DocumentService);
  private router = inject(Router);

  activeTab = signal<'upload' | 'text' | 'from_documents'>('from_documents');
  isDragging = signal<boolean>(false);
  uploadedFile = signal<File | null>(null);
  selectedWorkspaceDoc = signal<AppDocument | null>(null);

  pickerSearchQuery = signal<string>('');
  pickerTypeFilter = signal<string>('all');

  isPipelineRunning = signal<boolean>(false);
  currentResponse = signal<AdaptationResponse | null>(null);

  isExportMenuOpen = signal<boolean>(false);
  isJsonDrawerOpen = signal<boolean>(false);
  isSourcesDrawerOpen = signal<boolean>(false);
  selectedFuente = signal<RagFuente | undefined>(undefined);

  isConceptsExpanded = signal<boolean>(false);
  userVote = signal<'up' | 'down' | null>(null);
  feedbackSubmitted = signal<boolean>(false);

  private pipelineSub?: Subscription;

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
  nivelesCantidad: NivelCantidad[] = ['Breve', 'Estandar', 'Amplio', 'Exhaustivo', 'Personalizado'];

  adaptForm = this.fb.group({
    documento_titulo: ['Especificación de Redes VCN en Oracle Cloud Infrastructure (OCI)', [Validators.required]],
    documento_contenido: ['Una Virtual Cloud Network (VCN) en Oracle Cloud Infrastructure es una red privada definida por software...', [Validators.required]],
    perfil_destinatario: ['Desarrollador' as PerfilDestinatario, [Validators.required]],
    formato_salida: ['Flashcards' as FormatoSalida, [Validators.required]],
    nicho_sector: ['Fintech' as NichoSector, [Validators.required]],
    nivel_detalle: ['Tecnico' as NivelDetalle, [Validators.required]],
    nivel_cantidad: ['Estandar' as NivelCantidad, [Validators.required]],
    cantidad_objetivo: [20]
  });

  readonly formValues = toSignal(this.adaptForm.valueChanges, { initialValue: this.adaptForm.value });

  ngOnInit(): void {
    // Check if document was pre-selected from DocumentService
    const preselected = this.documentService.selectedWorkspaceDocument();
    if (preselected) {
      this.selectDocFromPicker(preselected);
    } else {
      const activeDocs = this.documentService.activeDocuments();
      if (activeDocs.length > 0) {
        this.selectDocFromPicker(activeDocs[0]);
      }
    }
  }

  pickerDocuments = computed(() => {
    const query = this.pickerSearchQuery().toLowerCase();
    const type = this.pickerTypeFilter();

    return this.documentService.activeDocuments().filter(doc => {
      const matchQuery = doc.name.toLowerCase().includes(query) ||
        (doc.tags && doc.tags.some(t => t.toLowerCase().includes(query)));
      const matchType = type === 'all' || doc.type === type;
      return matchQuery && matchType;
    });
  });

  selectDocFromPicker(doc: AppDocument): void {
    this.selectedWorkspaceDoc.set(doc);
    this.activeTab.set('from_documents');
    this.documentService.selectForWorkspace(doc);

    // Clean title from extension
    const cleanTitle = doc.name.replace(/\.(pdf|md|txt)$/i, '');
    let cleanContent = doc.content || `Contenido de ${doc.name}`;
    cleanContent = cleanContent.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\uFFFD]/g, '');
    cleanContent = cleanContent.replace(/stream[\s\S]*?endstream/gi, '');
    cleanContent = cleanContent.replace(/<<[\s\S]*?>>/g, '');
    cleanContent = cleanContent.replace(/\d+\s+\d+\s+obj[\s\S]*?endobj/gi, '');
    cleanContent = cleanContent.replace(/^.*(?:%PDF-|\b\d+\s+\d+\s+R\b|\/FlateDecode|\/Filter|\/FontDescriptor|\/MediaBox|\/Parent|\/Catalog|\/Length).*$/gm, '').trim();

    this.adaptForm.patchValue({
      documento_titulo: cleanTitle,
      documento_contenido: cleanContent || `Especificación técnica de ${cleanTitle}`
    });
  }

  clearSelectedWorkspaceDoc(): void {
    this.selectedWorkspaceDoc.set(null);
    this.documentService.clearWorkspaceSelection();
  }

  onPickerSearch(event: Event): void {
    this.pickerSearchQuery.set((event.target as HTMLInputElement).value);
  }

  onPickerTypeChange(event: Event): void {
    this.pickerTypeFilter.set((event.target as HTMLSelectElement).value);
  }

  navigateToDocuments(): void {
    this.router.navigate(['/documents']);
  }

  currentQuantityHint = computed(() => {
    const val = this.formValues();
    const fmt = (val?.formato_salida as FormatoSalida) || 'Flashcards';
    const lvl = (val?.nivel_cantidad as NivelCantidad) || 'Estandar';
    const customVal = val?.cantidad_objetivo || undefined;
    return getQuantityHintText(fmt, lvl, customVal);
  });

  currentCustomRange = computed(() => {
    const val = this.formValues();
    const fmt = (val?.formato_salida as FormatoSalida) || 'Flashcards';
    return CONTENT_QUANTITY_CONFIG[fmt]?.customRange || { min: 1, max: 100, default: 20 };
  });

  effectiveTargetCount = computed(() => {
    const val = this.formValues();
    const fmt = (val?.formato_salida as FormatoSalida) || 'Flashcards';
    const lvl = (val?.nivel_cantidad as NivelCantidad) || 'Estandar';
    const customVal = val?.cantidad_objetivo || undefined;
    return getTargetItemCount(fmt, lvl, customVal);
  });

  allConcepts = computed(() => {
    return this.currentResponse()?.metadatos?.conceptos_clave || [];
  });

  visibleConcepts = computed(() => {
    const list = this.allConcepts();
    if (this.isConceptsExpanded() || list.length <= 6) return list;
    return list.slice(0, 6);
  });

  hiddenConceptsCount = computed(() => {
    return Math.max(0, this.allConcepts().length - 6);
  });

  formattedStudyTime = computed(() => {
    const mins = this.currentResponse()?.metadatos?.tiempo_estimado_estudio_minutos || 5;
    if (mins === Math.floor(mins)) return `≈ ${mins} min de estudio`;
    const totalSecs = Math.round(mins * 60);
    const m = Math.floor(totalSecs / 60);
    const s = totalSecs % 60;
    return `⏱ ${m} min ${s} s`;
  });

  hasQuantityCapNotice = computed(() => {
    const meta = this.currentResponse()?.metadatos;
    if (!meta) return false;
    if (meta.aviso_cantidad) return true;
    if (meta.items_solicitados && meta.items_generados) {
      return meta.items_generados < meta.items_solicitados;
    }
    return false;
  });

  quantityCapNoticeText = computed(() => {
    const meta = this.currentResponse()?.metadatos;
    if (meta?.aviso_cantidad) return meta.aviso_cantidad;
    if (meta?.items_solicitados && meta?.items_generados) {
      return `Tu documento dio para ${meta.items_generados} elementos verificados. Con un documento más extenso podrás alcanzar los ${meta.items_solicitados} solicitados.`;
    }
    return 'Se ajustó la cantidad generada a la capacidad del documento fuente.';
  });

  selectPerfil(val: string): void {
    this.adaptForm.patchValue({ perfil_destinatario: val as PerfilDestinatario });
  }

  selectFormato(val: string): void {
    this.adaptForm.patchValue({ formato_salida: val as FormatoSalida });
    const fmt = val as FormatoSalida;
    const lvl = this.adaptForm.get('nivel_cantidad')?.value as NivelCantidad || 'Estandar';
    const defaultQty = getTargetItemCount(fmt, lvl);
    this.adaptForm.patchValue({ cantidad_objetivo: defaultQty });
  }

  selectNivelCantidad(val: NivelCantidad): void {
    this.adaptForm.patchValue({ nivel_cantidad: val });
    const fmt = this.adaptForm.get('formato_salida')?.value as FormatoSalida || 'Flashcards';
    const targetQty = getTargetItemCount(fmt, val);
    this.adaptForm.patchValue({ cantidad_objetivo: targetQty });
  }

  onCustomQuantityChange(event: Event): void {
    const val = parseInt((event.target as HTMLInputElement).value, 10);
    this.adaptForm.patchValue({ cantidad_objetivo: val });
  }

  applyPreset(type: string): void {
    if (type === 'beginner-flashcards') {
      this.adaptForm.patchValue({
        documento_titulo: 'Guía Didáctica: MsJava Microservicios',
        documento_contenido: 'MsJava en aplicaciones empresariales Fintech...',
        perfil_destinatario: 'Principiante',
        formato_salida: 'Flashcards',
        nicho_sector: 'Fintech',
        nivel_detalle: 'Didactico',
        nivel_cantidad: 'Estandar',
        cantidad_objetivo: 20
      });
    } else if (type === 'leader-summary') {
      this.adaptForm.patchValue({
        documento_titulo: 'Arquitectura de Redes VCN en OCI',
        documento_contenido: 'Virtual Cloud Network (VCN) en Oracle Cloud Infrastructure...',
        perfil_destinatario: 'Lider Tecnico',
        formato_salida: 'Resumen Ejecutivo',
        nicho_sector: 'General',
        nivel_detalle: 'Conciso',
        nivel_cantidad: 'Breve',
        cantidad_objetivo: 5
      });
    } else if (type === 'dev-quiz') {
      this.adaptForm.patchValue({
        documento_titulo: 'Manual de Desarrollo Spring Boot 3',
        documento_contenido: 'Configuración de endpoints REST con Spring Boot y Gradle...',
        perfil_destinatario: 'Desarrollador',
        formato_salida: 'Quiz',
        nicho_sector: 'Fintech',
        nivel_detalle: 'Tecnico',
        nivel_cantidad: 'Estandar',
        cantidad_objetivo: 10
      });
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      this.handleFile(event.dataTransfer.files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  private handleFile(file: File): void {
    this.uploadedFile.set(file);
    const cleanName = file.name.replace(/\.(pdf|md|txt)$/i, '');
    this.adaptForm.patchValue({ documento_titulo: cleanName });

    if (file.name.toLowerCase().endsWith('.pdf')) {
      this.api.parsePdf(file).subscribe({
        next: (res) => {
          if (res && res.texto_extraido) {
            this.adaptForm.patchValue({ documento_contenido: res.texto_extraido });
          }
        },
        error: () => {
          const reader = new FileReader();
          reader.onload = (e) => {
            const raw = e.target?.result as string || '';
            let text = raw.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\uFFFD]/g, '');
            text = text.replace(/stream[\s\S]*?endstream/gi, '');
            text = text.replace(/<<[\s\S]*?>>/g, '');
            text = text.replace(/\d+\s+\d+\s+obj[\s\S]*?endobj/gi, '');
            text = text.replace(/^.*(?:%PDF-|\b\d+\s+\d+\s+R\b|\/FlateDecode|\/Filter|\/FontDescriptor|\/MediaBox|\/Parent|\/Catalog|\/Length).*$/gm, '').trim();
            this.adaptForm.patchValue({ documento_contenido: text || `Especificación técnica de ${file.name}` });
          };
          reader.readAsText(file);
        }
      });
    } else {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string || `Contenido de ${file.name}`;
        this.adaptForm.patchValue({ documento_contenido: text });
      };
      reader.readAsText(file);
    }
  }

  removeFile(): void {
    this.uploadedFile.set(null);
  }

  runPipeline(): void {
    if (this.adaptForm.invalid) return;

    this.isPipelineRunning.set(true);
    const formVal = this.adaptForm.value;

    const req: AdaptationRequest = {
      documento_titulo: formVal.documento_titulo || 'Documento Técnico',
      documento_contenido: formVal.documento_contenido || '',
      perfil_destinatario: formVal.perfil_destinatario || 'Desarrollador',
      formato_salida: formVal.formato_salida || 'Flashcards',
      nicho_sector: formVal.nicho_sector || 'General',
      nivel_detalle: formVal.nivel_detalle || 'Tecnico',
      nivel_cantidad: formVal.nivel_cantidad || 'Estandar',
      cantidad_objetivo: formVal.cantidad_objetivo || 20
    };

    this.pipelineSub = this.api.adaptContent(req).subscribe({
      next: (resp) => {
        this.currentResponse.set(resp);
        this.stateService.addProjectFromResponse(req, resp);
        this.isPipelineRunning.set(false);
      },
      error: (err) => {
        console.error('Error en pipeline RAG:', err);
        this.isPipelineRunning.set(false);
      }
    });
  }

  cancelPipeline(): void {
    if (this.pipelineSub) {
      this.pipelineSub.unsubscribe();
    }
    this.isPipelineRunning.set(false);
  }

  getGenerationParams(): any {
    const val = this.adaptForm.value;
    return {
      titulo: val.documento_titulo,
      perfil: val.perfil_destinatario,
      formato: val.formato_salida,
      cantidad: this.effectiveTargetCount()
    };
  }

  resetForm(): void {
    this.currentResponse.set(null);
    this.isPipelineRunning.set(false);
    this.feedbackSubmitted.set(false);
    this.userVote.set(null);
  }

  navigateToLibrary(): void {
    this.router.navigate(['/library']);
  }

  toggleExportMenu(): void {
    this.isExportMenuOpen.set(!this.isExportMenuOpen());
  }

  closeExportMenu(): void {
    this.isExportMenuOpen.set(false);
  }

  exportPdf(): void {
    const resp = this.currentResponse();
    if (resp) this.exportService.exportPdfDidactico(resp);
  }

  exportMarkdown(): void {
    const resp = this.currentResponse();
    if (resp) this.exportService.exportMarkdown(resp);
  }

  exportAnki(): void {
    const resp = this.currentResponse();
    if (resp) this.exportService.exportAnkiCsv(resp);
  }

  getTypedItems(): any[] {
    const resp = this.currentResponse();
    return resp?.contenido_adaptado?.items || [];
  }

  quickPrefillFormat(fmt: string): void {
    this.selectFormato(fmt);
    this.resetForm();
  }

  quickPrefillProfile(prof: string): void {
    this.selectPerfil(prof);
    this.resetForm();
  }

  submitFeedback(vote: 'up' | 'down'): void {
    this.userVote.set(vote);
    this.feedbackSubmitted.set(true);
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  formatDate(dateStr: string): string {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
    } catch {
      return dateStr;
    }
  }
}
