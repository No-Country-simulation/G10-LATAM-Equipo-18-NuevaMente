export type PerfilDestinatario = 'Principiante' | 'Desarrollador' | 'Lider Tecnico' | 'Ejecutivo' | string;
export type FormatoSalida = 'Flashcards' | 'Quiz' | 'Tutorial' | 'Resumen Ejecutivo' | 'Guion de Clase' | string;
export type NichoSector = 'Fintech' | 'Salud' | 'E-commerce' | 'General' | string;
export type NivelDetalle = 'Didactico' | 'Conciso' | 'Tecnico' | 'Exhaustivo' | string;
export type NivelCantidad = 'Breve' | 'Estandar' | 'Amplio' | 'Exhaustivo' | 'Personalizado' | string;

export interface AdaptationRequest {
  documento_titulo: string;
  documento_contenido: string;
  perfil_destinatario: PerfilDestinatario;
  formato_salida: FormatoSalida;
  nicho_sector: NichoSector;
  nivel_detalle: NivelDetalle;
  nivel_cantidad?: NivelCantidad;
  cantidad_objetivo?: number;
  cantidad_generar?: number;
  tamano_chunk?: number;
  instrucciones_adicionales?: string;
}

export interface RagFuente {
  chunk_id: string;
  extracto: string;
  pagina?: number;
  similitud_score?: number;
}

export interface FlashcardItem {
  frente: string;
  dorso: string;
  pista_didactica?: string;
  fuentes?: RagFuente[];
}

export interface QuizItem {
  pregunta: string;
  opciones: string[];
  respuesta_correcta: string;
  justificacion?: string;
  justificacion_didactica?: string;
  fuentes?: RagFuente[];
}

export interface TutorialItem {
  paso: number;
  titulo: string;
  instruccion: string;
  ejemplo?: string;
  advertencia?: string;
  fuentes?: RagFuente[];
}

export interface ResumenEjecutivoItem {
  punto_clave: string;
  impacto_negocio: string;
  fuentes?: RagFuente[];
}

export interface GuionClaseItem {
  escena: number;
  duracion_seg: number;
  narracion: string;
  apoyo_visual: string;
  fuentes?: RagFuente[];
}

export type ItemAdaptado = FlashcardItem | QuizItem | TutorialItem | ResumenEjecutivoItem | GuionClaseItem | any;

export interface ContenidoAdaptado {
  titulo: string;
  introduccion_contextualizada: string;
  resumen_ejecutivo?: string;
  items: ItemAdaptado[];
  quizzes?: QuizItem[];
  secciones_tutorial?: { encabezado: string; contenido: string }[];
}

export interface Metadatos {
  perfil_aplicado: PerfilDestinatario;
  formato_generado: FormatoSalida;
  nicho_sector?: NichoSector;
  nivel_detalle?: NivelDetalle;
  nivel_cantidad?: NivelCantidad;
  items_solicitados?: number;
  items_generados?: number;
  aviso_cantidad?: string;
  tiempo_estimado_estudio_minutos: number;
  conceptos_clave: string[];
  prerrequisitos?: string[];
}

export interface EvaluacionCalidad {
  anclaje_fuente_score: number;
  claridad_pedagogica: 'Alta' | 'Media' | 'Baja' | string;
  observaciones: string;
}

export interface AlmacenamientoOCI {
  bucket: string;
  objeto_id: string;
  status_upload: 'completado' | 'pendiente' | 'error' | string;
}

export interface AdaptationResponse {
  status: 'exito' | 'error' | string;
  metadatos: Metadatos;
  contenido_adaptado: ContenidoAdaptado;
  evaluacion_calidad: EvaluacionCalidad;
  almacenamiento_oci: AlmacenamientoOCI;
  mensaje_error?: string;
}

export interface ScenarioComparison {
  id: string;
  titulo_escenario: string;
  request: AdaptationRequest;
  response: AdaptationResponse;
  created_at: Date;
}
