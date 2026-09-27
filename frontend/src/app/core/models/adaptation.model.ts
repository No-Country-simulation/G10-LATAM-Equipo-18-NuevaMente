export interface AdaptationRequest {
  documento_titulo: string;
  documento_contenido: string;
  perfil_destinatario: string; // 'Principiante' | 'Desarrollador' | 'Arquitecto' | 'Ejecutivo'
  formato_salida: string;     // 'Flashcards' | 'Tutorial' | 'Quiz' | 'TLDR'
  nicho_sector: string;       // 'Fintech' | 'Salud' | 'E-commerce' | 'General'
  nivel_detalle: string;
  cantidad_generar?: number;
  tamano_chunk?: number;
  instrucciones_adicionales?: string;
}

export interface FlashcardItem {
  frente: string;
  dorso: string;
  pista_didactica?: string;
}

export interface QuizItem {
  pregunta: string;
  opciones: string[];
  respuesta_correcta: string;
  justificacion_didactica: string;
}

export interface ContenidoAdaptado {
  titulo: string;
  introduccion_contextualizada: string;
  resumen_ejecutivo?: string;
  items?: FlashcardItem[];
  quizzes?: QuizItem[];
  secciones_tutorial?: { encabezado: string; contenido: string }[];
}

export interface Metadatos {
  perfil_aplicado: string;
  formato_generado: string;
  tiempo_estimado_estudio_minutos: number;
  conceptos_clave: string[];
  prerrequisitos?: string[];
}

export interface EvaluacionCalidad {
  anclaje_fuente_score: number;
  claridad_pedagogica: string;
  observaciones: string;
}

export interface AlmacenamientoOCI {
  bucket: string;
  objeto_id: string;
  status_upload: string;
}

export interface AdaptationResponse {
  status: string;
  metadatos: Metadatos;
  contenido_adaptado: ContenidoAdaptado;
  evaluacion_calidad: EvaluacionCalidad;
  almacenamiento_oci: AlmacenamientoOCI;
}
