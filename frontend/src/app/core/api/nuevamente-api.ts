import { InjectionToken } from '@angular/core';
import { Observable } from 'rxjs';
import { AdaptationRequest, AdaptationResponse } from '../models/adaptation.model';

export interface NuevaMenteApi {
  adaptContent(request: AdaptationRequest): Observable<AdaptationResponse>;
  parsePdf(file: File, useLlm?: boolean): Observable<{ status: string; engine?: string; texto_extraido: string; total_paginas?: number }>;
  checkHealth(): Observable<{ status: string; service: string }>;
  login(email: string, password: string): Observable<{ token: string; user: { name: string; email: string } }>;
  exportAnkiDeck(deckName: string, flashcards: any[]): Observable<Blob>;
}

export const NUEVAMENTE_API = new InjectionToken<NuevaMenteApi>('NUEVAMENTE_API');
