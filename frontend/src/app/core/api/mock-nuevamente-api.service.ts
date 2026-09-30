import { Injectable, inject } from '@angular/core';
import { Observable, of, timer } from 'rxjs';
import { map } from 'rxjs/operators';
import { NuevaMenteApi } from './nuevamente-api';
import { StateService, RecentProject } from '../services/state.service';
import { getTargetItemCount } from '../config/content-quantity.config';
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
  private stateService = inject(StateService);

  listLibrary(): Observable<RecentProject[]> {
    return of(this.stateService.getLibraryProjects());
  }

  moveToTrash(id: string): Observable<void> {
    this.stateService.moveToTrash(id);
    return of(void 0);
  }

  listTrash(): Observable<RecentProject[]> {
    return of(this.stateService.getTrashProjects());
  }

  restore(id: string): Observable<void> {
    this.stateService.restoreFromTrash(id);
    return of(void 0);
  }

  deletePermanently(id: string): Observable<void> {
    this.stateService.deletePermanently(id);
    return of(void 0);
  }

  emptyTrash(): Observable<void> {
    this.stateService.emptyTrash();
    return of(void 0);
  }

  getTrashCount(): Observable<number> {
    return of(this.stateService.getTrashProjects().length);
  }

  adaptContent(request: AdaptationRequest): Observable<AdaptationResponse> {
    const rawTitle = request.documento_titulo || 'Documento Técnico';
    const cleanTitle = rawTitle.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
    const formattedTitle = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);

    const textContent = request.documento_contenido || '';
    
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

    return timer(600).pipe(map(() => responsePayload));
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

  // --- DYNAMIC PAYLOAD BUILDERS WITH VARIETY FOR HIGH VOLUMES ---

  private resolveRequestedCount(req: AdaptationRequest): number {
    if (req.cantidad_objetivo && req.cantidad_objetivo > 0) {
      return req.cantidad_objetivo;
    }
    if (req.nivel_cantidad) {
      return getTargetItemCount(req.formato_salida, req.nivel_cantidad, req.cantidad_objetivo);
    }
    return req.cantidad_generar || 20;
  }

  private extractKeyConcepts(title: string, sentences: string[]): string[] {
    const concepts = [title];
    sentences.forEach((s, idx) => {
      if (idx < 15) {
        const words = s.split(/\s+/).filter(w => w.length > 5 && !['donde', 'desde', 'hasta', 'cuando', 'sobre', 'entre'].includes(w.toLowerCase()));
        if (words.length > 0) {
          const concept = words.slice(0, 2).join(' ').replace(/[^a-zA-Z0-9 áéíóúÁÉÍÓÚñÑ]/g, '');
          if (concept && !concepts.includes(concept)) {
            concepts.push(concept);
          }
        }
      }
    });

    const fallbackTopics = [
      'Arquitectura de Redes', 'Subredes VCN', 'Security Rules & NSG', 'Route Tables',
      'Internet Gateways', 'NAT Gateways', 'Service Gateways', 'DRG & Peering',
      'Load Balancers OCI', 'IAM Policies & Compartments', 'VPN IPSec', 'FastConnect',
      'Observabilidad & Audit Logs', 'High Availability & Fault Domains', 'PCI-DSS Compliance'
    ];
    
    fallbackTopics.forEach(t => {
      if (!concepts.includes(t)) concepts.push(t);
    });

    return concepts;
  }

  private buildFlashcardsPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const requested = this.resolveRequestedCount(req);
    const concepts = this.extractKeyConcepts(title, sentences);
    
    // Simulate document capacity limit if requested count > 60 and document is short
    const effectiveCount = (requested > 60 && sentences.length < 5) ? 45 : requested;
    const items: FlashcardItem[] = [];

    const verbs = ['analizar', 'configurar', 'optimizar', 'validar', 'implementar', 'desplegar', 'auditar', 'aislar'];
    const topics = concepts;

    for (let i = 0; i < effectiveCount; i++) {
      const topic = topics[i % topics.length];
      const verb = verbs[i % verbs.length];
      const pageNum = Math.floor(i / 5) + 1;
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Especificación técnica #${i + 1} sobre ${topic} en ${title}.`;

      const fuente: RagFuente = {
        chunk_id: `chunk-rag-${(i + 1).toString().padStart(3, '0')}`,
        extracto: sentence,
        pagina: pageNum,
        similitud_score: Number((0.92 + (i % 8) * 0.01).toFixed(2))
      };

      items.push({
        frente: `Tarjeta #${i + 1}: ¿Cómo se debe ${verb} ${topic} en ${title}?`,
        dorso: `En el contexto de ${req.nicho_sector}, la recomendación técnica es: ${sentence} Esto garantiza alineación con el nivel ${req.nivel_detalle}.`,
        pista_didactica: `Concepto clave #${(i % 5) + 1}: Enfócate en el impacto operativo para ${req.perfil_destinatario}.`,
        fuentes: [fuente]
      });
    }

    const aviso = effectiveCount < requested
      ? `Tu documento permitió generar ${effectiveCount} tarjetas verificadas. Con un texto fuente más extenso podrás alcanzar las ${requested} solicitadas.`
      : undefined;

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Flashcards',
        nicho_sector: req.nicho_sector,
        nivel_detalle: req.nivel_detalle,
        nivel_cantidad: req.nivel_cantidad || 'Estandar',
        items_solicitados: requested,
        items_generados: effectiveCount,
        aviso_cantidad: aviso,
        tiempo_estimado_estudio_minutos: Math.max(5, Math.ceil(effectiveCount * 0.5)),
        conceptos_clave: concepts.slice(0, 8)
      },
      contenido_adaptado: {
        titulo: `Tarjetas de Repaso (${effectiveCount} Items): ${title}`,
        introduccion_contextualizada: `Flashcards dinámicas generadas a partir del contenido de '${title}', adaptadas para el perfil ${req.perfil_destinatario} en el sector ${req.nicho_sector}.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.98,
        claridad_pedagogica: 'Alta',
        observaciones: `Adaptación de ${effectiveCount} tarjetas validada y anclada 100% en los extractos de '${title}'.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `flashcards-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }

  private buildQuizPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const requested = this.resolveRequestedCount(req);
    const concepts = this.extractKeyConcepts(title, sentences);
    const items: QuizItem[] = [];

    for (let i = 0; i < requested; i++) {
      const topic = concepts[i % concepts.length];
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Requerimiento de seguridad #${i + 1} para ${topic}.`;

      const fuente: RagFuente = {
        chunk_id: `chunk-rag-${(i + 1).toString().padStart(3, '0')}`,
        extracto: sentence,
        pagina: Math.floor(i / 3) + 1,
        similitud_score: 0.96
      };

      items.push({
        pregunta: `Pregunta ${i + 1}: En relación a ${topic} en ${title}, ¿cuál afirmación es correcta para el perfil de ${req.perfil_destinatario}?`,
        opciones: [
          `Opción A (Correcta): ${sentence}`,
          `Opción B: Desactivar los controles de auditoría en ${req.nicho_sector}`,
          `Opción C: Omitir la segmentación de red y usar valores por defecto`,
          `Opción D: Sustituir la autenticación por un método no validado`
        ],
        respuesta_correcta: `Opción A (Correcta): ${sentence}`,
        justificacion: `Directamente respaldado en el fragmento fuente: "${sentence}".`,
        justificacion_didactica: `Explicación pedagógica para ${req.perfil_destinatario}: ${topic} requiere mantener intactos los criterios de seguridad.`,
        fuentes: [fuente]
      });
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Quiz',
        nicho_sector: req.nicho_sector,
        nivel_detalle: req.nivel_detalle,
        nivel_cantidad: req.nivel_cantidad || 'Estandar',
        items_solicitados: requested,
        items_generados: requested,
        tiempo_estimado_estudio_minutos: Math.max(5, Math.ceil(requested * 1.5)),
        conceptos_clave: concepts.slice(0, 8)
      },
      contenido_adaptado: {
        titulo: `Quiz Evaluativo (${requested} Preguntas): ${title}`,
        introduccion_contextualizada: `Evaluación de ${requested} preguntas sobre '${title}', adaptada al nivel ${req.nivel_detalle} de ${req.perfil_destinatario}.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.97,
        claridad_pedagogica: 'Alta',
        observaciones: `Cuestionario de ${requested} preguntas validado contra la fuente.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `quiz-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }

  private buildTutorialPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const requested = this.resolveRequestedCount(req);
    const concepts = this.extractKeyConcepts(title, sentences);
    const items: TutorialItem[] = [];

    for (let i = 0; i < requested; i++) {
      const topic = concepts[i % concepts.length];
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Paso instructivo #${i + 1} sobre ${topic}.`;

      const fuente: RagFuente = {
        chunk_id: `chunk-rag-${(i + 1).toString().padStart(3, '0')}`,
        extracto: sentence,
        pagina: Math.floor(i / 3) + 1,
        similitud_score: 0.98
      };

      const codeExample = (i % 2 === 0)
        ? `\`\`\`bash\n# Paso ${i + 1}: ${topic}\noci network vcn create --display-name "${topic}" --cidr-block "10.${i}.0.0/16"\n\`\`\``
        : undefined;

      items.push({
        paso: i + 1,
        titulo: `Paso ${i + 1}: ${topic}`,
        instruccion: `${sentence} Configuración ajustada al sector ${req.nicho_sector} para ${req.perfil_destinatario}.`,
        ejemplo: codeExample,
        advertencia: (i % 4 === 0) ? `Verifica que las políticas IAM permitan la acción antes de ejecutar el Paso ${i + 1}.` : undefined,
        fuentes: [fuente]
      });
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Tutorial',
        nicho_sector: req.nicho_sector,
        nivel_detalle: req.nivel_detalle,
        nivel_cantidad: req.nivel_cantidad || 'Estandar',
        items_solicitados: requested,
        items_generados: requested,
        tiempo_estimado_estudio_minutos: Math.max(8, Math.ceil(requested * 2)),
        conceptos_clave: concepts.slice(0, 8)
      },
      contenido_adaptado: {
        titulo: `Guía Paso a Paso (${requested} Módulos): ${title}`,
        introduccion_contextualizada: `Tutorial didáctico de ${requested} pasos elaborado desde '${title}', optimizado para ${req.perfil_destinatario}.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.99,
        claridad_pedagogica: 'Alta',
        observaciones: `Pasos instructivos 100% verificados.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `tutorial-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }

  private buildSummaryPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const requested = this.resolveRequestedCount(req);
    const concepts = this.extractKeyConcepts(title, sentences);
    const items: ResumenEjecutivoItem[] = [];

    for (let i = 0; i < requested; i++) {
      const topic = concepts[i % concepts.length];
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Punto clave #${i + 1} de ${topic}.`;

      const fuente: RagFuente = {
        chunk_id: `chunk-rag-${(i + 1).toString().padStart(3, '0')}`,
        extracto: sentence,
        pagina: Math.floor(i / 2) + 1,
        similitud_score: 0.96
      };

      items.push({
        punto_clave: `${topic}: ${sentence.substring(0, 80)}...`,
        impacto_negocio: `Optimización operativa #${i + 1} en el sector ${req.nicho_sector}, acelerando la toma de decisiones para el perfil ${req.perfil_destinatario}.`,
        fuentes: [fuente]
      });
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Resumen Ejecutivo',
        nicho_sector: req.nicho_sector,
        nivel_detalle: req.nivel_detalle,
        nivel_cantidad: req.nivel_cantidad || 'Estandar',
        items_solicitados: requested,
        items_generados: requested,
        tiempo_estimado_estudio_minutos: Math.max(3, Math.ceil(requested * 1.2)),
        conceptos_clave: concepts.slice(0, 8)
      },
      contenido_adaptado: {
        titulo: `Resumen Ejecutivo (TL;DR - ${requested} Puntos): ${title}`,
        introduccion_contextualizada: `Síntesis ejecutiva de ${requested} puntos estratégicos extraídos de '${title}'.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.96,
        claridad_pedagogica: 'Alta',
        observaciones: `Resumen condensado en ${requested} puntos clave.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `summary-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }

  private buildScriptPayload(title: string, sentences: string[], req: AdaptationRequest): AdaptationResponse {
    const requested = this.resolveRequestedCount(req);
    const concepts = this.extractKeyConcepts(title, sentences);
    const items: GuionClaseItem[] = [];

    for (let i = 0; i < requested; i++) {
      const topic = concepts[i % concepts.length];
      const sentence = sentences[i % Math.max(1, sentences.length)] || `Explicación audiovisual #${i + 1} de ${topic}.`;

      const fuente: RagFuente = {
        chunk_id: `chunk-rag-${(i + 1).toString().padStart(3, '0')}`,
        extracto: sentence,
        pagina: Math.floor(i / 2) + 1,
        similitud_score: 0.97
      };

      items.push({
        escena: i + 1,
        duracion_seg: 60 + i * 15,
        narracion: `Escena ${i + 1}: En este segmento abordaremos ${topic}. ${sentence}`,
        apoyo_visual: `Diapositiva o esquema animado #${i + 1} mostrando ${topic} aplicado al sector ${req.nicho_sector}.`,
        fuentes: [fuente]
      });
    }

    return {
      status: 'exito',
      metadatos: {
        perfil_aplicado: req.perfil_destinatario,
        formato_generado: 'Guion de Clase',
        nicho_sector: req.nicho_sector,
        nivel_detalle: req.nivel_detalle,
        nivel_cantidad: req.nivel_cantidad || 'Estandar',
        items_solicitados: requested,
        items_generados: requested,
        tiempo_estimado_estudio_minutos: Math.max(5, Math.ceil(requested * 1.5)),
        conceptos_clave: concepts.slice(0, 8)
      },
      contenido_adaptado: {
        titulo: `Guion de Clase / Video (${requested} Escenas): ${title}`,
        introduccion_contextualizada: `Guion de ${requested} escenas cronometradas para impartir la clase de '${title}'.`,
        items
      },
      evaluacion_calidad: {
        anclaje_fuente_score: 0.97,
        claridad_pedagogica: 'Alta',
        observaciones: `Guion estructurado en ${requested} escenas.`
      },
      almacenamiento_oci: {
        bucket: 'nuevamente-educativo-oci',
        objeto_id: `script-${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}-${Date.now()}.json`,
        status_upload: 'completado'
      }
    };
  }
}
