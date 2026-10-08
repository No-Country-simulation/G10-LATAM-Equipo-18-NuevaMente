import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AdaptationRequest, AdaptationResponse } from '../models/adaptation.model';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  private get baseUrl(): string {
    if (typeof window !== 'undefined' && window.location) {
      if (window.location.port === '4200') {
        return 'http://localhost:8000/api/v1';
      }
      return '/api/v1';
    }
    return 'http://localhost:8000/api/v1';
  }

  constructor(private http: HttpClient) {}

  private getHeaders(): HttpHeaders {
    const token = localStorage.getItem('nuevamente_jwt_token');
    if (token) {
      return new HttpHeaders({
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      });
    }
    return new HttpHeaders({
      'Content-Type': 'application/json'
    });
  }

  adaptContent(request: AdaptationRequest): Observable<AdaptationResponse> {
    return this.http.post<AdaptationResponse>(`${this.baseUrl}/adapt-content`, request, { headers: this.getHeaders() });
  }

  parsePdf(file: File, useLlm: boolean = false): Observable<{ status: string; engine?: string; texto_extraido: string; total_paginas?: number }> {
    const formData = new FormData();
    formData.append('file', file);
    const token = localStorage.getItem('nuevamente_jwt_token');
    const headers = token ? new HttpHeaders({ 'Authorization': `Bearer ${token}` }) : undefined;
    const url = useLlm ? `${this.baseUrl}/parse-pdf?use_llm=true` : `${this.baseUrl}/parse-pdf`;
    return this.http.post<{ status: string; engine?: string; texto_extraido: string; total_paginas?: number }>(url, formData, { headers });
  }

  parsePdfLlm(file: File): Observable<{ status: string; engine: string; texto_extraido: string; total_paginas: number; metadatos_ia: any }> {
    const formData = new FormData();
    formData.append('file', file);
    const token = localStorage.getItem('nuevamente_jwt_token');
    const headers = token ? new HttpHeaders({ 'Authorization': `Bearer ${token}` }) : undefined;
    return this.http.post<{ status: string; engine: string; texto_extraido: string; total_paginas: number; metadatos_ia: any }>(`${this.baseUrl}/parse-pdf-llm`, formData, { headers });
  }

  checkHealth(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/health`);
  }

  login(email: string, password: string, name?: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/login`, { email, password, name });
  }

  register(name: string, email: string, password: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/register`, { name, email, password });
  }

  googleAuth(email?: string, name?: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/auth/google`, { email, name });
  }

  getMe(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/auth/me`, { headers: this.getHeaders() });
  }

  exportAnkiDeck(deckName: string, flashcards: any[]): Observable<Blob> {
    return this.http.post(`${this.baseUrl}/anki/export-deck`, {
      deck_name: deckName,
      flashcards: flashcards
    }, {
      responseType: 'blob'
    });
  }

  syncAnkiConnect(deckName: string, flashcards: any[]): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/anki/sync-ankiconnect`, {
      deck_name: deckName,
      flashcards: flashcards
    });
  }

  getAnkiInfo(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/anki/info`);
  }


  generateMockResponse(request: AdaptationRequest): AdaptationResponse {
    const docTitle = request.documento_titulo || 'Documento Técnico';
    const cleanTitle = docTitle.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
    const formattedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);
    const contentText = request.documento_contenido || '';
    
    // Extract key sentences or lines from user text
    const sentences = contentText
      .split(/[.\n]/)
      .map(s => s.trim())
      .filter(s => s.length > 10);

    const isFlashcards = request.formato_salida.includes('Flashcard');
    const isQuiz = request.formato_salida.includes('Quiz');
    const isTldr = request.formato_salida.includes('TLDR') || request.formato_salida.includes('Resumen');

    const count = request.cantidad_generar || 5;

    // Calculate reading time & concepts guarantee
    const wordCount = contentText.split(/\s+/).filter(w => w.length > 0).length;
    const estimatedTime = Math.max(8, Math.ceil(wordCount > 0 ? wordCount / 100 : 12));

    // Dynamic key concepts derived from title and user text
    const derivedConcepts = [
      formattedTitle,
      'Arquitectura & Principios',
      'Patrones de Diseño',
      'Buenas Prácticas',
      'Pruebas & Validación'
    ];

    if (sentences.length > 0) {
      const extraConcept = sentences[0].substring(0, 30).replace(/[^a-zA-Z0-9 áéíóúÁÉÍÓÚñÑ]/g, '');
      if (extraConcept) derivedConcepts.unshift(extraConcept);
    }

    const keyConcepts = Array.from(new Set(derivedConcepts)).slice(0, 5);

    let seccionesTutorial: { encabezado: string; contenido: string }[] | undefined = undefined;
    let items: { frente: string; dorso: string; pista_didactica?: string }[] | undefined = undefined;
    let quizzes: { pregunta: string; opciones: string[]; respuesta_correcta: string; justificacion_didactica: string }[] | undefined = undefined;
    let resumenEjecutivo: string | undefined = undefined;

    if (isFlashcards) {
      items = [];
      for (let i = 1; i <= count; i++) {
        const sentence = sentences[(i - 1) % sentences.length] || `Concepto clave #${i} de ${formattedTitle}.`;
        items.push({
          frente: `¿Cómo se aplica ${derivedConcepts[(i - 1) % derivedConcepts.length]} según ${formattedTitle}?`,
          dorso: `${sentence}`,
          pista_didactica: `Enfoque pedagógico orientado al nivel ${request.perfil_destinatario} en la industria de ${request.nicho_sector}.`
        });
      }
    } else if (isQuiz) {
      quizzes = [];
      for (let i = 1; i <= count; i++) {
        const sentence = sentences[(i - 1) % sentences.length] || `Premisa fundamental #${i} de ${formattedTitle}.`;
        quizzes.push({
          pregunta: `¿Cuál es la implicación principal de ${derivedConcepts[(i - 1) % derivedConcepts.length]} en el contexto de ${request.nicho_sector}?`,
          opciones: [
            `${sentence}`,
            `Desactivar los controles de validación en entornos de producción`,
            `Ignorar los requerimientos de la audiencia ${request.perfil_destinatario}`,
            `Reemplazar la arquitectura por métodos no estructurados`
          ],
          respuesta_correcta: `${sentence}`,
          justificacion_didactica: `Basado en el análisis de ${docTitle}, este aspecto garantiza la efectividad pedagógica.`
        });
      }
    } else if (isTldr) {
      const summaryPoints: string[] = [];
      for (let i = 1; i <= count; i++) {
        const sentence = sentences[(i - 1) % sentences.length] || `Punto de síntesis #${i}.`;
        summaryPoints.push(`${i}. ${derivedConcepts[(i - 1) % derivedConcepts.length]}: ${sentence}`);
      }
      resumenEjecutivo = `RESUMEN EJECUTIVO (TL;DR) DE ${formattedTitle.toUpperCase()} (${count} PUNTOS CLAVE):\n\n` + summaryPoints.join('\n');

      seccionesTutorial = [];
      for (let i = 1; i <= count; i++) {
        const sentence = sentences[(i - 1) % sentences.length] || `Síntesis estratégica #${i}.`;
        seccionesTutorial.push({
          encabezado: `Concepto ${i}: ${derivedConcepts[(i - 1) % derivedConcepts.length]}`,
          contenido: `${sentence} En el contexto de ${request.nicho_sector}, optimiza el proceso de aprendizaje para ${request.perfil_destinatario}.`
        });
      }
    } else {
      // Default: Tutorial / Guía Paso a Paso
      seccionesTutorial = [];
      const userNote = (request.instrucciones_adicionales || '').toLowerCase();
      const wantsDiagrams = ['diagrama', 'grafic', 'gráfic', 'imagen', 'esquema', 'flujo', 'dibujo', 'mapa', 'tabla'].some(kw => userNote.includes(kw));

      for (let i = 1; i <= count; i++) {
        const sentence = sentences[(i - 1) % sentences.length] || `Análisis del componente ${i} de la arquitectura ${formattedTitle}.`;
        
        let extraVisualBlock = '';
        if (wantsDiagrams && i === 1) {
          extraVisualBlock = `\n\n\`\`\`mermaid\ngraph TD\n    A[📥 Ingestión: ${formattedTitle}] --> B[⚙️ Procesamiento: ${derivedConcepts[(i - 1) % derivedConcepts.length]}]\n    B --> C[🎯 Aplicación en ${request.nicho_sector}]\n    C --> D[✅ Verificación para ${request.perfil_destinatario}]\n\`\`\`\n\n| Fase Didáctica | Objetivo | Estado |\n| --- | --- | --- |\n| 1. Diagnóstico | Evaluar ${derivedConcepts[(i - 1) % derivedConcepts.length]} | Completado |\n| 2. Ejecución | Integrar en ${request.nicho_sector} | Validado |\n`;
        }

        seccionesTutorial.push({
          encabezado: `${derivedConcepts[(i - 1) % derivedConcepts.length]}`,
          contenido: `${sentence} Adaptado especialmente al nivel ${request.nivel_detalle} del perfil ${request.perfil_destinatario} en la industria de ${request.nicho_sector}.${extraVisualBlock}`
        });
      }
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: request.perfil_destinatario,
        formato_generado: request.formato_salida,
        tiempo_estimado_estudio_minutos: estimatedTime,
        conceptos_clave: keyConcepts
      },
      contenido_adaptado: {
        titulo: `Guía Adaptada de ${docTitle} para ${request.perfil_destinatario}`,
        introduccion_contextualizada: `Esta versión adaptada transforma el material técnico de '${docTitle}' en un marco práctico orientado al perfil de ${request.perfil_destinatario} en la industria de ${request.nicho_sector}.`,
        resumen_ejecutivo: resumenEjecutivo,
        secciones_tutorial: seccionesTutorial,
        items: items,
        quizzes: quizzes
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.98,
        claridad_pedagogica: 'Alta',
        observaciones: `Adaptación generada y validada contra el documento original '${docTitle}'.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-contenidos-educativos',
        objeto_id: `contenido-${cleanTitle.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }
}
