import { Component, Input, Output, EventEmitter, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface PipelineStage {
  id: number;
  nombre: string;
  microcopy: string;
  estado: 'pendiente' | 'activo' | 'completado' | 'error';
  duracion_ms?: number;
}

@Component({
  selector: 'app-pipeline-progress',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="pipeline-progress-wrapper glass-card">
      <div class="progress-header">
        <div class="title-status">
          <span class="pulse-dot"></span>
          <h3>Pipeline Multi-Agente & RAG Reranking en Ejecución</h3>
        </div>
        <button class="btn-cancel" (click)="onCancel()">Cancelar Pipeline</button>
      </div>

      <!-- 7-Stage Stepper Grid -->
      <div class="stepper-container">
        <div 
          *ngFor="let stage of stages(); let idx = index" 
          class="stage-card"
          [class.activo]="stage.estado === 'activo'"
          [class.completado]="stage.estado === 'completado'"
        >
          <div class="stage-num">
            <span *ngIf="stage.estado === 'completado'">✓</span>
            <span *ngIf="stage.estado === 'activo'" class="spinner-sm"></span>
            <span *ngIf="stage.estado === 'pendiente'">{{ stage.id }}</span>
          </div>

          <div class="stage-info">
            <span class="stage-title">{{ stage.nombre }}</span>
            <p class="stage-copy">{{ stage.microcopy }}</p>
          </div>
        </div>
      </div>

      <!-- Live Skeleton Loader Preview -->
      <div class="skeleton-preview-box">
        <div class="skeleton-line skeleton-pulse" style="width: 40%; height: 18px; margin-bottom: 12px;"></div>
        <div class="skeleton-line skeleton-pulse" style="width: 85%; height: 14px; margin-bottom: 8px;"></div>
        <div class="skeleton-line skeleton-pulse" style="width: 70%; height: 14px;"></div>
      </div>
    </div>
  `,
  styles: [`
    .pipeline-progress-wrapper {
      padding: 2rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      margin-bottom: 2rem;
    }

    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
    }

    .title-status {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .pulse-dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: #22D3EE;
      box-shadow: 0 0 10px #22D3EE;
      animation: pulseGlow 1.5s infinite;
    }

    @keyframes pulseGlow {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.4; transform: scale(0.8); }
    }

    .title-status h3 {
      font-size: 1.25rem;
      font-weight: 800;
    }

    .btn-cancel {
      padding: 0.5rem 1rem;
      border-radius: 8px;
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      color: #EF4444;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
    }

    .stepper-container {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 0.85rem;
      margin-bottom: 2rem;
    }

    .stage-card {
      padding: 1rem 0.85rem;
      border-radius: 12px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      transition: all 0.3s;
    }

    .stage-card.activo {
      border-color: #22D3EE;
      background: rgba(34, 211, 238, 0.08);
      box-shadow: 0 0 15px rgba(34, 211, 238, 0.15);
    }

    .stage-card.completado {
      border-color: #10B981;
      background: rgba(16, 185, 129, 0.06);
    }

    .stage-num {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: var(--slate-200);
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.8rem;
    }

    .completado .stage-num {
      background: #10B981;
      color: #FFFFFF;
    }

    .activo .stage-num {
      background: #22D3EE;
      color: #0F172A;
    }

    .stage-title {
      font-size: 0.82rem;
      font-weight: 700;
      display: block;
      color: var(--text-primary);
    }

    .stage-copy {
      font-size: 0.72rem;
      color: var(--text-muted);
      line-height: 1.3;
    }

    .skeleton-preview-box {
      background: var(--bg-app);
      padding: 1.5rem;
      border-radius: 12px;
      border: 1px dashed var(--border-subtle);
    }

    .spinner-sm {
      width: 12px;
      height: 12px;
      border: 2px solid #0F172A;
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `]
})
export class PipelineProgressComponent implements OnInit, OnDestroy {
  @Output() cancelPipeline = new EventEmitter<void>();
  @Output() pipelineFinished = new EventEmitter<void>();

  private intervalId: any;

  stages = signal<PipelineStage[]>([
    { id: 1, nombre: '1. Ingesta', microcopy: 'Extrayendo PDF/MD/TXT localmente', estado: 'activo' },
    { id: 2, nombre: '2. Chunking', microcopy: 'División en fragmentos semánticos', estado: 'pendiente' },
    { id: 3, nombre: '3. Embeddings', microcopy: 'Vectorización con Nomic/BERT', estado: 'pendiente' },
    { id: 4, nombre: '4. RAG Search', microcopy: 'Búsqueda vectorial & BM25', estado: 'pendiente' },
    { id: 5, nombre: '5. Redactor IA', microcopy: 'Adaptación pedagógica orquestada', estado: 'pendiente' },
    { id: 6, nombre: '6. Revisor Crítico', microcopy: 'Evaluación de anclaje y calidad', estado: 'pendiente' },
    { id: 7, nombre: '7. Guardado OCI', microcopy: 'Persistencia en Object Storage', estado: 'pendiente' }
  ]);

  ngOnInit(): void {
    let currentIdx = 0;
    this.intervalId = setInterval(() => {
      if (currentIdx < 7) {
        this.stages.update(list => {
          const next = [...list];
          if (currentIdx > 0) next[currentIdx - 1].estado = 'completado';
          next[currentIdx].estado = 'activo';
          return next;
        });
        currentIdx++;
      } else {
        this.stages.update(list => {
          const next = [...list];
          next[6].estado = 'completado';
          return next;
        });
        clearInterval(this.intervalId);
        this.pipelineFinished.emit();
      }
    }, 400);
  }

  ngOnDestroy(): void {
    if (this.intervalId) clearInterval(this.intervalId);
  }

  onCancel(): void {
    if (this.intervalId) clearInterval(this.intervalId);
    this.cancelPipeline.emit();
  }
}
