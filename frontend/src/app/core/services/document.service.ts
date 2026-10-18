import { Injectable, signal, computed, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AppDocument, DocumentType } from '../models/document.model';
import { NUEVAMENTE_API, NuevaMenteApi, DocumentRecord } from '../api/nuevamente-api';
import { PipelineStateService } from './pipeline-state.service';

/**
 * DocumentService
 *
 * Purpose:
 *     Read model for the documents the real RAG pipeline has indexed. The
 *     backend `documents` table is the single source of truth: this service
 *     loads it through the API and maps every record to an `AppDocument` for
 *     the documents page and the workspace picker.
 *
 * Input:
 *     The authenticated user id (read from sessionStorage) to scope the list.
 *
 * Output:
 *     Reactive signals with the indexed documents plus helpers to upload a
 *     file through the real ingest pipeline and to hand a document over to
 *     the workspace.
 */
@Injectable({
  providedIn: 'root'
})
export class DocumentService {
  private api = inject<NuevaMenteApi>(NUEVAMENTE_API);
  private pipeline = inject(PipelineStateService);

  private documentsSignal = signal<AppDocument[]>([]);
  readonly selectedWorkspaceDocument = signal<AppDocument | null>(null);
  readonly isLoading = signal<boolean>(false);

  // Computed signals
  readonly activeDocuments = computed(() => this.documentsSignal());

  readonly totalActiveCount = computed(() => this.documentsSignal().length);

  readonly totalIndexedFragments = computed(() =>
    this.documentsSignal().reduce((acc, doc) => acc + (doc.children || 0), 0)
  );

  constructor() {
    // A user must be signed in before the backend scopes the list to them.
    if (this.currentUserId()) {
      void this.refresh();
    }
  }

  /** Reloads the document list from the backend `documents` table. */
  async refresh(userId: string | null = this.currentUserId()): Promise<void> {
    this.isLoading.set(true);
    try {
      const records = await firstValueFrom(this.api.listDocuments(userId));
      this.documentsSignal.set(records.map(record => this.toAppDocument(record)));
    } catch (e) {
      console.warn('[DocumentService] No se pudieron cargar los documentos del backend:', e);
    } finally {
      this.isLoading.set(false);
    }
  }

  /**
   * Uploads a file through the real ingestion pipeline (storage + embeddings +
   * index) and refreshes the list once it is ready. The run is routed through
   * PipelineStateService so the global banner shows the progress and a second
   * upload is refused while one is already running.
   */
  async uploadDocument(file: File): Promise<AppDocument | null> {
    const title = file.name.replace(/\.[^.]+$/, '');
    const record = await this.pipeline.ingestOnly({ file, title, userId: this.currentUserId() });
    await this.refresh();
    return this.documentsSignal().find(doc => doc.id === record.document_id)
      ?? this.toAppDocument(record);
  }

  getDocumentById(id: string): AppDocument | undefined {
    return this.documentsSignal().find(doc => doc.id === id);
  }

  /** Sets a document for Workspace consumption. */
  selectForWorkspace(document: AppDocument): void {
    this.selectedWorkspaceDocument.set(document);
  }

  /** Clears the selection for the Workspace. */
  clearWorkspaceSelection(): void {
    this.selectedWorkspaceDocument.set(null);
  }

  private currentUserId(): string | null {
    try {
      const raw = sessionStorage.getItem('nuevamente_user');
      if (!raw) return null;
      return JSON.parse(raw)?.id ?? null;
    } catch {
      return null;
    }
  }

  /** Maps a backend document record to the view model used by the UI. */
  private toAppDocument(record: DocumentRecord): AppDocument {
    const name = record.source_filename || record.title || 'Documento';
    return {
      id: record.document_id,
      name,
      size: 0,
      type: this.detectType(name),
      uploadDate: record.created_at || new Date().toISOString(),
      status: 'active',
      backendStatus: record.status,
      indexed: record.status === 'ready',
      parents: record.total_parents,
      children: record.total_children,
      storageBackend: record.storage_backend,
      tags: []
    };
  }

  private detectType(name: string): DocumentType {
    const ext = name.split('.').pop()?.toLowerCase();
    if (ext === 'pdf') return 'pdf';
    if (ext === 'md' || ext === 'markdown') return 'md';
    return 'txt';
  }
}
