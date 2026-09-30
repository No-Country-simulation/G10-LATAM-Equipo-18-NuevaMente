import { InjectionToken } from '@angular/core';
import { Observable } from 'rxjs';
import { AdaptationRequest, AdaptationResponse } from '../models/adaptation.model';
import { RecentProject } from '../services/state.service';

export interface NuevaMenteApi {
  adaptContent(request: AdaptationRequest): Observable<AdaptationResponse>;
  parsePdf(file: File, useLlm?: boolean): Observable<{ status: string; engine?: string; texto_extraido: string; total_paginas?: number }>;
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
  getTrashCount(): Observable<number>;
}

export const NUEVAMENTE_API = new InjectionToken<NuevaMenteApi>('NUEVAMENTE_API');
