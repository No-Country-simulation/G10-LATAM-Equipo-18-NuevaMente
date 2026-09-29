import { Injectable, signal, computed } from '@angular/core';

export type Language = 'es' | 'en' | 'pt';

interface Dictionary {
  [key: string]: {
    es: string;
    en: string;
    pt: string;
  };
}

@Injectable({
  providedIn: 'root'
})
export class I18nService {
  readonly currentLang = signal<Language>('es');

  private readonly dictionary: Dictionary = {
    brand_tagline: {
      es: 'Convierte documentación técnica en aprendizaje que se entiende.',
      en: 'Turn technical documentation into understandable learning.',
      pt: 'Transforme documentação técnica em aprendizado compreensível.'
    },
    value_prop: {
      es: 'De semanas de trabajo instruccional a minutos, con fidelidad a la fuente.',
      en: 'From weeks of instructional design to minutes, grounded in the source.',
      pt: 'De semanas de trabalho instrucional a minutos, com fidelidade à fonte.'
    },
    btn_generate: {
      es: 'Generar contenido educativo',
      en: 'Generate educational content',
      pt: 'Gerar conteúdo educacional'
    },
    preset_beginner_flashcards: {
      es: 'Demo Principiante · Flashcards',
      en: 'Beginner Demo · Flashcards',
      pt: 'Demo Iniciante · Flashcards'
    },
    preset_leader_summary: {
      es: 'Demo Líder · Resumen Ejecutivo',
      en: 'Leader Demo · Executive Summary',
      pt: 'Demo Líder · Resumo Executivo'
    },
    preset_dev_quiz: {
      es: 'Demo Dev · Quiz Fintech',
      en: 'Dev Demo · Fintech Quiz',
      pt: 'Demo Dev · Quiz Fintech'
    },
    security_badge: {
      es: '🔒 Tus documentos se procesan de forma segura',
      en: '🔒 Your documents are processed securely',
      pt: '🔒 Seus documentos são processados com segurança'
    },
    rag_cited: {
      es: 'RAG con fuentes citadas · 4 perfiles · 5 formatos',
      en: 'RAG with cited sources · 4 profiles · 5 formats',
      pt: 'RAG com fontes citadas · 4 perfis · 5 formatos'
    },
    nav_workspace: { es: 'Workspace', en: 'Workspace', pt: 'Espaço de Trabalho' },
    nav_compare: { es: 'Comparador', en: 'Comparator', pt: 'Comparador' },
    nav_library: { es: 'Biblioteca', en: 'Library', pt: 'Biblioteca' },
    nav_settings: { es: 'Configuración', en: 'Settings', pt: 'Configurações' }
  };

  setLanguage(lang: Language): void {
    this.currentLang.set(lang);
    localStorage.setItem('nuevamente_lang', lang);
  }

  t(key: string): string {
    const entry = this.dictionary[key];
    if (!entry) return key;
    return entry[this.currentLang()] || entry.es;
  }
}
