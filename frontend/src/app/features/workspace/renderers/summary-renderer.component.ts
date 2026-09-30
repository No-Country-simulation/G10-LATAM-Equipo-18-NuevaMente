import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResumenEjecutivoItem } from '../../../core/models/adaptation.model';

@Component({
  selector: 'app-summary-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="summary-container" *ngIf="items && items.length > 0">
      <!-- TL;DR Quick Card -->
      <div class="tldr-banner glass-card">
        <div class="tldr-badge">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          <span>SÍNTESIS RÁPIDA</span>
        </div>
        <h2>Resumen Ejecutivo</h2>
        <p>Los puntos más importantes condensados para una lectura rápida y directa.</p>
      </div>

      <!-- Key Points Grid -->
      <div class="summary-grid">
        <div class="summary-card glass-card" *ngFor="let item of items; let idx = index">
          <div class="card-header">
            <span class="point-num">{{ formatIndex(idx) }}</span>
            <h4>{{ item.punto_clave }}</h4>
          </div>

          <div class="impact-block">
            <span class="impact-label">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
              Por qué importa
            </span>
            <p>{{ item.impacto_negocio }}</p>
          </div>

          <div class="source-link" *ngIf="item.fuentes && item.fuentes.length > 0">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            <span>Ver en tu documento · Pág. {{ item.fuentes[0].pagina || 1 }}</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .summary-container {
      width: 100%;
    }

    .tldr-banner {
      padding: 1.75rem;
      border-radius: 18px;
      background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(16, 185, 129, 0.08) 100%);
      border: 1px solid rgba(16, 185, 129, 0.25);
      margin-bottom: 1.5rem;
    }

    .tldr-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.75rem;
      font-weight: 800;
      color: #10B981;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }

    .tldr-banner h2 {
      font-size: 1.4rem;
      font-weight: 800;
      margin-bottom: 0.35rem;
      color: var(--text-primary);
    }

    .tldr-banner p {
      color: var(--text-secondary);
      font-size: 0.92rem;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 1.25rem;
    }

    .summary-card {
      padding: 1.5rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .card-header {
      display: flex;
      gap: 0.85rem;
      align-items: flex-start;
      margin-bottom: 1rem;
    }

    .point-num {
      font-size: 0.95rem;
      font-weight: 800;
      color: #10B981;
      background: rgba(16, 185, 129, 0.12);
      padding: 0.25rem 0.55rem;
      border-radius: 8px;
      flex-shrink: 0;
    }

    .card-header h4 {
      font-size: 1.05rem;
      font-weight: 700;
      line-height: 1.4;
      color: var(--text-primary);
    }

    .impact-block {
      background: var(--bg-app);
      padding: 1rem;
      border-radius: 12px;
      margin-bottom: 1rem;
      border: 1px solid var(--border-subtle);
    }

    .impact-label {
      font-size: 0.75rem;
      font-weight: 800;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 0.35rem;
      margin-bottom: 0.4rem;
    }

    .impact-block p {
      font-size: 0.9rem;
      color: var(--text-primary);
      line-height: 1.5;
    }

    .source-link {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.8rem;
      color: #0284C7;
      font-weight: 600;
    }
  `]
})
export class SummaryRendererComponent {
  @Input({ required: true }) items: ResumenEjecutivoItem[] = [];

  formatIndex(idx: number): string {
    const num = idx + 1;
    return num < 10 ? `0${num}` : `${num}`;
  }
}
