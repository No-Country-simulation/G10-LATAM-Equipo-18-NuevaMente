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
    nav_settings: { es: 'Configuración', en: 'Settings', pt: 'Configurações' },

    // Pipeline stages (ingestion)
    stage_ingest_name: { es: 'Ingesta', en: 'Ingestion', pt: 'Ingestão' },
    stage_ingest_desc: { es: 'Lectura y extracción del documento', en: 'Document reading and extraction', pt: 'Leitura e extração do documento' },
    stage_chunking_name: { es: 'Chunking', en: 'Chunking', pt: 'Segmentação' },
    stage_chunking_desc: { es: 'División en fragmentos semánticos', en: 'Split into semantic chunks', pt: 'Divisão em fragmentos semânticos' },
    stage_embeddings_name: { es: 'Embeddings', en: 'Embeddings', pt: 'Embeddings' },
    stage_embeddings_desc: { es: 'Vectorización semántica', en: 'Semantic vectorization', pt: 'Vetorização semântica' },
    stage_indexing_name: { es: 'Indexado', en: 'Indexing', pt: 'Indexação' },
    stage_indexing_desc: { es: 'Guardando el índice de búsqueda', en: 'Saving the search index', pt: 'Salvando o índice de busca' },

    // Pipeline stages (generation)
    stage_retrieval_name: { es: 'Recuperación', en: 'Retrieval', pt: 'Recuperação' },
    stage_retrieval_desc: { es: 'Recuperando los fragmentos más relevantes (RAG)', en: 'Retrieving the most relevant passages (RAG)', pt: 'Recuperando os fragmentos mais relevantes (RAG)' },
    stage_planner_name: { es: 'Planificación', en: 'Planning', pt: 'Planejamento' },
    stage_planner_desc: { es: 'Planificando cobertura y tópicos pedagógicos', en: 'Planning coverage and pedagogical topics', pt: 'Planejando cobertura e tópicos pedagógicos' },
    stage_writer_name: { es: 'Redacción', en: 'Writing', pt: 'Redação' },
    stage_writer_desc: { es: 'Generando el contenido educativo por lotes', en: 'Generating educational content in batches', pt: 'Gerando o conteúdo educacional em lotes' },
    stage_deduplicator_name: { es: 'Depuración', en: 'Deduplication', pt: 'Deduplicação' },
    stage_deduplicator_desc: { es: 'Eliminando ítems duplicados', en: 'Removing duplicate items', pt: 'Removendo itens duplicados' },
    stage_grounding_name: { es: 'Verificación de anclaje', en: 'Grounding check', pt: 'Verificação de ancoragem' },
    stage_grounding_desc: { es: 'Validando citas contra los pasajes fuente', en: 'Validating citations against source passages', pt: 'Validando citações contra os trechos fonte' },
    stage_critic_name: { es: 'Auditoría de calidad', en: 'Quality audit', pt: 'Auditoria de qualidade' },
    stage_critic_desc: { es: 'Evaluando claridad pedagógica y fidelidad', en: 'Assessing pedagogical clarity and fidelity', pt: 'Avaliando clareza pedagógica e fidelidade' },
    stage_refiner_name: { es: 'Refinado', en: 'Refinement', pt: 'Refinamento' },
    stage_refiner_desc: { es: 'Completando ítems faltantes (si aplica)', en: 'Filling missing items (if needed)', pt: 'Completando itens faltantes (se aplicável)' },
    stage_formatter_name: { es: 'Formateo y guardado', en: 'Formatting & storage', pt: 'Formatação e salvamento' },
    stage_formatter_desc: { es: 'Serializando la respuesta y guardando artefactos', en: 'Serializing the response and storing artifacts', pt: 'Serializando a resposta e salvando artefatos' }
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
