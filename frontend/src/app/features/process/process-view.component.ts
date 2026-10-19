/**
 * ProcessViewComponent
 *
 * Purpose:
 *     Dedicated, restorable view of the document pipeline. It renders only
 *     from PipelineStateService, so it always shows the current stages and
 *     elapsed time no matter when the user navigates to it (or away and back).
 *
 * Input:
 *     Nothing: the run is owned by PipelineStateService. The route can be
 *     opened from the global banner on any page.
 *
 * Output:
 *     Cancel/retry actions and navigation back to the origin view or to the
 *     Workspace result.
 */
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { PipelineStateService } from '../../core/services/pipeline-state.service';
import { StateService } from '../../core/services/state.service';
import { GenerationLoaderComponent } from '../workspace/generation-loader.component';

@Component({
  selector: 'app-process-view',
  standalone: true,
  imports: [CommonModule, GenerationLoaderComponent],
  template: `
    <div class="process-page">
      <div class="page-header">
        <div>
          <span class="module-badge">⚙️ PROCESO EN EJECUCIÓN</span>
          <h1>{{ headerTitle() }}</h1>
          <p>{{ headerSubtitle() }}</p>
        </div>
      </div>

      <!-- ERROR NOTICE: keeps the failed stepper visible below -->
      <div class="process-error glass-card" *ngIf="pipeline.errorMessage() as err">
        <div class="err-text">
          <strong>⚠️ Error en el proceso</strong>
          <span>{{ err }}</span>
        </div>
        <button type="button" class="btn-secondary" (click)="onRetry()">Volver e intentar de nuevo</button>
      </div>

      <!-- ACTIVE RUN: the shared loader reads straight from the service -->
      <app-generation-loader
        *ngIf="pipeline.running() || pipeline.errorMessage()"
        [params]="pipeline.params()"
        [stages]="pipeline.stages()"
        [activeStage]="pipeline.activeStage()"
        [showDetails]="true"
        (cancel)="onCancel()"
        (retry)="onRetry()"
      ></app-generation-loader>

      <!-- EMPTY STATE: no run has been started in this session -->
      <div class="process-card glass-card" *ngIf="pipeline.stages().length === 0">
        <h2>No hay ningún proceso en curso</h2>
        <p>Cuando inicies una ingesta o una generación, aquí podrás seguir el avance paso a paso aunque cambies de página.</p>
        <button type="button" class="btn-primary" (click)="goToWorkspace()">Ir al Workspace</button>
      </div>

      <!-- FINISHED: a result is waiting in the Workspace -->
      <div class="process-card glass-card is-done" *ngIf="pipeline.response() && !pipeline.running() && !pipeline.errorMessage()">
        <h2>✅ Contenido educativo listo</h2>
        <p>El proceso terminó correctamente. Consulta el resultado generado.</p>
        <button type="button" class="btn-primary" (click)="goToResult()">Ver resultado</button>
      </div>
    </div>
  `,
  styles: [`
    .process-page {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
      padding: 2rem;
      max-width: 1100px;
      margin: 0 auto;
      width: 100%;
    }

    .page-header h1 { margin: 0.35rem 0 0.25rem; font-size: 1.6rem; }
    .page-header p { margin: 0; color: var(--text-secondary); }

    .module-badge {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.06em;
      color: #22D3EE;
    }

    .process-card {
      padding: 2rem;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      align-items: flex-start;
    }
    .process-card h2 { margin: 0; font-size: 1.2rem; }
    .process-card p { margin: 0; color: var(--text-secondary); }
    .process-card.is-done { border-color: rgba(16, 185, 129, 0.4); }

    .process-error {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      padding: 1rem 1.25rem;
      border-color: rgba(239, 68, 68, 0.4);
    }
    .process-error .err-text { display: flex; flex-direction: column; gap: 0.2rem; }
    .process-error strong { color: #EF4444; }
    .process-error span { color: var(--text-secondary); }

    .btn-primary {
      margin-top: 0.5rem;
      padding: 0.65rem 1.25rem;
      border: none;
      border-radius: 10px;
      background: linear-gradient(135deg, #6366F1, #22D3EE);
      color: #0F172A;
      font-weight: 800;
      cursor: pointer;
    }

    .btn-secondary {
      padding: 0.55rem 1rem;
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      background: var(--bg-surface);
      color: var(--text-primary);
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
    }
  `]
})
export class ProcessViewComponent {
  readonly pipeline = inject(PipelineStateService);
  private stateService = inject(StateService);
  private router = inject(Router);

  headerTitle(): string {
    if (this.pipeline.errorMessage()) return 'El proceso se detuvo';
    if (this.pipeline.running()) {
      return this.pipeline.mode() === 'ingest' ? 'Indexando documento' : 'Generando contenido educativo';
    }
    if (this.pipeline.response()) return 'Proceso finalizado';
    return 'Centro de proceso';
  }

  headerSubtitle(): string {
    if (this.pipeline.errorMessage()) return 'Revisa el detalle y vuelve a intentarlo.';
    return 'Puedes cambiar de página: el proceso continúa en segundo plano y aquí se restaura tal cual.';
  }

  onCancel(): void {
    this.pipeline.cancel();
    this.router.navigateByUrl(this.pipeline.originRoute());
  }

  /** A retry needs the original form, so we return the user to the origin view. */
  onRetry(): void {
    this.router.navigateByUrl(this.pipeline.originRoute());
  }

  goToResult(): void {
    this.stateService.setIsViewingActiveResult(false);
    this.router.navigateByUrl('/workspace');
  }

  goToWorkspace(): void {
    this.router.navigateByUrl('/workspace');
  }

  goToResult(): void {
    this.router.navigateByUrl('/workspace');
  }
}
