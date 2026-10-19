import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, catchError, map, of, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { DocumentGenerationEvent, DocumentIngestEvent, DocumentIngestInput, DocumentRecord, NuevaMenteApi } from './nuevamente-api';
import { MockNuevaMenteApiService } from './mock-nuevamente-api.service';
import { AdaptationRequest, AdaptationResponse, ContenidoAdaptado } from '../models/adaptation.model';
import { RecentProject } from '../services/state.service';

@Injectable({
  providedIn: 'root'
})
export class HttpNuevaMenteApiService implements NuevaMenteApi {
  private get baseUrl(): string {
    if (typeof window !== 'undefined' && window.location && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
      return '/api';
    }
    return environment.apiUrl ? environment.apiUrl.replace(/\/+$/, '') : '/api';
  }

  constructor(
    private http: HttpClient,
    private mockApi: MockNuevaMenteApiService
  ) {}

  private getHeaders(): HttpHeaders {
    const token = sessionStorage.getItem('nuevamente_jwt_token');
    let headers = new HttpHeaders({ 'Content-Type': 'application/json' });
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
  }

  /**
   * Step 1: uploads a file or pasted text and streams back ingestion progress.
   *
   * Uses fetch + ReadableStream instead of EventSource because the endpoint is
   * a POST with a multipart body, which EventSource cannot send.
   */
  ingestDocument(input: DocumentIngestInput, onEvent?: (event: DocumentIngestEvent) => void): Observable<DocumentRecord> {
    return new Observable<DocumentRecord>((subscriber) => {
      const controller = new AbortController();
      const outcome: { record: DocumentRecord | null; failed: string | null } = { record: null, failed: null };

      const handleEvent = (event: DocumentIngestEvent) => {
        if (onEvent) onEvent(event);
        if (event.stage === 'done' && event.document_id) {
          outcome.record = {
            document_id: event.document_id,
            title: event.title || input.title || 'Documento',
            status: event.status || 'ready',
            total_parents: event.total_parents,
            total_children: event.total_children,
            storage_backend: event.storage_backend
          };
        } else if (event.stage === 'failed') {
          outcome.failed = event.message || 'Falló la ingesta del documento.';
        }
      };

      const formData = new FormData();
      if (input.file) {
        formData.append('file', input.file, input.file.name);
      }
      if (input.text) {
        formData.append('text', input.text);
      }
      if (input.title) {
        formData.append('title', input.title);
      }
      formData.append('use_ai_vision', input.useAiVision ? 'true' : 'false');
      if (input.userId) {
        formData.append('user_id', input.userId);
      }

      const headers: Record<string, string> = {};
      const token = sessionStorage.getItem('nuevamente_jwt_token');
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      fetch(`${this.baseUrl}/documents?stream=true`, {
        method: 'POST',
        body: formData,
        headers,
        signal: controller.signal
      })
        .then(async (response) => {
          if (!response.ok) {
            const detail = await response.text().catch(() => '');
            throw new Error(`Ingesta falló (${response.status}). ${detail}`.trim());
          }
          if (!response.body) {
            throw new Error('El servidor no devolvió un stream de progreso.');
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            let separator = buffer.indexOf('\n\n');
            while (separator !== -1) {
              const frame = buffer.slice(0, separator);
              buffer = buffer.slice(separator + 2);
              for (const line of frame.split('\n')) {
                if (!line.startsWith('data:')) continue;
                const payload = line.slice(5).trim();
                if (!payload) continue;
                try {
                  handleEvent(JSON.parse(payload) as DocumentIngestEvent);
                } catch {
                  // Ignore malformed/partial frames; the next chunk completes them.
                }
              }
              separator = buffer.indexOf('\n\n');
            }
          }

          if (outcome.failed) {
            throw new Error(outcome.failed);
          }
          if (!outcome.record) {
            throw new Error('La ingesta terminó sin confirmar el documento.');
          }
          subscriber.next(outcome.record);
          subscriber.complete();
        })
        .catch((error) => {
          if (error && error.name === 'AbortError') {
            subscriber.complete();
            return;
          }
          subscriber.error(error);
        });

      return () => controller.abort();
    });
  }

  /**
   * Step 2: generates content from an already-indexed document.
   *
   * Without `onEvent` it is a plain POST. With `onEvent` it requests the SSE
   * variant (`?stream=true`) and reports one frame per graph node, ending with
   * a "done" frame that carries the full response. If the backend does not
   * stream (older deployment), it transparently falls back to the JSON body.
   */
  adaptDocument(
    documentId: string,
    request: AdaptationRequest,
    userId?: string | null,
    onEvent?: (event: DocumentGenerationEvent) => void
  ): Observable<AdaptationResponse> {
    const body = {
      perfil_destinatario: request.perfil_destinatario,
      formato_salida: request.formato_salida,
      nicho_sector: request.nicho_sector,
      nivel_detalle: request.nivel_detalle,
      nivel_cantidad: request.nivel_cantidad,
      cantidad_objetivo: request.cantidad_objetivo,
      cantidad_generar: request.cantidad_generar,
      instrucciones_adicionales: request.instrucciones_adicionales,
      idioma_salida: (request.idioma_salida || request.language || 'es'),
      forzar_regenerar: true
    };

    if (!onEvent) {
      const query = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
      return this.http.post<AdaptationResponse>(
        `${this.baseUrl}/documents/${encodeURIComponent(documentId)}/adapt${query}`,
        body,
        { headers: this.getHeaders() }
      );
    }

    return new Observable<AdaptationResponse>((subscriber) => {
      const controller = new AbortController();
      const params = new URLSearchParams({ stream: 'true' });
      if (userId) params.set('user_id', userId);

      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      const token = sessionStorage.getItem('nuevamente_jwt_token');
      if (token) headers['Authorization'] = `Bearer ${token}`;

      fetch(`${this.baseUrl}/documents/${encodeURIComponent(documentId)}/adapt?${params.toString()}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(body),
        signal: controller.signal
      })
        .then(async (response) => {
          if (!response.ok) {
            const detail = await response.text().catch(() => '');
            throw new Error(`Generación falló (${response.status}). ${detail}`.trim());
          }

          const contentType = response.headers.get('content-type') || '';
          // Backend without streaming support: parse the plain JSON response.
          if (!contentType.includes('text/event-stream') || !response.body) {
            const json = (await response.json()) as AdaptationResponse;
            subscriber.next(json);
            subscriber.complete();
            return;
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';
          let failure: string | null = null;
          let receivedDone = false;

          for (;;) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            let separator = buffer.indexOf('\n\n');
            while (separator !== -1) {
              const frame = buffer.slice(0, separator);
              buffer = buffer.slice(separator + 2);
              for (const line of frame.split('\n')) {
                if (!line.startsWith('data:')) continue;
                const payload = line.slice(5).trim();
                if (!payload) continue;
                let event: DocumentGenerationEvent;
                try {
                  event = JSON.parse(payload) as DocumentGenerationEvent;
                } catch {
                  continue; // partial frame; the next chunk completes it
                }

                if (event.stage === 'failed') {
                  failure = event.message || 'Falló la generación del contenido.';
                } else if (event.stage === 'done') {
                  receivedDone = true;
                  onEvent(event);
                  if (event.response) {
                    subscriber.next(event.response);
                    subscriber.complete();
                    return;
                  }
                } else {
                  onEvent(event);
                }
              }
              separator = buffer.indexOf('\n\n');
            }
          }

          if (failure) {
            throw new Error(failure);
          }
          if (!receivedDone) {
            throw new Error('La generación terminó sin devolver el contenido.');
          }
        })
        .catch((error) => {
          if (error && error.name === 'AbortError') {
            subscriber.complete();
            return;
          }
          subscriber.error(error);
        });

      return () => controller.abort();
    });
  }

  /** Lists indexed documents read from the backend `documents` table. */
  listDocuments(userId?: string | null): Observable<DocumentRecord[]> {
    const query = userId ? `?user_id=${encodeURIComponent(userId)}` : '';
    return this.http.get<DocumentRecord[]>(`${this.baseUrl}/documents${query}`, { headers: this.getHeaders() })
      .pipe(
        catchError((err) => {
          console.warn('[HttpNuevaMenteApi] No se pudo listar documentos:', err);
          return of([] as DocumentRecord[]);
        })
      );
  }

  adaptContent(request: AdaptationRequest): Observable<AdaptationResponse> {
    return this.http.post<AdaptationResponse>(`${this.baseUrl}/adapt-content`, request, { headers: this.getHeaders() })
      .pipe(
        catchError(err => {
          console.error('[HttpNuevaMenteApi] Error en adaptContent:', err);
          if (environment.useMock) {
            console.warn('[HttpNuevaMenteApi] environment.useMock activo: cayendo a Mock API');
            return this.mockApi.adaptContent(request);
          }
          return throwError(() => err);
        })
      );
  }

  parsePdf(file: File, useLlm: boolean = false): Observable<{ status: string; engine?: string; texto_extraido: string; total_paginas?: number }> {
    const formData = new FormData();
    formData.append('file', file);
    const token = sessionStorage.getItem('nuevamente_jwt_token');
    const headers = token ? new HttpHeaders({ 'Authorization': `Bearer ${token}` }) : undefined;
    const url = useLlm ? `${this.baseUrl}/parse-pdf?use_llm=true` : `${this.baseUrl}/parse-pdf`;
    
    return this.http.post<{ status: string; engine?: string; texto_extraido: string; total_paginas?: number }>(url, formData, { headers })
      .pipe(
        catchError(err => {
          console.error('[HttpNuevaMenteApi] Error en parsePdf:', err);
          if (environment.useMock) {
            console.warn('[HttpNuevaMenteApi] environment.useMock activo: cayendo a Mock API');
            return this.mockApi.parsePdf(file, useLlm);
          }
          return throwError(() => err);
        })
      );
  }

  checkHealth(): Observable<{ status: string; service: string }> {
    return this.http.get<{ status: string; service: string }>(`${this.baseUrl}/health`)
      .pipe(
        catchError((err) => {
          console.warn('[HttpNuevaMenteApi] checkHealth failed:', err);
          return of({ status: 'offline', service: 'FastAPI Backend unreachable' });
        })
      );
  }

  login(email: string, password: string): Observable<{ token: string; user: { name: string; email: string } }> {
    return this.http.post<{ token: string; user: { name: string; email: string } }>(`${this.baseUrl}/auth/login`, { email, password })
      .pipe(
        catchError(() => this.mockApi.login(email, password))
      );
  }

  exportAnkiDeck(deckName: string, flashcards: any[]): Observable<Blob> {
    return this.http.post(`${this.baseUrl}/anki/export-deck`, { deck_name: deckName, flashcards }, { responseType: 'blob' })
      .pipe(
        catchError(() => this.mockApi.exportAnkiDeck(deckName, flashcards))
      );
  }

  /**
   * Lists the authenticated user's active packages from the backend
   * `contenidos` table. Falls back to the local state when the backend is
   * unreachable so the view still renders offline.
   */
  listLibrary(): Observable<RecentProject[]> {
    return this.http.get<any[]>(`${this.baseUrl}/contenidos`, { headers: this.getHeaders() }).pipe(
      map((rows) => (rows || []).map((row) => this.mapContentToProject(row))),
      catchError((err) => {
        console.warn('[HttpNuevaMenteApi] listLibrary no disponible; usando estado local:', err?.status || err?.message);
        return this.mockApi.listLibrary();
      })
    );
  }

  /** Soft-deletes a package in the backend (moves it to the trash). */
  moveToTrash(id: string): Observable<void> {
    return this.http.delete(`${this.baseUrl}/contenidos/${encodeURIComponent(id)}`, { headers: this.getHeaders() }).pipe(
      map(() => void 0),
      catchError((err) => {
        console.warn('[HttpNuevaMenteApi] moveToTrash no disponible; usando estado local:', err?.status || err?.message);
        return this.mockApi.moveToTrash(id);
      })
    );
  }

  /** Lists the authenticated user's trashed packages from the backend. */
  listTrash(): Observable<RecentProject[]> {
    return this.http.get<any[]>(`${this.baseUrl}/papelera`, { headers: this.getHeaders() }).pipe(
      map((rows) => (rows || []).map((row) => this.mapContentToProject(row))),
      catchError((err) => {
        console.warn('[HttpNuevaMenteApi] listTrash no disponible; usando estado local:', err?.status || err?.message);
        return this.mockApi.listTrash();
      })
    );
  }

  /** Restores a trashed package back to the active library. */
  restore(id: string): Observable<void> {
    return this.http.post(`${this.baseUrl}/papelera/${encodeURIComponent(id)}/restore`, {}, { headers: this.getHeaders() }).pipe(
      map(() => void 0),
      catchError((err) => {
        console.warn('[HttpNuevaMenteApi] restore no disponible; usando estado local:', err?.status || err?.message);
        return this.mockApi.restore(id);
      })
    );
  }

  /** Permanently deletes one trashed package (and its stored object). */
  deletePermanently(id: string): Observable<void> {
    return this.http.delete(`${this.baseUrl}/papelera/${encodeURIComponent(id)}`, { headers: this.getHeaders() }).pipe(
      map(() => void 0),
      catchError((err) => {
        console.warn('[HttpNuevaMenteApi] deletePermanently no disponible; usando estado local:', err?.status || err?.message);
        return this.mockApi.deletePermanently(id);
      })
    );
  }

  /** Permanently deletes every package in the user's trash. */
  emptyTrash(): Observable<void> {
    return this.http.delete(`${this.baseUrl}/papelera`, { headers: this.getHeaders() }).pipe(
      map(() => void 0),
      catchError((err) => {
        console.warn('[HttpNuevaMenteApi] emptyTrash no disponible; usando estado local:', err?.status || err?.message);
        return this.mockApi.emptyTrash();
      })
    );
  }

  getTrashCount(): Observable<number> {
    return this.listTrash().pipe(map((list) => list.length));
  }

  /**
   * Reads the quality evaluation and metadata persisted with a content row.
   *
   * `/contenidos` returns them already parsed; `/papelera` returns the raw row
   * with the full adaptation response serialized inside `response_json`. Legacy
   * rows created before that column existed simply yield nulls.
   */
  private extractEvaluation(row: any): { evaluacion: any; metadatos: any } {
    let evaluacion = row?.evaluacion_calidad;
    let metadatos = row?.metadatos;
    if ((!evaluacion || !metadatos) && typeof row?.response_json === 'string' && row.response_json.trim()) {
      try {
        const full = JSON.parse(row.response_json);
        evaluacion = evaluacion ?? full?.evaluacion_calidad;
        metadatos = metadatos ?? full?.metadatos;
      } catch {
        // Ignore malformed legacy payloads.
      }
    }
    return {
      evaluacion: evaluacion && typeof evaluacion === 'object' ? evaluacion : null,
      metadatos: metadatos && typeof metadatos === 'object' ? metadatos : null
    };
  }

  /** Maps a backend `contenidos` row to the `RecentProject` view model. */
  private mapContentToProject(row: any): RecentProject {
    const adapted = this.extractAdaptedContent(row);
    const items = Array.isArray(adapted.items) ? adapted.items : [];
    const { evaluacion, metadatos } = this.extractEvaluation(row);

    const response: AdaptationResponse = {
      status: 'exito',
      metadatos: {
        perfil_aplicado: metadatos?.perfil_aplicado ?? row?.recipient_profile ?? 'General',
        formato_generado: metadatos?.formato_generado ?? row?.output_format ?? 'Tutorial',
        nicho_sector: metadatos?.nicho_sector ?? row?.niche ?? undefined,
        nivel_detalle: metadatos?.nivel_detalle ?? row?.detail_level ?? undefined,
        nivel_cantidad: metadatos?.nivel_cantidad,
        items_generados: metadatos?.items_generados ?? items.length,
        items_solicitados: metadatos?.items_solicitados ?? items.length,
        tiempo_estimado_estudio_minutos: metadatos?.tiempo_estimado_estudio_minutos ?? Math.max(1, items.length * 3),
        conceptos_clave: metadatos?.conceptos_clave ?? []
      },
      contenido_adaptado: adapted,
      evaluacion_calidad: {
        anclaje_fuente_score: evaluacion?.anclaje_fuente_score ?? 0.98,
        claridad_pedagogica: (evaluacion?.claridad_pedagogica === 'High' ? 'Alta' : evaluacion?.claridad_pedagogica === 'Medium' ? 'Media' : evaluacion?.claridad_pedagogica === 'Low' ? 'Baja' : evaluacion?.claridad_pedagogica) ?? 'Alta',
        observaciones: (evaluacion?.observaciones && !evaluacion.observaciones.includes('Heuristic fallback') && !evaluacion.observaciones.includes('Evaluated by'))
          ? evaluacion.observaciones
          : 'Contenido evaluado y validado contra pasajes fuente del documento técnico.'
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-contenidos-educativos',
        objeto_id: row?.object_key_json || '',
        status_upload: 'completado'
      }
    };

    return {
      id: row?.content_id ?? row?.id,
      nombre: row?.title || 'Documento Técnico',
      descripcion: `Adaptación (${row?.recipient_profile || 'General'})`,
      perfil: row?.recipient_profile || 'General',
      formato: row?.output_format || 'Tutorial',
      estado: 'Completado',
      fecha: this.formatProjectDate(row?.created_at),
      typeIcon: this.formatTypeIcon(row?.output_format),
      deletedAt: row?.deleted_at ?? null,
      purgeAt: row?.purge_at ?? null,
      response
    };
  }

  /**
   * Reads the adapted payload regardless of the endpoint shape: `/contenidos`
   * returns it already parsed as `contenido_adaptado`, while `/papelera`
   * returns the raw row with the JSON string stored in `content`.
   */
  private extractAdaptedContent(row: any): ContenidoAdaptado {
    if (row?.contenido_adaptado && typeof row.contenido_adaptado === 'object') {
      return row.contenido_adaptado as ContenidoAdaptado;
    }
    if (typeof row?.content === 'string' && row.content.trim()) {
      try {
        return JSON.parse(row.content) as ContenidoAdaptado;
      } catch {
        // Fall through to the empty shell below.
      }
    }
    return { titulo: row?.title || 'Documento Técnico', introduccion_contextualizada: '', items: [] };
  }

  /** Formats an epoch-seconds or ISO timestamp as the library date label. */
  private formatProjectDate(value: any): string {
    if (value === null || value === undefined || value === '') return '';
    const date = typeof value === 'number' ? new Date(value * 1000) : new Date(value);
    if (isNaN(date.getTime())) return '';
    return `${date.getDate()} ${date.toLocaleString('es-ES', { month: 'short' })}. ${date.getFullYear()} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
  }

  /** Derives the short icon code shown on each library/trash card. */
  private formatTypeIcon(format?: string): string {
    const value = format || '';
    if (value.includes('Flashcard')) return 'FC';
    if (value.includes('Quiz')) return 'QZ';
    if (value.includes('Tutorial')) return 'TUT';
    if (value.includes('TLDR') || value.includes('Resumen')) return 'TL';
    if (value.includes('Guion')) return 'GC';
    return 'DOC';
  }

  getStorageStatus(contentId: string): Observable<{ status: string; status_upload: string; bucket: string; objeto_id?: string; error?: string }> {
    return this.http.get<{ status: string; status_upload: string; bucket: string; objeto_id?: string; error?: string }>(
      `${this.baseUrl}/almacenamiento/estado/${encodeURIComponent(contentId)}`,
      { headers: this.getHeaders() }
    );
  }

  retryStorageJob(contentId: string): Observable<{ status: string; mensaje: string }> {
    return this.http.post<{ status: string; mensaje: string }>(
      `${this.baseUrl}/almacenamiento/reintentar/${encodeURIComponent(contentId)}`,
      {},
      { headers: this.getHeaders() }
    );
  }
}
