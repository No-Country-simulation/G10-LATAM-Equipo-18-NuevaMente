/**
 * PipelineStateService
 *
 * Purpose:
 *     Singleton owner of the document pipeline (ingestion + content
 *     generation). The subscription to the ingest SSE stream and the
 *     generation POST lives here instead of in any component, so navigating
 *     away from the Workspace (or logging out and back in) never cancels a
 *     run in progress.
 *
 * Input:
 *     Ingest inputs and adaptation requests handed over by the Workspace or
 *     the Documents page, plus the SSE progress frames of the ingest call.
 *
 * Output:
 *     Reactive signals consumed by the Workspace loader (running, stages,
 *     activeStage), the global app banner (mode, originRoute, elapsed time,
 *     justFinished) and the duplicate-action guards (guard()), plus the
 *     persisted active adaptation in StateService when generation completes.
 */
import { Injectable, inject, signal, computed, effect } from '@angular/core';
import { Subscription, switchMap } from 'rxjs';
import { Router } from '@angular/router';
import {
  NUEVAMENTE_API,
  NuevaMenteApi,
  DocumentGenerationEvent,
  DocumentIngestInput,
  DocumentIngestEvent,
  DocumentRecord
} from '../api/nuevamente-api';
import { AdaptationRequest, AdaptationResponse } from '../models/adaptation.model';
import { PipelineMode, PipelineStage, PipelineParams } from '../models/pipeline.model';
import { StateService } from './state.service';
import { I18nService } from './i18n.service';

@Injectable({
  providedIn: 'root'
})
export class PipelineStateService {
  private api = inject<NuevaMenteApi>(NUEVAMENTE_API);
  private stateService = inject(StateService);
  private i18n = inject(I18nService);
  private router = inject(Router);

  /** 'ingest' while only indexing, 'generate' once the LLM pipeline runs. */
  readonly mode = signal<PipelineMode | null>(null);
  readonly running = signal<boolean>(false);
  readonly stages = signal<PipelineStage[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly response = signal<AdaptationResponse | null>(null);
  readonly lastRequest = signal<AdaptationRequest | null>(null);
  /** True until the Workspace displays the result of a finished generation. */
  readonly finished = signal<boolean>(false);
  readonly elapsedSeconds = signal<number>(0);
  /** Route of the view that started the run, so the banner can return to it. */
  readonly originRoute = signal<string>('/workspace');
  /** Display context of the current run (chips in the process view). */
  readonly params = signal<PipelineParams | null>(null);

  readonly activeStage = computed<PipelineStage | null>(
    () => this.stages().find(stage => stage.estado === 'activo') || null
  );

  private sub?: Subscription;
  private timerId: ReturnType<typeof setInterval> | null = null;

  constructor() {
    // Single app-wide ticker used by the global banner's elapsed time.
    this.timerId = setInterval(() => {
      if (this.running()) {
        this.elapsedSeconds.update(sec => sec + 1);
      }
    }, 1000);

    // Auto-navigate to workspace when generation finishes.
    effect(() => {
      const resp = this.response();
      const finished = this.finished();
      const running = this.running();
      if (resp && finished && !running) {
        if (this.router.url !== '/workspace') {
          this.router.navigateByUrl('/workspace');
        }
        this.stateService.setIsViewingActiveResult(true);
      }
    });
  }

  /** Blocks a second upload/generation while one is already in progress. */
  guard(): boolean {
    if (this.running()) {
      console.warn('[PipelineState] Acción bloqueada: ya hay un proceso en curso.');
      return false;
    }
    return true;
  }

  /**
   * Full flow: optional ingestion (SSE) followed by content generation.
   * Provide either `ingestInput` (new upload/paste) or `documentId`
   * (already-indexed document).
   */
  runGeneration(opts: {
    ingestInput?: DocumentIngestInput | null;
    documentId?: string;
    request: AdaptationRequest;
    userId?: string | null;
    params?: PipelineParams | null;
  }): void {
    if (!this.guard()) return;

    const usesIngest = !!opts.ingestInput;
    this.begin(usesIngest ? 'ingest' : 'generate', '/workspace', this.buildGenerationStages());
    this.lastRequest.set(opts.request);
    this.params.set(opts.params ?? null);

    if (opts.documentId) {
      // Already indexed: the ingest group is done, generation starts right away.
      this.mode.set('generate');
      this.setStageProgress(4, 'Generando el contenido educativo con IA (puede tardar unos minutos)…');
      this.sub = this.api
        .adaptDocument(opts.documentId, opts.request, opts.userId, event => this.onGenerationEvent(event))
        .subscribe(this.generationObserver());
      return;
    }

    this.sub = this.api
      .ingestDocument(opts.ingestInput!, event => this.onIngestEvent(event))
      .pipe(
        switchMap((record: DocumentRecord) => {
          this.mode.set('generate');
          this.setStageProgress(4, 'Generando el contenido educativo con IA (puede tardar unos minutos)…');
          return this.api.adaptDocument(record.document_id, opts.request, opts.userId, event => this.onGenerationEvent(event));
        })
      )
      .subscribe(this.generationObserver());
  }

  /** Index-only flow (Documents page upload); resolves with the record. */
  async ingestOnly(input: DocumentIngestInput): Promise<DocumentRecord> {
    if (!this.guard()) {
      throw new Error('Ya hay un proceso en curso. Espera a que termine antes de subir otro documento.');
    }
    this.begin('ingest', '/documents', this.buildIngestStages());

    return new Promise<DocumentRecord>((resolve, reject) => {
      this.sub = this.api.ingestDocument(input, event => this.onIngestEvent(event)).subscribe({
        next: (record) => {
          this.finishStages();
          // Release the global lock so the banner and workspace don't stay
          // "in progress" after an index-only upload finishes.
          this.running.set(false);
          this.mode.set(null);
          resolve(record);
        },
        error: (err) => {
          this.failStages(this.errorDetail(err));
          reject(err);
        }
      });
    });
  }

  /** Aborts the in-flight request (fetch/HTTP unsubscribe tears it down). */
  cancel(): void {
    if (this.sub) {
      this.sub.unsubscribe();
      this.sub = undefined;
    }
    this.running.set(false);
    this.mode.set(null);
  }

  /** Clears the "finished" flag once the result has been displayed. */
  consumeFinished(): boolean {
    const wasFinished = this.finished();
    if (wasFinished) {
      this.finished.set(false);
    }
    return wasFinished;
  }

  /** Clears a displayed error (used by the Workspace error alert). */
  clearError(): void {
    this.errorMessage.set(null);
  }

  // --- internals ----------------------------------------------------------

  private begin(mode: PipelineMode, origin: string, stages: PipelineStage[]): void {
    this.mode.set(mode);
    this.originRoute.set(origin);
    this.stages.set(stages);
    this.errorMessage.set(null);
    this.response.set(null);
    this.finished.set(false);
    this.params.set(null);
    this.elapsedSeconds.set(0);
    this.running.set(true);
  }

  private generationObserver() {
    return {
      next: (resp: AdaptationResponse) => {
        this.finishStages();
        this.response.set(resp);
        this.finished.set(true);
        this.running.set(false);
        this.mode.set(null);
        const req = this.lastRequest();
        if (req) {
          this.stateService.addProjectFromResponse(req, resp);
        }
      },
      error: (err: unknown) => {
        console.error('Error en pipeline RAG:', err);
        this.failStages(this.errorDetail(err));
      }
    };
  }

  private errorDetail(err: any): string {
    const detail = err?.error?.detail || err?.message || 'Error de procesamiento en backend';
    return typeof detail === 'string' ? detail : JSON.stringify(detail);
  }

  /** Maps a backend ingestion stage name to its index in the UI stepper. */
  private ingestStageIndex(stage: string): number {
    switch (stage) {
      case 'uploading': return 0;
      case 'ingesting': return 1;
      case 'embedding': return 2;
      case 'indexing': return 3;
      default: return -1;
    }
  }

  /** Mapping from backend generation step keys to stepper indices. */
  private generationStageIndex(stage: string): number {
    switch (stage) {
      case 'retrieval': return 4;
      case 'planner': return 5;
      case 'writer': return 6;
      case 'deduplicator': return 7;
      case 'grounding_verifier': return 8;
      case 'critic': return 9;
      case 'refiner': return 10;
      case 'formatter': return 11;
      default: return -1;
    }
  }

  private onIngestEvent(event: DocumentIngestEvent): void {
    if (event.stage === 'failed') {
      this.failStages(event.message || 'Falló la ingesta del documento.');
      return;
    }
    if (event.stage === 'ready' || event.stage === 'done') {
      const last = this.stages().length - 1;
      const message = this.mode() === 'generate'
        ? 'Documento indexado. Generando contenido…'
        : 'Documento indexado.';
      this.setStageProgress(last, message);
      return;
    }
    const index = this.ingestStageIndex(event.stage);
    if (index >= 0) {
      this.setStageProgress(index, event.message);
    }
  }

  private onGenerationEvent(event: DocumentGenerationEvent): void {
    if (event.stage === 'failed') {
      this.failStages(event.message || 'Falló la generación del contenido.');
      return;
    }
    if (event.stage === 'done') {
      return; // The final response is delivered by the observable's next.
    }
    const index = this.generationStageIndex(event.stage);
    if (index >= 0) {
      const message = event.message || this.defaultGenerationMessage(event.stage);
      this.setStageProgress(index, message);
    }
  }

  private defaultGenerationMessage(stage: string): string {
    switch (stage) {
      case 'retrieval': return this.i18n.t('stage_retrieval_desc');
      case 'planner': return this.i18n.t('stage_planner_desc');
      case 'writer': return this.i18n.t('stage_writer_desc');
      case 'deduplicator': return this.i18n.t('stage_deduplicator_desc');
      case 'grounding_verifier': return this.i18n.t('stage_grounding_desc');
      case 'critic': return this.i18n.t('stage_critic_desc');
      case 'refiner': return this.i18n.t('stage_refiner_desc');
      case 'formatter': return this.i18n.t('stage_formatter_desc');
      default: return '';
    }
  }

  /** Marks every stage before `index` completed and `index` itself active. */
  private setStageProgress(index: number, message?: string): void {
    this.stages.update(list => list.map((stage, i): PipelineStage => {
      if (i < index) return { ...stage, estado: 'completado' };
      if (i === index) return { ...stage, estado: 'activo', microcopy: message || stage.microcopy };
      return { ...stage, estado: 'pendiente' };
    }));
  }

  private finishStages(): void {
    this.stages.update(list => list.map(stage => ({ ...stage, estado: 'completado' as const })));
  }

  private failStages(message: string): void {
    this.stages.update(list => {
      const activeIdx = Math.max(0, list.findIndex(stage => stage.estado === 'activo'));
      return list.map((stage, i): PipelineStage => {
        if (i < activeIdx) return { ...stage, estado: 'completado' };
        if (i === activeIdx) return { ...stage, estado: 'error', microcopy: message };
        return { ...stage, estado: 'pendiente' };
      });
    });
    this.errorMessage.set(message);
    this.running.set(false);
    this.mode.set(null);
  }

  /** Ingestion-only stepper (Documents page upload). */
  private buildIngestStages(): PipelineStage[] {
    const t = (k: string) => this.i18n.t(k);
    return [
      { id: 1, nombre: '1. ' + t('stage_ingest_name'), microcopy: t('stage_ingest_desc'), estado: 'pendiente', key: 'ingesting' },
      { id: 2, nombre: '2. ' + t('stage_chunking_name'), microcopy: t('stage_chunking_desc'), estado: 'pendiente', key: 'chunking' },
      { id: 3, nombre: '3. ' + t('stage_embeddings_name'), microcopy: t('stage_embeddings_desc'), estado: 'pendiente', key: 'embedding' },
      { id: 4, nombre: '4. ' + t('stage_indexing_name'), microcopy: t('stage_indexing_desc'), estado: 'pendiente', key: 'indexing' }
    ];
  }

  /** Ingestion + generation stepper (Workspace pipeline). */
  private buildGenerationStages(): PipelineStage[] {
    const lang = this.i18n.currentLang();
    const t = (k: string) => this.i18n.t(k);
    return [
      { id: 1, nombre: '1. ' + t('stage_ingest_name'), microcopy: t('stage_ingest_desc'), estado: 'pendiente', key: 'ingesting' },
      { id: 2, nombre: '2. ' + t('stage_chunking_name'), microcopy: t('stage_chunking_desc'), estado: 'pendiente', key: 'chunking' },
      { id: 3, nombre: '3. ' + t('stage_embeddings_name'), microcopy: t('stage_embeddings_desc'), estado: 'pendiente', key: 'embedding' },
      { id: 4, nombre: '4. ' + t('stage_indexing_name'), microcopy: t('stage_indexing_desc'), estado: 'pendiente', key: 'indexing' },
      { id: 5, nombre: '5. ' + t('stage_retrieval_name'), microcopy: t('stage_retrieval_desc'), estado: 'pendiente', key: 'retrieval' },
      { id: 6, nombre: '6. ' + t('stage_planner_name'), microcopy: t('stage_planner_desc'), estado: 'pendiente', key: 'planner' },
      { id: 7, nombre: '7. ' + t('stage_writer_name'), microcopy: t('stage_writer_desc'), estado: 'pendiente', key: 'writer' },
      { id: 8, nombre: '8. ' + t('stage_deduplicator_name'), microcopy: t('stage_deduplicator_desc'), estado: 'pendiente', key: 'deduplicator' },
      { id: 9, nombre: '9. ' + t('stage_grounding_name'), microcopy: t('stage_grounding_desc'), estado: 'pendiente', key: 'grounding_verifier' },
      { id: 10, nombre: '10. ' + t('stage_critic_name'), microcopy: t('stage_critic_desc'), estado: 'pendiente', key: 'critic' },
      { id: 11, nombre: '11. ' + t('stage_refiner_name'), microcopy: t('stage_refiner_desc'), estado: 'pendiente', key: 'refiner' },
      { id: 12, nombre: '12. ' + t('stage_formatter_name'), microcopy: t('stage_formatter_desc'), estado: 'pendiente', key: 'formatter' }
    ];
  }
}
