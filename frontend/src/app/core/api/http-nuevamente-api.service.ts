import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, catchError, of, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { NuevaMenteApi } from './nuevamente-api';
import { MockNuevaMenteApiService } from './mock-nuevamente-api.service';
import { AdaptationRequest, AdaptationResponse } from '../models/adaptation.model';
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
    const token = localStorage.getItem('nuevamente_jwt_token');
    let headers = new HttpHeaders({ 'Content-Type': 'application/json' });
    if (token) {
      headers = headers.set('Authorization', `Bearer ${token}`);
    }
    return headers;
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
    const token = localStorage.getItem('nuevamente_jwt_token');
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

  listLibrary(): Observable<RecentProject[]> {
    return this.mockApi.listLibrary();
  }

  moveToTrash(id: string): Observable<void> {
    return this.mockApi.moveToTrash(id);
  }

  listTrash(): Observable<RecentProject[]> {
    return this.mockApi.listTrash();
  }

  restore(id: string): Observable<void> {
    return this.mockApi.restore(id);
  }

  deletePermanently(id: string): Observable<void> {
    return this.mockApi.deletePermanently(id);
  }

  emptyTrash(): Observable<void> {
    return this.mockApi.emptyTrash();
  }

  getTrashCount(): Observable<number> {
    return this.mockApi.getTrashCount();
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
