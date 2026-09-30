import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TutorialItem } from '../../../core/models/adaptation.model';

@Component({
  selector: 'app-tutorial-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="tutorial-container" *ngIf="items && items.length > 0">
      <!-- TUTORIAL HEADER & INDEX NAV BAR -->
      <div class="tutorial-header glass-card">
        <div class="header-left">
          <span class="step-count">Tutorial Paso a Paso ({{ items.length }} Módulos)</span>
          <div class="progress-checklist">
            <span>Completados: {{ completedCount() }} / {{ items.length }}</span>
          </div>
        </div>

        <!-- QUICK STEP JUMP SELECTOR FOR HIGH VOLUMES -->
        <div class="quick-jump-wrapper" *ngIf="items.length > 5">
          <label for="step-jump-select" class="jump-label">Ir a módulo:</label>
          <select 
            id="step-jump-select" 
            class="step-jump-select" 
            (change)="scrollToStep($event)"
          >
            <option value="" disabled selected>Selecciona un paso...</option>
            <option *ngFor="let item of items; let idx = index" [value]="'step-' + idx">
              Paso {{ item.paso || (idx + 1) }}: {{ item.titulo || ('Módulo ' + (idx + 1)) }}
            </option>
          </select>
        </div>
      </div>

      <!-- STEP TIMELINE -->
      <div class="timeline-wrapper">
        <div 
          *ngFor="let step of items; let idx = index" 
          [id]="'step-' + idx"
          class="timeline-step-card"
          [class.step-completed]="isStepCompleted(idx)"
        >
          <div class="step-indicator">
            <button 
              type="button" 
              class="btn-check" 
              (click)="toggleStepCompleted(idx)"
              [attr.aria-label]="'Marcar paso ' + (step.paso || (idx + 1)) + ' como completado'"
            >
              {{ isStepCompleted(idx) ? '✓' : (step.paso || (idx + 1)) }}
            </button>
            <div class="step-line" *ngIf="idx < items.length - 1"></div>
          </div>

          <div class="step-content glass-card">
            <div class="step-title-row">
              <h3>Paso {{ step.paso || (idx + 1) }}: {{ step.titulo || 'Instrucción Técnica' }}</h3>
            </div>

            <p class="step-instruccion">{{ step.instruccion }}</p>

            <!-- Code Block -->
            <div class="code-block-wrapper" *ngIf="step.ejemplo">
              <div class="code-block-header">
                <span>COMANDO / CÓDIGO SUGERIDO</span>
                <button type="button" class="btn-copy" (click)="copyCode(step.ejemplo)">Copiar</button>
              </div>
              <pre class="code-content"><code>{{ cleanCodeSnippet(step.ejemplo) }}</code></pre>
            </div>

            <!-- Warning Callout Card -->
            <div class="warning-callout" *ngIf="step.advertencia">
              <span class="warning-icon">⚠️</span>
              <div class="warning-text">
                <strong>Nota de seguridad:</strong>
                <p>{{ step.advertencia }}</p>
              </div>
            </div>

            <!-- Source Citation -->
            <div class="source-link" *ngIf="step.fuentes && step.fuentes.length > 0">
              <span>📄 Ver en tu documento · Pág. {{ step.fuentes[0].pagina || 1 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .tutorial-container {
      width: 100%;
    }

    .tutorial-header {
      padding: 1.25rem 1.5rem;
      border-radius: 18px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      margin-bottom: 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 1rem;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 1.25rem;
    }

    .step-count {
      font-weight: 800;
      font-size: 1.1rem;
      color: var(--text-primary);
    }

    .progress-checklist {
      font-size: 0.85rem;
      font-weight: 700;
      color: #059669;
      background: rgba(16, 185, 129, 0.12);
      padding: 0.25rem 0.65rem;
      border-radius: 20px;
    }

    .quick-jump-wrapper {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .jump-label {
      font-size: 0.82rem;
      font-weight: 700;
      color: var(--text-muted);
    }

    .step-jump-select {
      padding: 0.4rem 0.75rem;
      border-radius: 8px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-size: 0.82rem;
      font-weight: 600;
      outline: none;
      max-width: 240px;
    }

    .timeline-wrapper {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .timeline-step-card {
      display: flex;
      gap: 1.25rem;
      scroll-margin-top: 5rem;
    }

    .step-indicator {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 40px;
      flex-shrink: 0;
    }

    .btn-check {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: #4F46E5;
      color: #FFFFFF;
      border: none;
      font-weight: 800;
      font-size: 0.95rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
    }

    .step-completed .btn-check {
      background: #10B981;
    }

    .step-line {
      flex: 1;
      width: 2px;
      background: var(--border-subtle);
      margin-top: 0.5rem;
    }

    .step-content {
      flex: 1;
      padding: 1.5rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
    }

    .step-title-row h3 {
      font-size: 1.15rem;
      font-weight: 800;
      margin-bottom: 0.75rem;
      color: var(--text-primary);
    }

    .step-instruccion {
      font-size: 0.95rem;
      color: var(--text-secondary);
      line-height: 1.6;
      margin-bottom: 1.25rem;
    }

    .code-block-wrapper {
      background: #0D1117;
      border-radius: 10px;
      overflow: hidden;
      margin-bottom: 1.25rem;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .code-block-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem 1rem;
      background: rgba(255, 255, 255, 0.05);
      font-size: 0.72rem;
      font-weight: 700;
      color: #8B949E;
    }

    .btn-copy {
      background: transparent;
      border: 1px solid rgba(255, 255, 255, 0.2);
      color: #C9D1D9;
      font-size: 0.75rem;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      cursor: pointer;
    }

    .code-content {
      padding: 1rem;
      font-family: Consolas, Monaco, monospace;
      font-size: 0.88rem;
      color: #58A6FF;
      overflow-x: auto;
      margin: 0;
    }

    .warning-callout {
      display: flex;
      gap: 0.75rem;
      padding: 1rem;
      border-radius: 10px;
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: #D97706;
      font-size: 0.88rem;
      margin-bottom: 0.75rem;
    }

    .source-link {
      font-size: 0.8rem;
      color: #0284C7;
      font-weight: 600;
    }
  `]
})
export class TutorialRendererComponent {
  @Input({ required: true }) items: TutorialItem[] = [];

  completedSteps = signal<Set<number>>(new Set());

  completedCount(): number {
    return this.completedSteps().size;
  }

  isStepCompleted(idx: number): boolean {
    return this.completedSteps().has(idx);
  }

  toggleStepCompleted(idx: number): void {
    this.completedSteps.update(set => {
      const next = new Set(set);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  }

  scrollToStep(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const targetId = select.value;
    if (targetId) {
      const el = document.getElementById(targetId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }

  cleanCodeSnippet(raw: string): string {
    return raw.replace(/^```[a-z]*\n?/i, '').replace(/```$/i, '').trim();
  }

  copyCode(code: string): void {
    const clean = this.cleanCodeSnippet(code);
    navigator.clipboard.writeText(clean);
  }
}
