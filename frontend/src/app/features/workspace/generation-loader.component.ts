import { 
  Component, 
  Input, 
  Output, 
  EventEmitter, 
  OnInit, 
  OnDestroy, 
  ChangeDetectionStrategy, 
  signal, 
  computed, 
  inject, 
  DestroyRef 
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { timer, Subscription } from 'rxjs';
import { environment } from '../../../environments/environment';
import { PipelineStage } from './pipeline-progress.component';

export interface GenerationParams {
  perfil?: string;
  formato?: string;
  nicho?: string;
  nivel?: string;
}

@Component({
  selector: 'app-generation-loader',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <!-- COMPACT VARIANT (For Library / Comparator inline loaders) -->
    <div *ngIf="compact" class="loader-compact-box">
      <div class="spinner-compact" aria-hidden="true"></div>
      <span class="compact-text" role="status" aria-live="polite">{{ currentMicrocopy() }}</span>
    </div>

    <!-- FULL INMERSIVE WORKSPACE LOADER -->
    <div *ngIf="!compact" class="generation-loader-container glass-card" [class.is-error-state]="isError()">
      
      <!-- REASSURING TOP BADGE & DETAILS TOGGLE HEADER -->
      <div class="loader-top-bar">
        <div class="brand-tag">
          <span class="pulse-dot" [class.paused]="!isTabVisible()" aria-hidden="true"></span>
          <span class="tag-text">Procesamiento RAG de Alta Fidelidad</span>
        </div>

        <button 
          type="button" 
          class="btn-toggle-details" 
          (click)="toggleDetails()"
          [attr.aria-expanded]="isDetailsOpen()"
          aria-controls="technical-details-panel"
        >
          {{ isDetailsOpen() ? '▼ Ocultar detalles técnicos' : '▶ Ver detalles técnicos' }}
        </button>
      </div>

      <!-- ERROR STATE VIEW -->
      <div class="error-state-box" *ngIf="isError()">
        <div class="error-icon-box" aria-hidden="true">⚠️</div>
        <h3>Ocurrió un inconveniente al generar el contenido</h3>
        <p class="error-desc">{{ errorMessage() || 'No se pudo procesar la solicitud con el pipeline. Por favor reintenta.' }}</p>

        <div class="error-actions-row">
          <button type="button" class="btn-retry" (click)="onRetry()">
            🔄 Reintentar Generación
          </button>
          <button type="button" class="btn-back-form" (click)="onCancel()">
            ← Volver al Formulario
          </button>
        </div>
      </div>

      <!-- NORMAL LOADING STATE VIEW -->
      <div class="loading-state-content" *ngIf="!isError()">

        <!-- 3D KNOWLEDGE ORBITAL GRAPHIC (60FPS GPU ACCELERATED) -->
        <div class="orbital-stage-wrapper" aria-hidden="true">
          <div class="orbital-canvas" [class.paused]="!isTabVisible()">
            <!-- Concentric Orbital Rings -->
            <div class="orbit-ring ring-outer">
              <div class="orbit-particle p-1"></div>
              <div class="orbit-particle p-2"></div>
            </div>
            <div class="orbit-ring ring-mid">
              <div class="orbit-particle p-3"></div>
            </div>
            <div class="orbit-ring ring-inner">
              <div class="orbit-particle p-4"></div>
            </div>

            <!-- Floating Materializing Icon Cards -->
            <div class="floating-card float-doc">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            </div>
            <div class="floating-card float-card">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#EC4899" stroke-width="2"><rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 10h18"/></svg>
            </div>
            <div class="floating-card float-quiz">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </div>

            <!-- Central NuevaMente Brand Core Isotype -->
            <div class="brand-core-nucleus">
              <svg class="brand-core-isotype" viewBox="0 0 40 40" fill="none">
                <path d="M20 4L4 12L20 20L36 12L20 4Z" fill="url(#loader-grad-1)"/>
                <path d="M4 12V24L20 32V20L4 12Z" fill="url(#loader-grad-2)"/>
                <path d="M36 12V24L20 32V20L36 12Z" fill="url(#loader-grad-3)"/>
                <defs>
                  <linearGradient id="loader-grad-1" x1="4" y1="4" x2="36" y2="20"><stop stop-color="#4F46E5"/><stop offset="1" stop-color="#7C3AED"/></linearGradient>
                  <linearGradient id="loader-grad-2" x1="4" y1="12" x2="20" y2="32"><stop stop-color="#6366F1"/><stop offset="1" stop-color="#22D3EE"/></linearGradient>
                  <linearGradient id="loader-grad-3" x1="36" y1="12" x2="20" y2="32"><stop stop-color="#7C3AED"/><stop offset="1" stop-color="#4F46E5"/></linearGradient>
                </defs>
              </svg>
            </div>
          </div>
        </div>

        <!-- PROGRESS BAR (INDETERMINATE SHIMMER OR DETERMINATE smooth) -->
        <div class="progress-bar-container">
          <div 
            class="progress-track"
            [class.indeterminate]="progress === null || progress === undefined"
          >
            <div 
              *ngIf="progress !== null && progress !== undefined"
              class="progress-fill-smooth" 
              [style.width.%]="progress"
            ></div>
          </div>
        </div>

        <!-- ACCESSIBLE STATUS TEXT & MICROCOPY (role="status" aria-live="polite") -->
        <div class="status-text-block" role="status" aria-live="polite">
          <h2 class="main-loader-title">{{ title }}</h2>
          <p class="microcopy-dynamic-text">{{ currentMicrocopy() }}</p>
        </div>

        <!-- CONTEXT PARAMETER CHIPS -->
        <div class="context-chips-row" *ngIf="params">
          <span class="ctx-chip" *ngIf="params.perfil">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline;vertical-align:-2px;margin-right:4px;"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            {{ params.perfil }}
          </span>
          <span class="ctx-chip" *ngIf="params.formato">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline;vertical-align:-2px;margin-right:4px;"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
            {{ params.formato }}
          </span>
          <span class="ctx-chip" *ngIf="params.nicho">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline;vertical-align:-2px;margin-right:4px;"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="9" y1="6" x2="9.01" y2="6"/><line x1="15" y1="6" x2="15.01" y2="6"/><line x1="9" y1="10" x2="9.01" y2="10"/><line x1="15" y1="10" x2="15.01" y2="10"/><line x1="9" y1="14" x2="9.01" y2="14"/><line x1="15" y1="14" x2="15.01" y2="14"/><line x1="9" y1="18" x2="15" y2="18"/></svg>
            {{ params.nicho }}
          </span>
          <span class="ctx-chip" *ngIf="params.nivel">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline;vertical-align:-2px;margin-right:4px;"><path d="M2 20h20"/><path d="M5 20V14"/><path d="M12 20V9"/><path d="M19 20V4"/></svg>
            {{ params.nivel }}
          </span>
        </div>

        <!-- ELAPSED TIMER & REASSURING HINT -->
        <div class="timer-reassure-block">
          <span class="timer-text">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline;vertical-align:-2px;margin-right:4px;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Llevas {{ formattedTime() }}
          </span>
          <span class="reassure-hint" *ngIf="elapsedSeconds() >= 20">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline;vertical-align:-2px;margin-right:4px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            Los documentos extensos o análisis profundos tardan un poco más.
          </span>
        </div>

        <!-- CANCEL BUTTON (SECONDARY & DISCREET) -->
        <div class="cancel-action-row">
          <button 
            type="button" 
            class="btn-cancel-secondary"
            (click)="onCancel()"
            title="Cancelar generación y conservar datos del formulario"
          >
            ✕ Cancelar Generación
          </button>
        </div>

      </div>

      <!-- COLLAPSIBLE STEPPER DETAILS PANEL (Hidden by default) -->
      <div 
        id="technical-details-panel"
        class="technical-details-panel" 
        *ngIf="isDetailsOpen()"
      >
        <div class="details-divider">
          <span>Detalles Técnicos del Pipeline (7 Etapas)</span>
        </div>

        <div class="stepper-grid">
          <div 
            *ngFor="let st of currentStages(); let idx = index" 
            class="stage-item-card"
            [class.is-active]="st.estado === 'activo'"
            [class.is-done]="st.estado === 'completado'"
          >
            <div class="st-badge">
              <span *ngIf="st.estado === 'completado'">✓</span>
              <span *ngIf="st.estado === 'activo'" class="dot-spinner"></span>
              <span *ngIf="st.estado === 'pendiente'">{{ st.id }}</span>
            </div>
            <div class="st-content">
              <strong>{{ st.nombre }}</strong>
              <p>{{ st.microcopy }}</p>
            </div>
          </div>
        </div>
      </div>

    </div>
  `,
  styles: [`
    :host {
      display: block;
      width: 100%;
    }

    /* COMPACT VARIANT */
    .loader-compact-box {
      display: inline-flex;
      align-items: center;
      gap: 0.65rem;
      padding: 0.5rem 0.85rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
    }
    .spinner-compact {
      width: 16px;
      height: 16px;
      border: 2px solid var(--border-subtle);
      border-top-color: #6366F1;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    .compact-text {
      font-size: 0.82rem;
      color: var(--text-secondary);
      font-weight: 600;
    }

    /* CONTAINER CARD */
    .generation-loader-container {
      min-height: 420px;
      padding: 2.25rem;
      border-radius: 24px;
      background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(99, 102, 241, 0.04) 50%, rgba(34, 211, 238, 0.03) 100%);
      border: 1px solid var(--border-subtle);
      box-shadow: var(--shadow-lg);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      position: relative;
      overflow: hidden;
      transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
    }

    .generation-loader-container.is-error-state {
      animation: shake 0.4s ease-in-out;
      border-color: rgba(239, 68, 68, 0.4);
    }

    @keyframes shake {
      0%, 100% { transform: translateX(0); }
      20%, 60% { transform: translateX(-6px); }
      40%, 80% { transform: translateX(6px); }
    }

    /* TOP BAR & TOGGLE DETAILS */
    .loader-top-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .brand-tag {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.78rem;
      font-weight: 800;
      color: #22D3EE;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    .pulse-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #22D3EE;
      box-shadow: 0 0 8px #22D3EE;
      animation: pulseDot 1.5s infinite;
    }
    .pulse-dot.paused { animation-play-state: paused; }

    @keyframes pulseDot {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.85); }
    }

    .btn-toggle-details {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      font-size: 0.78rem;
      font-weight: 700;
      padding: 0.4rem 0.85rem;
      border-radius: 20px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-toggle-details:hover {
      background: rgba(99, 102, 241, 0.12);
      color: var(--text-primary);
    }

    /* LOADING CONTENT STAGE */
    .loading-state-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      margin: auto 0;
      width: 100%;
    }

    /* 3D ORBITAL GRAPHIC */
    .orbital-stage-wrapper {
      margin-bottom: 1.5rem;
      height: 140px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .orbital-canvas {
      width: 130px;
      height: 130px;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .orbital-canvas.paused * { animation-play-state: paused !important; }

    .brand-core-nucleus {
      width: 52px;
      height: 52px;
      border-radius: 50%;
      background: var(--bg-surface);
      border: 2px solid rgba(99, 102, 241, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
      z-index: 10;
      animation: pulseNucleus 2.5s ease-in-out infinite;
    }

    @keyframes pulseNucleus {
      0%, 100% { transform: scale(0.96); box-shadow: 0 0 15px rgba(99, 102, 241, 0.2); }
      50% { transform: scale(1.04); box-shadow: 0 0 28px rgba(34, 211, 238, 0.4); }
    }

    .brand-core-isotype {
      width: 32px;
      height: 32px;
    }

    /* RINGS & PARTICLES (60FPS GPU ROTATIONS) */
    .orbit-ring {
      position: absolute;
      border-radius: 50%;
      border: 1px stroke rgba(255, 255, 255, 0.08);
      pointer-events: none;
    }

    .ring-outer {
      width: 130px;
      height: 130px;
      border: 1px dashed rgba(99, 102, 241, 0.25);
      animation: rotateOrbit 12s linear infinite;
    }
    .ring-mid {
      width: 100px;
      height: 100px;
      border: 1px dotted rgba(34, 211, 238, 0.3);
      animation: rotateOrbitReverse 8s linear infinite;
    }
    .ring-inner {
      width: 72px;
      height: 72px;
      border: 1px solid rgba(236, 72, 153, 0.2);
      animation: rotateOrbit 6s linear infinite;
    }

    .orbit-particle {
      position: absolute;
      width: 8px;
      height: 8px;
      border-radius: 50%;
    }
    .p-1 { top: 0; left: 50%; background: #6366F1; box-shadow: 0 0 6px #6366F1; }
    .p-2 { bottom: 10px; right: 20px; background: #22D3EE; box-shadow: 0 0 6px #22D3EE; }
    .p-3 { top: 15px; left: 10px; background: #EC4899; box-shadow: 0 0 6px #EC4899; }
    .p-4 { bottom: 0; right: 50%; background: #10B981; box-shadow: 0 0 6px #10B981; }

    @keyframes rotateOrbit {
      to { transform: rotate(360deg); }
    }
    @keyframes rotateOrbitReverse {
      to { transform: rotate(-360deg); }
    }

    /* FLOATING CARDS */
    .floating-card {
      position: absolute;
      padding: 0.4rem;
      border-radius: 8px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: 5;
    }
    .float-doc { top: -10px; left: -10px; animation: floatCard 4s ease-in-out infinite; }
    .float-card { bottom: -5px; right: -10px; animation: floatCard 4.5s ease-in-out infinite 0.5s; }
    .float-quiz { top: -5px; right: -15px; animation: floatCard 3.8s ease-in-out infinite 1s; }

    @keyframes floatCard {
      0%, 100% { transform: translateY(0) scale(0.95); opacity: 0.7; }
      50% { transform: translateY(-6px) scale(1.05); opacity: 1; }
    }

    /* PROGRESS BAR */
    .progress-bar-container {
      width: 100%;
      max-width: 480px;
      margin-bottom: 1.25rem;
    }
    .progress-track {
      height: 6px;
      background: var(--border-subtle);
      border-radius: 3px;
      overflow: hidden;
      position: relative;
    }
    .progress-fill-smooth {
      height: 100%;
      background: linear-gradient(90deg, #6366F1, #22D3EE, #EC4899);
      transition: width 0.4s ease;
      border-radius: 3px;
    }
    .progress-track.indeterminate::after {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.8), #22D3EE, transparent);
      animation: shimmer 1.5s infinite;
    }

    @keyframes shimmer {
      0% { transform: translateX(-100%); }
      100% { transform: translateX(100%); }
    }

    /* STATUS TEXT & MICROCOPY */
    .status-text-block {
      margin-bottom: 1.25rem;
    }
    .main-loader-title {
      font-size: 1.45rem;
      font-weight: 800;
      margin-bottom: 0.4rem;
      color: var(--text-primary);
    }
    .microcopy-dynamic-text {
      font-size: 0.95rem;
      color: var(--text-secondary);
      min-height: 24px;
      transition: opacity 0.3s ease;
    }

    /* CONTEXT CHIPS */
    .context-chips-row {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: 0.5rem;
      margin-bottom: 1.25rem;
    }
    .ctx-chip {
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.25rem 0.65rem;
      border-radius: 20px;
      background: rgba(99, 102, 241, 0.1);
      color: #6366F1;
      border: 1px solid rgba(99, 102, 241, 0.25);
    }

    /* TIMER & HINT */
    .timer-reassure-block {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.35rem;
      margin-bottom: 1.25rem;
    }
    .timer-text {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--text-muted);
    }
    .reassure-hint {
      font-size: 0.8rem;
      color: #F59E0B;
      font-weight: 600;
      animation: fadeIn 0.4s ease-in;
    }

    /* CANCEL BUTTON */
    .cancel-action-row {
      margin-top: 0.5rem;
    }
    .btn-cancel-secondary {
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      font-size: 0.82rem;
      font-weight: 600;
      padding: 0.45rem 1rem;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-cancel-secondary:hover {
      background: rgba(239, 68, 68, 0.08);
      color: #EF4444;
      border-color: rgba(239, 68, 68, 0.3);
    }

    /* TECHNICAL DETAILS STEPPER PANEL */
    .technical-details-panel {
      margin-top: 1.75rem;
      padding-top: 1.25rem;
      animation: slideDown 0.3s ease-out;
    }
    @keyframes slideDown {
      from { opacity: 0; transform: translateY(-8px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .details-divider {
      text-align: center;
      border-top: 1px solid var(--border-subtle);
      margin-bottom: 1.25rem;
      position: relative;
    }
    .details-divider span {
      position: relative;
      top: -10px;
      background: var(--bg-surface);
      padding: 0 0.75rem;
      font-size: 0.75rem;
      font-weight: 800;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    .stepper-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 0.75rem;
    }

    .stage-item-card {
      padding: 0.75rem;
      border-radius: 12px;
      background: var(--bg-app);
      border: 1.5px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }
    .stage-item-card.is-active {
      border-color: #22D3EE;
      background: rgba(34, 211, 238, 0.06);
    }
    .stage-item-card.is-done {
      border-color: #10B981;
      background: rgba(16, 185, 129, 0.06);
    }

    .st-badge {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.72rem;
      font-weight: 800;
    }
    .is-done .st-badge { background: #10B981; color: #FFF; }
    .is-active .st-badge { background: #22D3EE; color: #0F172A; }

    .dot-spinner {
      width: 10px;
      height: 10px;
      border: 2px solid #0F172A;
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    .st-content strong {
      font-size: 0.82rem;
      display: block;
    }
    .st-content p {
      font-size: 0.72rem;
      color: var(--text-muted);
      margin-top: 0.15rem;
      line-height: 1.25;
    }

    /* ERROR STATE */
    .error-state-box {
      text-align: center;
      padding: 2rem 1rem;
      margin: auto 0;
    }
    .error-icon-box {
      font-size: 2.5rem;
      margin-bottom: 0.75rem;
    }
    .error-state-box h3 {
      font-size: 1.35rem;
      font-weight: 800;
      color: #EF4444;
      margin-bottom: 0.5rem;
    }
    .error-desc {
      font-size: 0.95rem;
      color: var(--text-secondary);
      max-width: 440px;
      margin: 0 auto 1.5rem;
    }
    .error-actions-row {
      display: flex;
      justify-content: center;
      gap: 1rem;
    }
    .btn-retry {
      padding: 0.65rem 1.25rem;
      border-radius: 10px;
      background: #4F46E5;
      color: #FFF;
      border: none;
      font-weight: 700;
      font-size: 0.88rem;
      cursor: pointer;
    }
    .btn-back-form {
      padding: 0.65rem 1.25rem;
      border-radius: 10px;
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-weight: 600;
      font-size: 0.88rem;
      cursor: pointer;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

    /* PREFERS REDUCED MOTION */
    @media (prefers-reduced-motion: reduce) {
      .ring-outer, .ring-mid, .ring-inner, .float-doc, .float-card, .float-quiz, .brand-core-nucleus, .pulse-dot {
        animation: none !important;
      }
      .microcopy-dynamic-text {
        transition: none !important;
      }
    }
  `]
})
export class GenerationLoaderComponent implements OnInit, OnDestroy {
  private destroyRef = inject(DestroyRef);

  @Input() title: string = 'Creando tu contenido educativo';
  @Input() messages: string[] = [
    'Leyendo tu documento…',
    'Buscando los fragmentos más relevantes…',
    'Adaptando el lenguaje a tu audiencia…',
    'Verificando que todo esté anclado a la fuente…',
    'Guardando de forma segura…'
  ];
  @Input() progress: number | null = null;
  @Input() compact: boolean = false;
  @Input() activeStage: PipelineStage | null = null;
  @Input() params: GenerationParams | null = null;
  @Input() stages: PipelineStage[] = [];

  @Output() cancel = new EventEmitter<void>();
  @Output() retry = new EventEmitter<void>();

  // SIGNALS
  elapsedSeconds = signal<number>(0);
  microcopyIndex = signal<number>(0);
  isDetailsOpen = signal<boolean>(environment.showPipelineDetails ?? false);
  isError = signal<boolean>(false);
  errorMessage = signal<string>('');
  isTabVisible = signal<boolean>(true);

  private timerSub?: Subscription;
  private microcopySub?: Subscription;

  defaultStages: PipelineStage[] = [
    { id: 1, nombre: '1. Ingesta', microcopy: 'Extrayendo PDF/MD/TXT localmente', estado: 'activo' },
    { id: 2, nombre: '2. Chunking', microcopy: 'División en fragmentos semánticos', estado: 'pendiente' },
    { id: 3, nombre: '3. Embeddings', microcopy: 'Vectorización con Nomic/BERT', estado: 'pendiente' },
    { id: 4, nombre: '4. RAG Search', microcopy: 'Búsqueda vectorial & BM25', estado: 'pendiente' },
    { id: 5, nombre: '5. Redactor IA', microcopy: 'Adaptación pedagógica orquestada', estado: 'pendiente' },
    { id: 6, nombre: '6. Revisor Crítico', microcopy: 'Evaluación de anclaje y calidad', estado: 'pendiente' },
    { id: 7, nombre: '7. Guardado OCI', microcopy: 'Persistencia en Object Storage', estado: 'pendiente' }
  ];

  currentStages = computed(() => {
    return this.stages && this.stages.length > 0 ? this.stages : this.defaultStages;
  });

  currentMicrocopy = computed(() => {
    if (this.activeStage && this.activeStage.microcopy) {
      return this.activeStage.microcopy;
    }
    const msgs = this.messages && this.messages.length > 0 ? this.messages : ['Procesando tu contenido…'];
    return msgs[this.microcopyIndex() % msgs.length];
  });

  formattedTime = computed(() => {
    const sec = this.elapsedSeconds();
    const mins = Math.floor(sec / 60);
    const remainderSec = sec % 60;
    return `${mins}:${remainderSec < 10 ? '0' : ''}${remainderSec}`;
  });

  ngOnInit(): void {
    // 1. Timer ticker
    this.timerSub = timer(1000, 1000).subscribe(() => {
      if (this.isTabVisible() && !this.isError()) {
        this.elapsedSeconds.update(s => s + 1);
      }
    });

    // 2. Microcopy rotator (every 3 seconds)
    this.microcopySub = timer(3000, 3000).subscribe(() => {
      if (this.isTabVisible() && !this.activeStage && !this.isError()) {
        this.microcopyIndex.update(idx => idx + 1);
      }
    });

    // 3. Page Visibility listener to pause CSS/timers when tab is hidden
    if (typeof document !== 'undefined') {
      const handleVisibilityChange = () => {
        this.isTabVisible.set(!document.hidden);
      };
      document.addEventListener('visibilitychange', handleVisibilityChange);
      this.destroyRef.onDestroy(() => {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
      });
    }
  }

  ngOnDestroy(): void {
    if (this.timerSub) this.timerSub.unsubscribe();
    if (this.microcopySub) this.microcopySub.unsubscribe();
  }

  toggleDetails(): void {
    this.isDetailsOpen.update(open => !open);
  }

  triggerError(msg: string): void {
    this.isError.set(true);
    this.errorMessage.set(msg);
  }

  onCancel(): void {
    this.cancel.emit();
  }

  onRetry(): void {
    this.isError.set(false);
    this.errorMessage.set('');
    this.elapsedSeconds.set(0);
    this.retry.emit();
  }
}
