/**
 * Shared pipeline view-model used by the global PipelineStateService, the
 * Workspace loader and the legacy progress components. Declared in core so
 * services and features can share one definition without feature-to-feature
 * imports.
 */

/** Which phase of the two-step pipeline is currently executing. */
export type PipelineMode = 'ingest' | 'generate';

/** One step of the stepper rendered by the generation loader. */
export interface PipelineStage {
  id: number;
  nombre: string;
  microcopy: string;
  estado: 'pendiente' | 'activo' | 'completado' | 'error';
  duracion_ms?: number;
  /** Backend key of the step (ingest stage or LangGraph node) used to advance it. */
  key?: string;
}

/**
 * Display context of a run (chips shown by the loader). Kept in core so the
 * service and the restorable process view can read it without touching the
 * Workspace form.
 */
export interface PipelineParams {
  titulo?: string;
  perfil?: string;
  formato?: string;
  nicho?: string;
  nivel?: string;
  cantidad?: number;
}
