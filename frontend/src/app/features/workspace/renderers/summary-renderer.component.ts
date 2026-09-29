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
        <div class="tldr-badge">⚡ RESUMEN DE ALTO NIVEL (TL;DR)</div>
        <h2>Síntesis Estratégica en 30 Segundos</h2>
        <p>Documento condensado en métricas clave e impacto directo de negocio para tomadores de decisiones.</p>
      </div>

      <!-- Business Impact Grid -->
      <div class="summary-grid">
        <div class="summary-card glass-card" *ngFor="let item of items; let idx = index">
          <div class="card-header">
            <span class="point-num">0{{ idx + 1 }}</span>
            <h4>{{ item.punto_clave }}</h4>
          </div>

          <div class="impact-block">
            <span class="impact-label">📊 IMPACTO DE NEGOCIO</span>
            <p>{{ item.impacto_negocio }}</p>
          </div>

          <div class="rag-source-link" *ngIf="item.fuentes && item.fuentes.length > 0">
            <span class="source-tag">🔍 Cita RAG [Pág {{ item.fuentes[0].pagina || 1 }}]</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .summary-container {
      max-width: 840px;
      margin: 0 auto;
    }

    .tldr-banner {
      padding: 2rem;
      border-radius: 20px;
      background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(16, 185, 129, 0.08) 100%);
      border: 1px solid rgba(16, 185, 129, 0.3);
      margin-bottom: 2rem;
    }

    .tldr-badge {
      font-size: 0.75rem;
      font-weight: 800;
      color: #10B981;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }

    .tldr-banner h2 {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }

    .tldr-banner p {
      color: var(--text-secondary);
      font-size: 0.95rem;
    }

    .summary-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
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
      gap: 1rem;
      align-items: flex-start;
      margin-bottom: 1rem;
    }

    .point-num {
      font-size: 1.25rem;
      font-weight: 800;
      color: #10B981;
      background: rgba(16, 185, 129, 0.1);
      padding: 0.2rem 0.6rem;
      border-radius: 8px;
    }

    .card-header h4 {
      font-size: 1.1rem;
      line-height: 1.35;
    }

    .impact-block {
      background: var(--bg-app);
      padding: 1rem;
      border-radius: 10px;
      margin-bottom: 1rem;
    }

    .impact-label {
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--text-muted);
      display: block;
      margin-bottom: 0.3rem;
    }

    .impact-block p {
      font-size: 0.9rem;
      color: var(--text-primary);
      line-height: 1.5;
    }

    .source-tag {
      font-size: 0.78rem;
      color: #0284C7;
      font-weight: 600;
    }
  `]
})
export class SummaryRendererComponent {
  @Input({ required: true }) items: ResumenEjecutivoItem[] = [];
}
