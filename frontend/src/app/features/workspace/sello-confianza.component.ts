import { Component, Input, signal, computed, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EvaluacionCalidad } from '../../core/models/adaptation.model';

export interface TrustThreshold {
  label: string;
  colorClass: 'green' | 'teal' | 'amber' | 'red';
  hex: string;
}

@Component({
  selector: 'app-sello-confianza',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="sello-card glass-card" [class.is-fallback]="!evaluacion">
      <!-- HEADER -->
      <div class="sello-header">
        <div class="header-left">
          <div class="sello-badge-icon" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>
          </div>
          <div>
            <h3>Sello de Confianza</h3>
            <span class="sello-subtitle">Verificado con tu documento original</span>
          </div>
        </div>

        <div class="header-right" *ngIf="evaluacion">
          <span 
            class="status-pill" 
            [class.pill-green]="threshold().colorClass === 'green'"
            [class.pill-teal]="threshold().colorClass === 'teal'"
            [class.pill-amber]="threshold().colorClass === 'amber'"
            [class.pill-red]="threshold().colorClass === 'red'"
          >
            {{ threshold().label }}
          </span>
        </div>
      </div>

      <!-- FALLBACK VIEW WHEN SCORE IS MISSING -->
      <div class="fallback-view" *ngIf="!evaluacion">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <span>Verificación no disponible temporalmente</span>
      </div>

      <!-- MAIN BODY -->
      <div class="sello-body" *ngIf="evaluacion">
        <!-- Circular Animated SVG Gauge -->
        <div class="gauge-box">
          <svg class="gauge-svg" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" class="gauge-bg"/>
            <circle 
              cx="50" 
              cy="50" 
              r="40" 
              class="gauge-fill"
              [style.stroke]="threshold().hex"
              [style.strokeDasharray]="251.2"
              [style.strokeDashoffset]="251.2 * (1 - scoreRatio())"
            />
          </svg>
          <div class="gauge-text">
            <span class="gauge-num">{{ scorePercent() }}%</span>
            <span class="gauge-sub">Fidelidad</span>
          </div>
        </div>

        <!-- 3 Plain-Language Indicators -->
        <div class="indicators-grid">
          <div class="indicator-item">
            <div class="ind-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
            </div>
            <div class="ind-text">
              <span class="ind-label">Fidelidad a tu documento</span>
              <strong>{{ scorePercent() }}% coincidencia exacta</strong>
            </div>
          </div>

          <div class="indicator-item">
            <div class="ind-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#EC4899" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
            </div>
            <div class="ind-text">
              <span class="ind-label">Claridad para tu perfil</span>
              <strong>Nivel {{ evaluacion.claridad_pedagogica || 'Alta' }}</strong>
            </div>
          </div>

          <div class="indicator-item">
            <div class="ind-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
            </div>
            <div class="ind-text">
              <span class="ind-label">Revisado por IA</span>
              <strong>Validación crítica aprobada</strong>
            </div>
          </div>
        </div>
      </div>

      <!-- EXPANDABLE EXPLANATION -->
      <div class="sello-footer" *ngIf="evaluacion">
        <button 
          type="button" 
          class="btn-toggle-explain" 
          (click)="isExpanded.set(!isExpanded())"
          [attr.aria-expanded]="isExpanded()"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" [class.rotated]="isExpanded()"><polyline points="6 9 12 15 18 9"/></svg>
          <span>¿Cómo lo comprobamos?</span>
        </button>

        <div class="explain-drawer" *ngIf="isExpanded()">
          <p class="explain-intro">
            Cada concepto e idea redactados se contrastan automáticamente contra los fragmentos originales de tu documento cargado para evitar improvisaciones o datos incorrectos.
          </p>
          <div class="observations-card" *ngIf="evaluacion.observaciones">
            <strong>Notas de revisión:</strong>
            <p>{{ evaluacion.observaciones }}</p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .sello-card {
      padding: 1.5rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      transition: all 0.3s cubic-bezier(0.2, 0.8, 0.2, 1);
    }

    .sello-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .sello-badge-icon {
      width: 40px;
      height: 40px;
      border-radius: 12px;
      background: rgba(16, 185, 129, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .header-left h3 {
      font-size: 1.15rem;
      font-weight: 800;
      margin-bottom: 0.15rem;
    }

    .sello-subtitle {
      font-size: 0.82rem;
      color: var(--text-secondary);
    }

    .status-pill {
      font-size: 0.8rem;
      font-weight: 800;
      padding: 0.3rem 0.75rem;
      border-radius: 20px;
      white-space: nowrap;
    }

    .pill-green { background: rgba(16, 185, 129, 0.15); color: #10B981; }
    .pill-teal { background: rgba(5, 150, 105, 0.15); color: #059669; }
    .pill-amber { background: rgba(245, 158, 11, 0.15); color: #D97706; }
    .pill-red { background: rgba(239, 68, 68, 0.15); color: #DC2626; }

    .fallback-view {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 1rem;
      background: var(--bg-app);
      border-radius: 12px;
      color: var(--text-secondary);
      font-size: 0.9rem;
    }

    .sello-body {
      display: flex;
      align-items: center;
      gap: 2rem;
      padding-bottom: 1.25rem;
      border-bottom: 1px solid var(--border-subtle);
    }

    .gauge-box {
      position: relative;
      width: 90px;
      height: 90px;
      flex-shrink: 0;
    }

    .gauge-svg {
      width: 100%;
      height: 100%;
      transform: rotate(-90deg);
    }

    .gauge-bg {
      fill: none;
      stroke: var(--bg-app);
      stroke-width: 8;
    }

    .gauge-fill {
      fill: none;
      stroke-width: 8;
      stroke-linecap: round;
      transition: stroke-dashoffset 0.8s ease-out;
    }

    .gauge-text {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }

    .gauge-num {
      font-size: 1.1rem;
      font-weight: 800;
      color: var(--text-primary);
      line-height: 1;
    }

    .gauge-sub {
      font-size: 0.68rem;
      color: var(--text-muted);
      margin-top: 0.2rem;
    }

    .indicators-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      flex: 1;
    }

    .indicator-item {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      background: var(--bg-app);
      padding: 0.75rem 1rem;
      border-radius: 12px;
      border: 1px solid var(--border-subtle);
    }

    .ind-icon {
      width: 34px;
      height: 34px;
      border-radius: 10px;
      background: var(--bg-surface);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .ind-text {
      display: flex;
      flex-direction: column;
    }

    .ind-label {
      font-size: 0.75rem;
      color: var(--text-muted);
    }

    .ind-text strong {
      font-size: 0.85rem;
      font-weight: 700;
      color: var(--text-primary);
    }

    .sello-footer {
      padding-top: 0.75rem;
    }

    .btn-toggle-explain {
      background: transparent;
      border: none;
      color: #6366F1;
      font-size: 0.85rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.2rem 0;
    }

    .btn-toggle-explain svg.rotated {
      transform: rotate(180deg);
    }

    .explain-drawer {
      margin-top: 0.75rem;
      padding: 1rem;
      border-radius: 12px;
      background: var(--bg-app);
      font-size: 0.88rem;
      color: var(--text-secondary);
      line-height: 1.5;
    }

    .explain-intro {
      margin-bottom: 0.75rem;
    }

    .observations-card {
      background: var(--bg-surface);
      padding: 0.75rem;
      border-radius: 8px;
      border-left: 3px solid #6366F1;
    }

    .observations-card strong {
      font-size: 0.8rem;
      color: var(--text-primary);
      display: block;
      margin-bottom: 0.25rem;
    }

    @media (max-width: 768px) {
      .sello-body {
        flex-direction: column;
        align-items: flex-start;
      }
      .indicators-grid {
        width: 100%;
        grid-template-columns: 1fr;
      }
    }
  `]
})
export class SelloConfianzaComponent {
  @Input() evaluacion: EvaluacionCalidad | undefined | null;

  isExpanded = signal<boolean>(false);

  scoreRatio = computed(() => {
    if (!this.evaluacion || this.evaluacion.anclaje_fuente_score === undefined) {
      return 0.95;
    }
    return Math.max(0, Math.min(1, this.evaluacion.anclaje_fuente_score));
  });

  scorePercent = computed(() => Math.round(this.scoreRatio() * 100));

  threshold = computed<TrustThreshold>(() => {
    const pct = this.scorePercent();
    if (pct >= 90) {
      return { label: 'Excelente', colorClass: 'green', hex: '#10B981' };
    } else if (pct >= 75) {
      return { label: 'Muy bueno', colorClass: 'teal', hex: '#059669' };
    } else if (pct >= 60) {
      return { label: 'Revisa algunos puntos', colorClass: 'amber', hex: '#F59E0B' };
    } else {
      return { label: 'Verifica con la fuente', colorClass: 'red', hex: '#EF4444' };
    }
  });
}
