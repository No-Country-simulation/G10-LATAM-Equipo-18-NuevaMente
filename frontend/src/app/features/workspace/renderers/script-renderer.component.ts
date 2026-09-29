import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GuionClaseItem } from '../../../core/models/adaptation.model';

@Component({
  selector: 'app-script-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="script-container" *ngIf="items && items.length > 0">
      <div class="script-header glass-card">
        <div class="duration-badge">⏱️ DURACIÓN TOTAL ESTIMADA: {{ getTotalDuration() }} SEG ({{ (getTotalDuration() / 60) | number:'1.1-1' }} MIN)</div>
        <h2>Guion Audiovisual para Clase / Video</h2>
        <p>Estructura por escenas con narración locutada y recursos visuales recomendados.</p>
      </div>

      <!-- Scenes Table / Timeline -->
      <div class="scenes-list">
        <div class="scene-row glass-card" *ngFor="let scene of items">
          <div class="scene-meta">
            <span class="scene-number">Escena {{ scene.escena }}</span>
            <span class="scene-duration">⏱️ {{ scene.duracion_seg }}s</span>
          </div>

          <div class="scene-body">
            <div class="narration-box">
              <span class="box-label">🎙️ NARRACIÓN / GUION HABLADO</span>
              <p>{{ scene.narracion }}</p>
            </div>

            <div class="visual-box">
              <span class="box-label">🎨 APOYO VISUAL / PANTALLA</span>
              <p>{{ scene.apoyo_visual }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .script-container {
      max-width: 860px;
      margin: 0 auto;
    }

    .script-header {
      padding: 2rem;
      border-radius: 20px;
      background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(245, 158, 11, 0.08) 100%);
      border: 1px solid rgba(245, 158, 11, 0.3);
      margin-bottom: 2rem;
    }

    .duration-badge {
      font-size: 0.78rem;
      font-weight: 800;
      color: #F59E0B;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }

    .script-header h2 {
      font-size: 1.5rem;
      margin-bottom: 0.5rem;
    }

    .script-header p {
      color: var(--text-secondary);
      font-size: 0.95rem;
    }

    .scenes-list {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .scene-row {
      padding: 1.5rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      display: flex;
      gap: 1.5rem;
    }

    .scene-meta {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      width: 110px;
      flex-shrink: 0;
    }

    .scene-number {
      font-size: 1.1rem;
      font-weight: 800;
      color: #F59E0B;
    }

    .scene-duration {
      font-size: 0.8rem;
      color: var(--text-muted);
      font-weight: 600;
    }

    .scene-body {
      flex: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }

    .narration-box, .visual-box {
      background: var(--bg-app);
      padding: 1rem;
      border-radius: 10px;
    }

    .box-label {
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--text-muted);
      display: block;
      margin-bottom: 0.4rem;
    }

    .scene-body p {
      font-size: 0.92rem;
      line-height: 1.5;
      color: var(--text-primary);
    }

    @media (max-width: 768px) {
      .scene-row { flex-direction: column; }
      .scene-body { grid-template-columns: 1fr; }
    }
  `]
})
export class ScriptRendererComponent {
  @Input({ required: true }) items: GuionClaseItem[] = [];

  getTotalDuration(): number {
    return this.items.reduce((acc, curr) => acc + (curr.duracion_seg || 0), 0);
  }
}
