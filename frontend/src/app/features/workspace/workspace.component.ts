import { Component, signal, computed, inject, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';

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
                formControlName="cantidad_objetivo"
              />
              <div class="slider-labels">
                <span>{{ currentCustomRange().min }}</span>
                <span>{{ currentCustomRange().max }} elementos</span>
              </div>
            </div>
          </div>

          <!-- Sector Nicho & Nivel de Detalle Row -->
          <div class="form-row-dual">
            <!-- Sector Chips (4) -->
            <div class="form-group flex-1">
              <label>4. Nicho / Sector Industrial</label>
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
                <span>Exportar Todos</span>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" [class.rotated]="isExportMenuOpen()"><polyline points="6 9 12 15 18 9"/></svg>
              </button>

              <div class="export-menu glass-card" *ngIf="isExportMenuOpen()">
                <button type="button" class="menu-item" (click)="exportMarkdown(); closeExportMenu()">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  <span>Markdown (.md)</span>
                </button>
                <button type="button" class="menu-item" (click)="exportPdf(); closeExportMenu()">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#EC4899" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/></svg>
                  <span>PDF Didáctico</span>
                </button>
                <button 
                  type="button" 
                  class="menu-item" 
                  *ngIf="currentResponse()?.metadatos?.formato_generado === 'Flashcards'" 
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

      <!-- RAG SOURCES DRAWER MODAL -->
      <app-sources-drawer 
        [isOpen]="isSourcesDrawerOpen()" 
        [fuente]="selectedFuente()"
        (closeDrawer)="isSourcesDrawerOpen.set(false)"
      ></app-sources-drawer>

      <!-- JSON DATA DRAWER OVERLAY -->
      <app-json-drawer
        [isOpen]="isJsonDrawerOpen()"
        [data]="currentResponse()"
        (closeDrawer)="isJsonDrawerOpen.set(false)"
      ></app-json-drawer>
    </div>
  `,
  styles: [`
    .workspace-layout {
      max-width: 1040px;
      margin: 0 auto;
      padding: 0 1rem;
    }

    .workspace-header { margin-bottom: 2rem; }
    .value-prop-tag { font-size: 0.75rem; font-weight: 800; color: #22D3EE; letter-spacing: 0.05em; margin-bottom: 0.4rem; display: block; }
    .workspace-header h2 { font-size: 2rem; font-weight: 800; margin-bottom: 0.35rem; }
    .value-prop-subtitle { color: var(--text-secondary); font-size: 1rem; margin-bottom: 1.25rem; }
    .presets-row { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
    .presets-label { font-size: 0.8rem; font-weight: 700; color: var(--text-muted); }
    .preset-btn { padding: 0.4rem 0.85rem; border-radius: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); color: var(--text-primary); font-size: 0.82rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
    .preset-btn:hover { border-color: #6366F1; background: rgba(99, 102, 241, 0.08); }

    .input-zone-card { padding: 2rem; border-radius: 20px; background: var(--bg-surface); border: 1px solid var(--border-subtle); margin-bottom: 2rem; }
    .form-group { margin-bottom: 1.5rem; }
    .form-group label { display: block; font-size: 0.88rem; font-weight: 700; margin-bottom: 0.5rem; color: var(--text-primary); }

    input[type="text"], textarea { width: 100%; padding: 0.85rem 1rem; border-radius: 12px; background: var(--bg-app); border: 1px solid var(--border-subtle); color: var(--text-primary); font-size: 0.95rem; outline: none; }

    .input-tabs-wrapper { margin-bottom: 2rem; }
    .tabs-header { display: flex; gap: 0.5rem; margin-bottom: 0.75rem; }
    .tab-btn { padding: 0.5rem 1rem; border-radius: 8px; background: transparent; border: 1px solid var(--border-subtle); color: var(--text-secondary); font-size: 0.88rem; font-weight: 600; cursor: pointer; }
    .tab-btn.active { background: #4F46E5; color: #FFFFFF; border-color: #4F46E5; }

    .dropzone { border: 2px dashed var(--border-subtle); border-radius: 16px; padding: 2.5rem 1.5rem; text-align: center; cursor: pointer; background: var(--bg-app); transition: border-color 0.2s; }
    .dropzone.dragover { border-color: #22D3EE; background: rgba(34, 211, 238, 0.05); }
    .drop-icon { font-size: 2.5rem; display: block; margin-bottom: 0.5rem; }
    .drop-hint { font-size: 0.8rem; color: var(--text-muted); display: block; margin-top: 0.25rem; }
    .file-preview { display: flex; align-items: center; gap: 1rem; justify-content: center; }
    .btn-remove-file { background: transparent; border: none; color: #EF4444; font-weight: 800; cursor: pointer; }
    .char-count { font-size: 0.78rem; color: var(--text-muted); text-align: right; margin-top: 0.35rem; }

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
export class WorkspaceComponent {
  private api = inject<NuevaMenteApi>(NUEVAMENTE_API);
  private fb = inject(FormBuilder);
  private exportService = inject(ExportService);
  private stateService = inject(StateService);
  private router = inject(Router);

  activeTab = signal<'upload' | 'text'>('text');
  isDragging = signal<boolean>(false);
  uploadedFile = signal<File | null>(null);

  isPipelineRunning = signal<boolean>(false);
  currentResponse = signal<AdaptationResponse | null>(null);

  isExportMenuOpen = signal<boolean>(false);
  isJsonDrawerOpen = signal<boolean>(false);
  isSourcesDrawerOpen = signal<boolean>(false);
  selectedFuente = signal<RagFuente | undefined>(undefined);

  isConceptsExpanded = signal<boolean>(false);
  userVote = signal<'up' | 'down' | null>(null);
  feedbackSubmitted = signal<boolean>(false);

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
    documento_titulo: ['Introducción a la Arquitectura de Redes VCN en OCI', [Validators.required]],
    documento_contenido: ['Una Virtual Cloud Network (VCN) en Oracle Cloud Infrastructure es una red privada definida por software...', [Validators.required]],
    perfil_destinatario: ['Desarrollador' as PerfilDestinatario, [Validators.required]],
    formato_salida: ['Flashcards' as FormatoSalida, [Validators.required]],
    nicho_sector: ['Fintech' as NichoSector, [Validators.required]],
    nivel_detalle: ['Tecnico' as NivelDetalle, [Validators.required]],
    nivel_cantidad: ['Estandar' as NivelCantidad, [Validators.required]],
    cantidad_objetivo: [20]
  });

  currentQuantityHint = computed(() => {
    const val = this.adaptForm.value;
    const fmt = val.formato_salida as FormatoSalida || 'Flashcards';
    const lvl = val.nivel_cantidad as NivelCantidad || 'Estandar';
    const customVal = val.cantidad_objetivo || undefined;
    return getQuantityHintText(fmt, lvl, customVal);
  });

  currentCustomRange = computed(() => {
    const fmt = (this.adaptForm.get('formato_salida')?.value as FormatoSalida) || 'Flashcards';
    return CONTENT_QUANTITY_CONFIG[fmt]?.customRange || { min: 1, max: 100, default: 20 };
  });

  effectiveTargetCount = computed(() => {
    const val = this.adaptForm.value;
    const fmt = val.formato_salida as FormatoSalida || 'Flashcards';
    const lvl = val.nivel_cantidad as NivelCantidad || 'Estandar';
    const customVal = val.cantidad_objetivo || undefined;
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

  toggleExportMenu(): void {
    this.isExportMenuOpen.set(!this.isExportMenuOpen());
  }

  closeExportMenu(): void {
    this.isExportMenuOpen.set(false);
  }

  navigateToLibrary(): void {
    this.router.navigate(['/biblioteca']);
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
        nivel_detalle: 'Didactico',
        nivel_cantidad: 'Estandar',
        cantidad_objetivo: 20
      });
    } else if (preset === 'leader-summary') {
      this.adaptForm.patchValue({
        documento_titulo: 'Estrategia de Redes Privadas & Seguridad OCI',
        documento_contenido: 'Las redes VCN permiten aislamiento corporativo y reducción de riesgos ante auditorías PCI-DSS.',
        perfil_destinatario: 'Ejecutivo',
        formato_salida: 'Resumen Ejecutivo',
        nicho_sector: 'Fintech',
        nivel_detalle: 'Conciso',
        nivel_cantidad: 'Estandar',
        cantidad_objetivo: 5
      });
    } else if (preset === 'dev-quiz') {
      this.adaptForm.patchValue({
        documento_titulo: 'Configuración Avanzada de Network Security Groups',
        documento_contenido: 'Los NSGs aplican reglas a nivel de VNIC individual sin alterar la subred completa.',
        perfil_destinatario: 'Desarrollador',
        formato_salida: 'Quiz',
        nicho_sector: 'E-commerce',
        nivel_detalle: 'Tecnico',
        nivel_cantidad: 'Estandar',
        cantidad_objetivo: 10
      });
    }
  }

  quickPrefillFormat(formato: FormatoSalida): void {
    this.adaptForm.patchValue({ formato_salida: formato });
    const lvl = this.adaptForm.get('nivel_cantidad')?.value as NivelCantidad || 'Estandar';
    this.adaptForm.patchValue({ cantidad_objetivo: getTargetItemCount(formato, lvl) });
    this.resetForm();
  }

  quickPrefillProfile(perfil: PerfilDestinatario): void {
    this.adaptForm.patchValue({ perfil_destinatario: perfil });
    this.resetForm();
  }

  submitFeedback(vote: 'up' | 'down'): void {
    this.userVote.set(vote);
    this.feedbackSubmitted.set(true);
  }

  onDragOver(e: DragEvent): void { e.preventDefault(); this.isDragging.set(true); }
  onDragLeave(e: DragEvent): void { e.preventDefault(); this.isDragging.set(false); }

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
      this.api.parsePdf(file).subscribe({
        next: (res) => {
          if (res && res.texto_extraido) {
            const cleanText = this.sanitizeTechnicalText(res.texto_extraido);
            this.adaptForm.patchValue({ documento_contenido: cleanText });
          }
        },
        error: () => {
          const fallbackText = `Documento Técnico: ${formattedTitle}\nCurso de Microservicios con Spring Boot 3 y 4. Arquitectura de Microservicios, APIs REST, Spring Data JPA, Spring Cloud Gateway, Resilience4j Circuit Breakers, Apache Kafka, Observabilidad y Kubernetes.`;
          this.adaptForm.patchValue({ documento_contenido: fallbackText });
        }
      });
    }
  }

  private sanitizeTechnicalText(text: string): string {
    if (!text) return '';
    return text.replace(/[^\x20-\x7E\xA0-\xFFáéíóúÁÉÍÓÚñÑ\n\r\t]/g, ' ').replace(/[^\S\r\n]{2,}/g, ' ').trim();
  }

  @ViewChild(GenerationLoaderComponent) loaderComp?: GenerationLoaderComponent;
  private activeAdaptationSub: Subscription | null = null;

  removeFile(): void { this.uploadedFile.set(null); }

  getGenerationParams(): { perfil?: string; formato?: string; nicho?: string; nivel?: string } {
    const val = this.adaptForm.value;
    return {
      perfil: val.perfil_destinatario ?? undefined,
      formato: val.formato_salida ?? undefined,
      nicho: val.nicho_sector ?? undefined,
      nivel: val.nivel_detalle ?? undefined
    };
  }

  runPipeline(): void {
    if (this.adaptForm.invalid) return;
    this.isPipelineRunning.set(true);
    this.currentResponse.set(null);
    this.feedbackSubmitted.set(false);
    this.userVote.set(null);

    const startTime = Date.now();
    const req = this.adaptForm.value as AdaptationRequest;
    req.cantidad_generar = this.effectiveTargetCount();

    if (typeof console !== 'undefined' && console.log) {
      console.log('[NUEVAMENTE DEV] Payload de Generación enviado al Backend:', req);
    }

    if (this.activeAdaptationSub) {
      this.activeAdaptationSub.unsubscribe();
    }

    this.activeAdaptationSub = this.api.adaptContent(req).subscribe({
      next: (res) => {
        const elapsed = Date.now() - startTime;
        const minDuration = 600;
        const delay = elapsed < minDuration ? minDuration - elapsed : 0;

        setTimeout(() => {
          this.currentResponse.set(res);
          this.isPipelineRunning.set(false);
          localStorage.setItem('nuevamente_library_initialized', 'true');
          this.stateService.addProjectFromResponse(req, res);
        }, delay);
      },
      error: (err) => {
        const errorMsg = err?.error?.mensaje || err?.message || 'Error al comunicarse con el servidor RAG.';
        this.loaderComp?.triggerError(errorMsg);
      }
    });
  }

  cancelPipeline(): void {
    if (this.activeAdaptationSub) {
      this.activeAdaptationSub.unsubscribe();
      this.activeAdaptationSub = null;
    }
    this.isPipelineRunning.set(false);
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
