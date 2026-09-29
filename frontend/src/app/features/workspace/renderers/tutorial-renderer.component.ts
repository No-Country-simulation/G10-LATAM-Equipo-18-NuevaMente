import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TutorialItem } from '../../../core/models/adaptation.model';

@Component({
  selector: 'app-tutorial-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="tutorial-container" *ngIf="items && items.length > 0">
      <div class="tutorial-header">
        <span class="step-count">Tutorial de {{ items.length }} Pasos</span>
        <div class="progress-checklist">
          <span>Completados: {{ completedCount() }} / {{ items.length }}</span>
        </div>
      </div>

      <!-- Step Timeline -->
      <div class="timeline-wrapper">
        <div 
          *ngFor="let step of items; let idx = index" 
          class="timeline-step-card"
          [class.step-completed]="isStepCompleted(idx)"
        >
          <div class="step-indicator">
            <button class="btn-check" (click)="toggleStepCompleted(idx)">
              {{ isStepCompleted(idx) ? '✓' : step.paso }}
            </button>
            <div class="step-line" *ngIf="idx < items.length - 1"></div>
          </div>

          <div class="step-content glass-card">
            <div class="step-title-row">
              <h3>Paso {{ step.paso }}: {{ step.titulo }}</h3>
            </div>

            <p class="step-instruccion">{{ step.instruccion }}</p>

            <!-- Code Block with JetBrains Mono -->
            <div class="code-block-wrapper" *ngIf="step.ejemplo">
              <div class="code-block-header">
                <span>CÓDIGO / COMANDO CLI</span>
                <button class="btn-copy" (click)="copyCode(step.ejemplo)">Copiar</button>
              </div>
              <pre class="code-content"><code>{{ cleanCodeSnippet(step.ejemplo) }}</code></pre>
            </div>

            <!-- Warning Callout Card -->
            <div class="warning-callout" *ngIf="step.advertencia">
              <span class="warning-icon">⚠️</span>
              <div class="warning-text">
                <strong>Advertencia importante:</strong>
                <p>{{ step.advertencia }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .tutorial-container {
      max-width: 800px;
      margin: 0 auto;
    }

    .tutorial-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border-subtle);
    }

    .step-count {
      font-weight: 700;
      font-size: 1.1rem;
    }

    .timeline-wrapper {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .timeline-step-card {
      display: flex;
      gap: 1.25rem;
    }

    .step-indicator {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 40px;
      flex-shrink: 0;
    }

    .btn-check {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: var(--primary-600);
      color: #FFFFFF;
      border: none;
      font-weight: 800;
      font-size: 1rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
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
      font-size: 1.2rem;
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
      font-family: var(--font-code);
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

  cleanCodeSnippet(raw: string): string {
    return raw.replace(/^```[a-z]*\n?/i, '').replace(/```$/i, '').trim();
  }

  copyCode(code: string): void {
    const clean = this.cleanCodeSnippet(code);
    navigator.clipboard.writeText(clean);
  }
}
