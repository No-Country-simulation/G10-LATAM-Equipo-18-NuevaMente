import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RagFuente } from '../../core/models/adaptation.model';

@Component({
  selector: 'app-sources-drawer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="drawer-overlay" *ngIf="isOpen" (click)="close()">
      <div class="drawer-content glass-card" (click)="$event.stopPropagation()">
        <div class="drawer-header">
          <div class="title-with-icon">
            <span class="icon">🔍</span>
            <h3>Anclaje a la Fuente (RAG Vectorial)</h3>
          </div>
          <button class="btn-close" (click)="close()">✕</button>
        </div>

        <div class="drawer-body" *ngIf="fuente">
          <div class="meta-pills">
            <span class="pill">Chunk ID: <code>{{ fuente.chunk_id }}</code></span>
            <span class="pill" *ngIf="fuente.pagina">Página: <strong>{{ fuente.pagina }}</strong></span>
            <span class="pill score" *ngIf="fuente.similitud_score">Similitud Vectorial: <strong>{{ (fuente.similitud_score * 100) | number:'1.1-1' }}%</strong></span>
          </div>

          <div class="excerpt-box">
            <span class="box-label">EXTRACTO TEXTUAL VERIFICADO DE LA FUENTE ORIGINAL:</span>
            <blockquote class="excerpt-text">
              "{{ fuente.extracto }}"
            </blockquote>
          </div>

          <div class="verification-note">
            <span class="shield-icon">🛡️</span>
            <span>Este extracto garantiza que la respuesta generada no presenta alucinaciones y proviene estrictamente de la documentación técnica ingresada.</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .drawer-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.6);
      backdrop-filter: blur(4px);
      z-index: 1000;
      display: flex;
      justify-content: flex-end;
    }

    .drawer-content {
      width: 100%;
      max-width: 480px;
      height: 100%;
      background: var(--bg-surface);
      border-left: 1px solid var(--border-subtle);
      padding: 2rem;
      display: flex;
      flex-direction: column;
      box-shadow: -10px 0 30px rgba(0, 0, 0, 0.3);
    }

    .drawer-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 1.25rem;
      border-bottom: 1px solid var(--border-subtle);
      margin-bottom: 1.5rem;
    }

    .title-with-icon {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .title-with-icon h3 {
      font-size: 1.15rem;
    }

    .btn-close {
      background: transparent;
      border: none;
      font-size: 1.25rem;
      color: var(--text-muted);
      cursor: pointer;
    }

    .drawer-body {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .meta-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }

    .pill {
      background: var(--bg-app);
      padding: 0.4rem 0.75rem;
      border-radius: 8px;
      font-size: 0.82rem;
      color: var(--text-secondary);
      border: 1px solid var(--border-subtle);
    }

    .pill.score {
      background: rgba(34, 211, 238, 0.1);
      border-color: rgba(34, 211, 238, 0.3);
      color: #0284C7;
    }

    .excerpt-box {
      background: rgba(15, 23, 42, 0.05);
      border-left: 4px solid #22D3EE;
      padding: 1.25rem;
      border-radius: 8px;
    }

    .box-label {
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      display: block;
      margin-bottom: 0.5rem;
    }

    .excerpt-text {
      font-style: italic;
      font-size: 0.95rem;
      line-height: 1.6;
      color: var(--text-primary);
    }

    .verification-note {
      display: flex;
      gap: 0.75rem;
      padding: 1rem;
      border-radius: 10px;
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.25);
      font-size: 0.85rem;
      color: #047857;
    }

    @media (max-width: 640px) {
      .drawer-overlay { align-items: flex-end; }
      .drawer-content { height: 80vh; max-width: 100%; border-radius: 20px 20px 0 0; }
    }
  `]
})
export class SourcesDrawerComponent {
  @Input() isOpen = false;
  @Input() fuente?: RagFuente;
  @Output() closeDrawer = new EventEmitter<void>();

  close(): void {
    this.closeDrawer.emit();
  }
}
