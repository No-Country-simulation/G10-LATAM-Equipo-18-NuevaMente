export type NivelCantidad = 'Breve' | 'Estandar' | 'Amplio' | 'Exhaustivo' | 'Personalizado' | string;

export interface QuantityPresetInfo {
  items: number;
  label: string;
  hint: string;
}

export interface FormatQuantityConfig {
  presets: Record<string, QuantityPresetInfo>;
  customRange: { min: number; max: number; default: number };
}

export const CONTENT_QUANTITY_CONFIG: Record<string, FormatQuantityConfig> = {
  Flashcards: {
    presets: {
      Breve: { items: 10, label: 'Breve', hint: '≈ 10 tarjetas de memoria rápidas' },
      Estandar: { items: 20, label: 'Estándar', hint: '≈ 20 tarjetas de repaso activo' },
      Amplio: { items: 40, label: 'Amplio', hint: '≈ 40 tarjetas profundas' },
      Exhaustivo: { items: 80, label: 'Exhaustivo', hint: '≈ 80 tarjetas de cobertura completa' }
    },
    customRange: { min: 5, max: 100, default: 25 }
  },
  Quiz: {
    presets: {
      Breve: { items: 5, label: 'Breve', hint: '≈ 5 preguntas rápidas de autoevaluación' },
      Estandar: { items: 10, label: 'Estándar', hint: '≈ 10 preguntas con justificación' },
      Amplio: { items: 20, label: 'Amplio', hint: '≈ 20 preguntas de evaluación completa' },
      Exhaustivo: { items: 30, label: 'Exhaustivo', hint: '≈ 30 preguntas de examen técnico' }
    },
    customRange: { min: 3, max: 50, default: 15 }
  },
  Tutorial: {
    presets: {
      Breve: { items: 4, label: 'Breve', hint: '≈ 4 pasos clave de orientación' },
      Estandar: { items: 8, label: 'Estándar', hint: '≈ 8 módulos explicativos con código' },
      Amplio: { items: 15, label: 'Amplio', hint: '≈ 15 secciones paso a paso detalladas' },
      Exhaustivo: { items: 25, label: 'Exhaustivo', hint: '≈ 25 módulos de guía exhaustiva' }
    },
    customRange: { min: 3, max: 30, default: 10 }
  },
  'Resumen Ejecutivo': {
    presets: {
      Breve: { items: 3, label: 'Breve', hint: '≈ 3 puntos ejecutivos (TL;DR)' },
      Estandar: { items: 5, label: 'Estándar', hint: '≈ 5 síntesis de impacto de negocio' },
      Amplio: { items: 10, label: 'Amplio', hint: '≈ 10 análisis de métricas y riesgo' },
      Exhaustivo: { items: 15, label: 'Exhaustivo', hint: '≈ 15 puntos de auditoría ejecutiva' }
    },
    customRange: { min: 2, max: 20, default: 6 }
  },
  'Guion de Clase': {
    presets: {
      Breve: { items: 3, label: 'Breve', hint: '≈ 3 escenas de presentación rápidas' },
      Estandar: { items: 5, label: 'Estándar', hint: '≈ 5 escenas cronometradas para clase' },
      Amplio: { items: 8, label: 'Amplio', hint: '≈ 8 módulos didácticos con tiempos' },
      Exhaustivo: { items: 12, label: 'Exhaustivo', hint: '≈ 12 bloques para curso completo' }
    },
    customRange: { min: 2, max: 15, default: 6 }
  }
};

export function getTargetItemCount(formato: string, nivel: string, customVal?: number): number {
  if (nivel === 'Personalizado' && customVal !== undefined) {
    const range = CONTENT_QUANTITY_CONFIG[formato]?.customRange || { min: 1, max: 100, default: 10 };
    return Math.max(range.min, Math.min(range.max, customVal));
  }
  const config = CONTENT_QUANTITY_CONFIG[formato] || CONTENT_QUANTITY_CONFIG['Flashcards'];
  if (config && config.presets[nivel]) {
    return config.presets[nivel].items;
  }
  return 10;
}

export function getQuantityHintText(formato: string, nivel: string, customVal?: number): string {
  if (nivel === 'Personalizado' && customVal !== undefined) {
    return `≈ ${customVal} elementos seleccionados`;
  }
  const config = CONTENT_QUANTITY_CONFIG[formato] || CONTENT_QUANTITY_CONFIG['Flashcards'];
  if (config && config.presets[nivel]) {
    return config.presets[nivel].hint;
  }
  return '≈ 10 elementos';
}
