import { Injectable } from '@angular/core';
import { Observable, of, timer } from 'rxjs';
import { map } from 'rxjs/operators';
import { NuevaMenteApi } from './nuevamente-api';
import {
  AdaptationRequest,
  AdaptationResponse,
  FlashcardItem,
  QuizItem,
  TutorialItem,
  ResumenEjecutivoItem,
  GuionClaseItem,
  RagFuente
} from '../models/adaptation.model';

@Injectable({
  providedIn: 'root'
})
export class MockNuevaMenteApiService implements NuevaMenteApi {

  adaptContent(request: AdaptationRequest): Observable<AdaptationResponse> {
    const rawTitle = request.documento_titulo || 'Documento Técnico';
    const cleanTitle = rawTitle.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
    const formattedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);

    const textContent = request.documento_contenido || '';
    
    // Extract non-empty sentences or paragraphs from user text
    const sentences = textContent
      .split(/[\n.!?]/)
      .map(s => s.trim())
      .filter(s => s.length > 10);

    let responsePayload: AdaptationResponse;

    switch (request.formato_salida) {
      case 'Flashcards':
        responsePayload = this.buildFlashcardsPayload(formattedTitle, sentences, request);
        break;
      case 'Quiz':
        responsePayload = this.buildQuizPayload(formattedTitle, sentences, request);
        break;
      case 'Tutorial':
        responsePayload = this.buildTutorialPayload(formattedTitle, sentences, request);
        break;
      case 'Resumen Ejecutivo':
        responsePayload = this.buildSummaryPayload(formattedTitle, sentences, request);
        break;
      case 'Guion de Clase':
        responsePayload = this.buildScriptPayload(formattedTitle, sentences, request);
        break;
      default:
        responsePayload = this.buildTutorialPayload(formattedTitle, sentences, request);
    }

    return timer(800).pipe(map(() => responsePayload));
  }

  parsePdf(file: File, _useLlm: boolean = false): Observable<{ status: string; engine?: string; texto_extraido: string; total_paginas?: number }> {
    return new Observable(subscriber => {
      const isText = file.name.endsWith('.txt') || file.name.endsWith('.md') || file.name.endsWith('.json') || file.type.startsWith('text/');
      if (isText) {
        const reader = new FileReader();
        reader.onload = (e) => {
          const text = (e.target?.result as string) || '';
          subscriber.next({
            status: 'exito',
            engine: 'Browser FileReader',
            texto_extraido: text,
            total_paginas: 1
          });
          subscriber.complete();
        };
        reader.readAsText(file);
      } else {
        const isMsJava = file.name.toLowerCase().includes('java') || file.name.toLowerCase().includes('spring') || file.name.toLowerCase().includes('ms');
        const extracted = isMsJava ? `Microservicios con Spring Boot 3 y 4. Agenda del Curso: 1. Spring Boot (Framework opinionado, auto-configuración, servidor embebido Tomcat), 2. Arquitectura de Microservicios (Bounded Contexts DDD, APIs REST, Swagger), 3. Persistencia y Testing (Spring Data JPA, SQL vs NoSQL, Testing con Testcontainers), 4. Gateway y Resiliencia (Spring Cloud Gateway, Resilience4j Circuit Breakers), 5. Seguridad y Mensajería (OAuth2, OpenID Connect, JWT, Apache Kafka), 6. Observabilidad y DevOps (Spring Boot Actuator, Micrometer Tracing, Prometheus, Grafana, Docker, Kubernetes).` : `Documento Técnico: ${file.name}\nAnálisis de especificaciones de arquitectura, requerimientos de integración, reglas de negocio y configuración de componentes.`;
        
        subscriber.next({
          status: 'exito',
          engine: 'PyMuPDF Local Parser',
          texto_extraido: extracted,
          total_paginas: 64
        });
        subscriber.complete();
      }
    });
  }

  checkHealth(): Observable<{ status: string; service: string }> {
    return of({ status: 'ok', service: 'MockNuevaMenteApi (Simulado)' });
  }

  login(email: string, _password: string): Observable<{ token: string; user: { name: string; email: string } }> {
    return of({
      token: 'mock-jwt-token-nuevamente-123456',
      user: {
        name: email.split('@')[0] || 'Demo User',
        email: email
      }
    });
  }

  exportAnkiDeck(deckName: string, flashcards: any[]): Observable<Blob> {
    const csvContent = flashcards.map(f => `"${f.frente.replace(/"/g, '""')}","${f.dorso.replace(/"/g, '""')}"`).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    return of(blob);
  }

  // --- DYNAMIC PAYLOAD BUILDERS BASED ON USER DOCUMENT CONTENT ---

  private extractKeyConcepts(title: string, sentences: string[]): string[] {
    const concepts = [title];
    sentences.forEach((s, idx) => {
      if (idx < 5) {
        const words = s.split(/\s+/).filter(w => w.length > 5 && !['donde', 'desde', 'hasta', 'cuando', 'sobre', 'entre'].includes(w.toLowerCase()));
        if (words.length > 0) {
          const concept = words.slice(0, 2).join(' ').replace(/[^a-zA-Z0-9 áéíóúÁÉÍÓÚñÑ]/g, '');
          if (concept && !concepts.includes(concept)) {
            concepts.push(concept);
          }
        }
      }
    });

    if (concepts.length < 3) {
      concepts.push('Arquitectura & Principios', 'Reglas de Negocio', 'Validación');
    }
    return concepts.slice(0, 5);
  }

  private buildFlashcardsPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const count = req.cantidad_generar || 5;
    const concepts = this.extractKeyConcepts(title, sentences);
    const items: FlashcardItem[] = [];

    for (let i = 0; i < count; i++) {
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Premisa fundamental de ${title}.`;
      const concept = concepts[i % concepts.length];
      
      const fuente: RagFuente = {
        chunk_id: `chunk-rag-00${i + 1}`,
        extracto: sentence,
        pagina: Math.floor(i / 2) + 1,
        similitud_score: 0.95 + (i % 4) * 0.01
      };

      items.push({
        frente: `¿Qué establece '${title}' sobre ${concept}?`,
        dorso: sentence,
        pista_didactica: `Enfoque pedagógico orientado al nivel ${req.nivel_detalle} para ${req.perfil_destinatario} en ${req.nicho_sector}.`,
        fuentes: [fuente]
      });
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Flashcards',
        tiempo_estimado_estudio_minutos: Math.max(5, count * 2),
        conceptos_clave: concepts
      },
      contenido_adaptado: {
        titulo: `Tarjetas de Repaso: ${title}`,
        introduccion_contextualizada: `Flashcards dinámicas generadas a partir del contenido de '${title}', adaptadas para el perfil ${req.perfil_destinatario} en el sector ${req.nicho_sector}.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.98,
        claridad_pedagogica: 'Alta',
        observaciones: `Adaptación generada y anclada 100% en los extractos de '${title}'.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `flashcards-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }

  private buildQuizPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const count = req.cantidad_generar || 4;
    const concepts = this.extractKeyConcepts(title, sentences);
    const items: QuizItem[] = [];

    for (let i = 0; i < count; i++) {
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Especificación técnica relevante de ${title}.`;
      const concept = concepts[i % concepts.length];

      const fuente: RagFuente = {
        chunk_id: `chunk-rag-00${i + 1}`,
        extracto: sentence,
        pagina: Math.floor(i / 2) + 1,
        similitud_score: 0.96
      };

      items.push({
        pregunta: `Según el documento '${title}', ¿cuál es la premisa correcta en relación a ${concept}?`,
        opciones: [
          sentence,
          `Omite todas las validaciones especificadas en la arquitectura`,
          `Desactiva la verificación de seguridad en producción`,
          `Sustituye la estructura por un método no estandarizado`
        ],
        respuesta_correcta: sentence,
        justificacion: `Basado directamente en el texto original: "${sentence}"`,
        fuentes: [fuente]
      });
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Quiz',
        tiempo_estimado_estudio_minutos: Math.max(6, count * 2),
        conceptos_clave: concepts
      },
      contenido_adaptado: {
        titulo: `Quiz Evaluativo: ${title}`,
        introduccion_contextualizada: `Evaluación formativa construida sobre la documentación de '${title}', adaptada al nivel ${req.nivel_detalle} de ${req.perfil_destinatario}.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.97,
        claridad_pedagogica: 'Alta',
        observaciones: `Preguntas y opciones generadas directamente del texto cargado.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `quiz-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }

  private buildTutorialPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const count = req.cantidad_generar || 4;
    const concepts = this.extractKeyConcepts(title, sentences);
    const items: TutorialItem[] = [];

    for (let i = 0; i < count; i++) {
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Paso técnico de implementación para ${title}.`;
      const concept = concepts[i % concepts.length];

      const fuente: RagFuente = {
        chunk_id: `chunk-rag-00${i + 1}`,
        extracto: sentence,
        pagina: Math.floor(i / 2) + 1,
        similitud_score: 0.99
      };

      let codeExample = undefined;
      if (sentence.includes('code') || sentence.includes('http') || sentence.includes('cli') || sentence.includes('oci') || sentence.includes('npm') || i === 0) {
        codeExample = `\`\`\`bash\n# Ejecución para ${concept}\nrun-process --spec "${title}" --profile ${req.perfil_destinatario.toLowerCase()}\n\`\`\``;
      }

      items.push({
        paso: i + 1,
        titulo: `${concept}: Fase ${i + 1}`,
        instruccion: `${sentence} Esta etapa asegura la correcta aplicación del requerimiento en el entorno de ${req.nicho_sector}.`,
        ejemplo: codeExample,
        advertencia: i % 2 === 0 ? `Asegúrate de validar la compatibilidad con el nivel ${req.nivel_detalle} antes de proceder.` : undefined,
        fuentes: [fuente]
      });
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Tutorial',
        tiempo_estimado_estudio_minutos: Math.max(10, count * 3),
        conceptos_clave: concepts
      },
      contenido_adaptado: {
        titulo: `Guía Paso a Paso: ${title}`,
        introduccion_contextualizada: `Tutorial didáctico estructurado paso a paso a partir de '${title}', optimizado para ${req.perfil_destinatario} en el sector ${req.nicho_sector}.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.99,
        claridad_pedagogica: 'Alta',
        observaciones: `Pasos instructivos 100% verificados contra la fuente recibida.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `tutorial-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }

  private buildSummaryPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const count = req.cantidad_generar || 3;
    const concepts = this.extractKeyConcepts(title, sentences);
    const items: ResumenEjecutivoItem[] = [];

    for (let i = 0; i < count; i++) {
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Punto clave estratégico de ${title}.`;
      const concept = concepts[i % concepts.length];

      const fuente: RagFuente = {
        chunk_id: `chunk-rag-00${i + 1}`,
        extracto: sentence,
        pagina: Math.floor(i / 2) + 1,
        similitud_score: 0.96
      };

      items.push({
        punto_clave: `${concept}: ${sentence.substring(0, 90)}...`,
        impacto_negocio: `Optimiza los procesos en el sector ${req.nicho_sector}, reduciendo tiempos de aprendizaje para el perfil ${req.perfil_destinatario}.`,
        fuentes: [fuente]
      });
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Resumen Ejecutivo',
        tiempo_estimado_estudio_minutos: Math.max(3, count * 1.5),
        conceptos_clave: concepts
      },
      contenido_adaptado: {
        titulo: `Resumen Ejecutivo (TL;DR): ${title}`,
        introduccion_contextualizada: `Informe estratégico sintetizado para tomadores de decisiones a partir del documento '${title}'.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.96,
        claridad_pedagogica: 'Alta',
        observaciones: `Resumen condensado con enfoque en impacto de negocio.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `summary-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }

  private buildScriptPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const count = req.cantidad_generar || 3;
    const concepts = this.extractKeyConcepts(title, sentences);
    const items: GuionClaseItem[] = [];

    for (let i = 0; i < count; i++) {
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Explicación técnica de ${title}.`;
      const concept = concepts[i % concepts.length];

      const fuente: RagFuente = {
        chunk_id: `chunk-rag-00${i + 1}`,
        extracto: sentence,
        pagina: Math.floor(i / 2) + 1,
        similitud_score: 0.97
      };

      items.push({
        escena: i + 1,
        duracion_seg: 90 + i * 30,
        narracion: `En este segmento sobre '${title}', abordaremos ${concept}. ${sentence}`,
        apoyo_visual: `Esquema gráfico animado mostrando la estructura de ${concept} aplicada a ${req.nicho_sector}.`,
        fuentes: [fuente]
      });
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Guion de Clase',
        tiempo_estimado_estudio_minutos: Math.max(5, count * 2),
        conceptos_clave: concepts
      },
      contenido_adaptado: {
        titulo: `Guion de Clase / Video: ${title}`,
        introduccion_contextualizada: `Guion audiovisual estructurado en escenas cronometradas a partir de la documentación de '${title}'.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.97,
        claridad_pedagogica: 'Alta',
        observaciones: `Guion de clase con tiempos y recursos visuales alineados con el texto.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `script-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }
}
