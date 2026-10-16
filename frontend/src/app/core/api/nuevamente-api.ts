import { InjectionToken } from '@angular/core';
import { Observable } from 'rxjs';
import { AdaptationRequest, AdaptationResponse } from '../models/adaptation.model';
import { RecentProject } from '../services/state.service';

/** One progress frame emitted while a document is being ingested (SSE). */
export interface DocumentIngestEvent {
  stage: string;
  message?: string;
  document_id?: string;
  status?: string;
  title?: string;
  total_parents?: number;
  total_children?: number;
  storage_backend?: string;
  current?: number;
  total?: number;
}

/** Metadata record of an indexed document (mirrors the backend `documents` row). */
export interface DocumentRecord {
  document_id: string;
  user_id?: string | null;
  title: string;
  source_filename?: string;
  object_key?: string;
  status: string;
  total_parents?: number;
  total_children?: number;
  storage_backend?: string;
  created_at?: string;
  updated_at?: string;
}

/** Input for the ingestion step: either an uploaded file or pasted text. */
export interface DocumentIngestInput {
  file?: File | null;
  text?: string | null;
  title?: string | null;
  userId?: string | null;
  useAiVision?: boolean;
}

export interface NuevaMenteApi {
  /**
   * Step 1 of the real pipeline: ingest a document (upload or pasted text)
   * into storage and the vector index. Reports live progress through
   * `onEvent` and resolves with the indexed document record.
   */
  ingestDocument(input: DocumentIngestInput, onEvent?: (event: DocumentIngestEvent) => void): Observable<DocumentRecord>;
  /**
   * Step 2 of the real pipeline: generate educational content from an
   * already-indexed document (retrieval + multi-agent generation).
   */
  adaptDocument(documentId: string, request: AdaptationRequest, userId?: string | null): Observable<AdaptationResponse>;
  /** Lists indexed documents, optionally scoped to one owner. */
  listDocuments(userId?: string | null): Observable<DocumentRecord[]>;

  adaptContent(request: AdaptationRequest): Observable<AdaptationResponse>;
  parsePdf(file: File, useLlm?: boolean): Observable<{ status: string; engine?: string; texto_extraido: string; total_paginas?: number }>;
  parseDocument?(file: File, useLlm?: boolean): Observable<{ status: string; engine?: string; texto_extraido: string; total_paginas?: number }>;
  checkHealth(): Observable<{ status: string; service: string }>;
  login(email: string, password: string): Observable<{ token: string; user: { name: string; email: string } }>;
  exportAnkiDeck(deckName: string, flashcards: any[]): Observable<Blob>;
  
  // Trash & Library management
  listLibrary(): Observable<RecentProject[]>;
  moveToTrash(id: string): Observable<void>;
  listTrash(): Observable<RecentProject[]>;
  restore(id: string): Observable<void>;
  deletePermanently(id: string): Observable<void>;
  emptyTrash(): Observable<void>;
  // OCI Storage management
  getStorageStatus?(contentId: string): Observable<{ status: string; status_upload: string; bucket: string; objeto_id?: string; error?: string }>;
  retryStorageJob?(contentId: string): Observable<{ status: string; mensaje: string }>;
}

export const NUEVAMENTE_API = new InjectionToken<NuevaMenteApi>('NUEVAMENTE_API');
