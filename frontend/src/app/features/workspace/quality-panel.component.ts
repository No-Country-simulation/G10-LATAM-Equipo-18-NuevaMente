import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EvaluacionCalidad } from '../../core/models/adaptation.model';

@Component({
  selector: 'app-quality-panel',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="quality-card glass-card" *ngIf="evaluacion">
      <div class="panel-title">
        <h3>🛡️ Panel de Calidad y Anclaje RAG</h3>
        <span class="verified-badge" [class.badge-fallback]="isCriticFallback">
          {{ isCriticFallback ? 'EVALUADOR HEURÍSTICO (FALLBACK)' : 'AUDITADO POR AGENTE CRÍTICO' }}
        </span>
      </div>

      <div class="quality-body">
        <!-- Circular SVG Gauge -->
        <div class="gauge-container">
          <svg class="gauge-svg" viewBox="0 0 100 100">
            <!-- Background track -->
            <circle cx="50" cy="50" r="40" fill="none" stroke="var(--slate-200)" stroke-width="8"/>
            <!-- Animated Score Fill -->
            <circle 
              cx="50" 
              cy="50" 
              r="40" 
              fill="none" 
              stroke="url(#gauge-gradient)" 
              stroke-width="8"
              stroke-linecap="round"
              [style.strokeDasharray]="251.2"
              [style.strokeDashoffset]="251.2 * (1 - normalizedScore)"
              class="gauge-circle"
            />
            <defs>
              <linearGradient id="gauge-gradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="#22D3EE"/>
                <stop offset="100%" stop-color="#10B981"/>
              </linearGradient>
            </defs>
          </svg>
          <div class="gauge-label">
            <span class="gauge-number">{{ (normalizedScore * 100) | number:'1.0-0' }}%</span>
            <span class="gauge-sub">Fidelidad</span>
          </div>
        </div>

        <!-- Details Column -->
        <div class="quality-details">
          <div class="metric-row">
            <span class="metric-key">Claridad Pedagógica:</span>
            <span class="badge-clarity" [class.alta]="evaluacion.claridad_pedagogica === 'Alta'">
              {{ evaluacion.claridad_pedagogica }}
            </span>
          </div>

          <div class="metric-row" *ngIf="criticProvider">
            <span class="metric-key">Auditor / Procedencia:</span>
            <span class="badge-provenance">
              {{ criticProvider }} <span *ngIf="criticModel">({{ criticModel }})</span>
            </span>
          </div>

          <div class="fallback-note" *ngIf="isCriticFallback">
            <span>ℹ️ El crítico LLM no estuvo disponible; se aplicó la verificación léxica heurística sin inflar puntuaciones.</span>
          </div>

          <div class="observations-box">
            <span class="obs-title">Observaciones del Revisor:</span>
            <p>{{ evaluacion.observaciones }}</p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .quality-card {
      padding: 1.75rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
    }

    .panel-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .panel-title h3 {
      font-size: 1.25rem;
      font-weight: 800;
    }

    .verified-badge {
      font-size: 0.72rem;
      font-weight: 800;
      color: #10B981;
      background: rgba(16, 185, 129, 0.1);
      padding: 0.25rem 0.6rem;
      border-radius: 20px;
    }

    .quality-body {
      display: flex;
      gap: 2rem;
      align-items: center;
    }

    .gauge-container {
      position: relative;
      width: 120px;
      height: 120px;
      flex-shrink: 0;
    }

    .gauge-svg {
      width: 100%;
      height: 100%;
      transform: rotate(-90deg);
    }

    .gauge-circle {
      transition: stroke-dashoffset 1s ease-out;
    }

    .gauge-label {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }

    .gauge-number {
      font-size: 1.5rem;
      font-weight: 800;
      color: var(--text-primary);
    }

    .gauge-sub {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .quality-details {
      flex: 1;
    }

    .metric-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1rem;
    }

    .metric-key {
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--text-secondary);
    }

    .badge-clarity {
      padding: 0.2rem 0.6rem;
      border-radius: 6px;
      font-size: 0.82rem;
      font-weight: 700;
      background: var(--slate-200);
      color: var(--text-primary);
    }

    .badge-clarity.alta {
      background: rgba(16, 185, 129, 0.15);
      color: #059669;
    }

    .badge-provenance {
      padding: 0.2rem 0.6rem;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 700;
      background: rgba(99, 102, 241, 0.12);
      color: #4f46e5;
    }

    .badge-fallback {
      color: #d97706 !important;
      background: rgba(245, 158, 11, 0.12) !important;
    }

    .fallback-note {
      padding: 0.6rem 0.85rem;
      border-radius: 8px;
      background: rgba(245, 158, 11, 0.08);
      border: 1px solid rgba(245, 158, 11, 0.25);
      color: #b45309;
      font-size: 0.8rem;
      margin-bottom: 0.75rem;
      line-height: 1.4;
    }

    .observations-box {
      background: var(--bg-app);
      padding: 0.85rem 1rem;
      border-radius: 10px;
      font-size: 0.88rem;
    }

    .obs-title {
      font-weight: 700;
      color: var(--text-muted);
      font-size: 0.78rem;
      display: block;
      margin-bottom: 0.25rem;
    }

    .observations-box p {
      color: var(--text-primary);
    }
  `]
})
export class QualityPanelComponent {
  @Input() evaluacion?: EvaluacionCalidad;
  @Input() metadatos?: any;

  get normalizedScore(): number {
    if (!this.evaluacion || this.evaluacion.anclaje_fuente_score === undefined) return 0;
    const s = this.evaluacion.anclaje_fuente_score;
    return s > 1 ? s / 100 : s;
  }

  get criticProvider(): string | undefined {
    return this.metadatos?.proveedor_critico || this.metadatos?.critic_provider;
  }

  get criticModel(): string | undefined {
    return this.metadatos?.modelo_critico || this.metadatos?.critic_model;
  }

  get isCriticFallback(): boolean {
    const prov = (this.criticProvider || '').toLowerCase();
    const obs = (this.evaluacion?.observaciones || '').toLowerCase();
    return prov.includes('heuristico') || prov.includes('analizador_anclaje') || obs.includes('heurística') || obs.includes('heuristic');
  }
}
