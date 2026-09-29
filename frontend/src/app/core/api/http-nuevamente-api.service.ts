import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, catchError, of } from 'rxjs';
import { NuevaMenteApi } from './nuevamente-api';
import { MockNuevaMenteApiService } from './mock-nuevamente-api.service';
import { AdaptationRequest, AdaptationResponse } from '../models/adaptation.model';

@Injectable({
  providedIn: 'root'
})
export class HttpNuevaMenteApiService implements NuevaMenteApi {
  private baseUrl = 'http://localhost:8000/api/v1';

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
          console.warn('[HttpNuevaMenteApi] Backend request failed or unreachable. Falling back to Mock API:', err);
          return this.mockApi.adaptContent(request);
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
          console.warn('[HttpNuevaMenteApi] Parse PDF failed. Falling back to mock:', err);
          return this.mockApi.parsePdf(file, useLlm);
        })
      );
  }

  checkHealth(): Observable<{ status: string; service: string }> {
    return this.http.get<{ status: string; service: string }>(`${this.baseUrl}/health`)
      .pipe(
        catchError(() => of({ status: 'offline', service: 'FastAPI Backend unreachable (Mock Mode Active)' }))
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
}
