"""
graph_rag_service.py

Purpose:
    Builds a Directed Acyclic Graph (DAG) of concepts and relationships from
    any technical document dynamically using Google Gemini LLM or dynamic
    heuristic extraction (headings, bold terms, code identifiers, TF-IDF terms).
    Zero hardcoded concept lists.
"""

import json
import logging
import re
from typing import List, Dict, Any, Tuple

try:
    import networkx as nx
except ImportError:
    nx = None

from app.infrastructure.gemini_client import GeminiClient

logger = logging.getLogger("GraphRAGService")

STOP_WORDS = {
    "Página", "Pagina", "Page", "Pág", "Pag", "Figura", "Figure", "Tabla", "Table", 
    "Sección", "Section", "Abstract", "Introduction", "Autor", "Author", "Et", "Al",
    "Vol", "No", "Pp", "Pages", "Doi", "Http", "Https", "Org", "Pdf", "Text", "Documento",
    "Módulo", "Modulo", "Capítulo", "Capitulo", "Ejemplo", "Notas", "Resumen"
}


def _extract_dynamic_fallback_concepts(text: str) -> List[str]:
    """
    Extracción heurística dinámica basada en la estructura del documento:
    1. Títulos Markdown (H1, H2, H3)
    2. Términos en negrita (**concepto**)
    3. Identificadores en código (`concepto`)
    4. Palabras clave en mayúscula/CamelCase no vacías
    """
    concepts = []
    
    # 1. Encabezados Markdown
    headings = re.findall(r'^(?:#{1,4})\s+(.+)$', text or '', re.MULTILINE)
    for h in headings:
        clean_h = re.sub(r'[*_`]', '', h).strip()
        if clean_h and clean_h not in STOP_WORDS and len(clean_h) > 2:
            if clean_h not in concepts:
                concepts.append(clean_h[:50])

    # 2. Términos en negrita
    bolds = re.findall(r'\*\*([^*]+)\*\*', text or '')
    for b in bolds:
        clean_b = b.strip()
        if clean_b and clean_b not in STOP_WORDS and len(clean_b) > 2:
            if clean_b not in concepts:
                concepts.append(clean_b[:50])

    # 3. Términos de código
    code_terms = re.findall(r'`([^`]+)`', text or '')
    for c in code_terms:
        clean_c = c.strip()
        if clean_c and clean_c not in STOP_WORDS and len(clean_c) > 2 and not clean_c.isnumeric():
            if clean_c not in concepts:
                concepts.append(clean_c[:40])

    # 4. Palabras técnicas capitalizadas
    capitalized = re.findall(r'\b[A-Z][a-zA-Z0-9_\-]{2,}\b', text or '')
    for cap in capitalized:
        if cap not in STOP_WORDS and not cap.isnumeric() and len(cap) > 3:
            if cap not in concepts:
                concepts.append(cap)

    return concepts[:10]


class GraphRAGService:
    def __init__(self):
        self.gemini_client = GeminiClient()

    def build_concept_dag(self, document_text: str) -> Tuple[Any, List[str], List[str]]:
        """
        Construye dinámicamente el Grafo Acíclico Dirigido (DAG) de conceptos y relaciones.
        Retorna (Grafo NetworkX/dict, Conceptos Clave por Centralidad, Prerrequisitos).
        """
        prompt = f"""
        Analiza el siguiente texto y extrae un Knowledge Graph. 
        Identifica los conceptos clave verdaderos del texto y las relaciones entre ellos, enfocándote en dependencias o prerrequisitos.
        Devuelve el resultado ÚNICAMENTE en formato JSON estricto con la siguiente estructura:
        {{
            "concepts": ["Concepto 1", "Concepto 2", ...],
            "relationships": [
                {{"source": "Concepto 1", "target": "Concepto 2", "relation": "prerrequisito_de"}}
            ]
        }}
        Solo incluye un máximo de 10 conceptos más relevantes para ahorrar tokens.
        
        Texto:
        {document_text[:3500]}
        """
        
        unique_concepts: List[str] = []
        relationships: List[Dict[str, str]] = []
        
        if self.gemini_client.has_real_key:
            try:
                response_text = self.gemini_client.generate_content(
                    prompt=prompt,
                    system_instruction="Eres un experto en extracción de conocimiento. Devuelve siempre JSON válido.",
                    json_output=True
                )
                
                cleaned_resp = response_text.strip().removeprefix("```json").removesuffix("```").strip()
                data = json.loads(cleaned_resp)
                raw_concepts = data.get("concepts", [])
                unique_concepts = [c for c in raw_concepts if isinstance(c, str) and c.strip() not in STOP_WORDS]
                relationships = data.get("relationships", [])
            except Exception as e:
                logger.warning(f"Error al extraer grafo con Gemini: {e}. Activando extracción heurística dinámica.")
                unique_concepts = []
                
        if not unique_concepts:
            unique_concepts = _extract_dynamic_fallback_concepts(document_text)
            if unique_concepts:
                relationships = [
                    {"source": unique_concepts[i], "target": unique_concepts[i+1], "relation": "prerrequisito_de"}
                    for i in range(len(unique_concepts) - 1)
                ]

        if not unique_concepts:
            logger.warning("WARNING: Grafo construido con 0 conceptos extraídos del documento (degradacion: grafo_vacio).")
            return None, [], []

        logger.info("Grafo construido con %d conceptos extraídos del documento: %s", len(unique_concepts), unique_concepts)

        key_concepts = unique_concepts[:4]
        prerequisites = unique_concepts[:2]

        if nx is not None and unique_concepts:
            G = nx.DiGraph()
            for concept in unique_concepts:
                G.add_node(concept)
                
            for rel in relationships:
                src = rel.get("source")
                tgt = rel.get("target")
                if src and tgt and src in G and tgt in G:
                    G.add_edge(src, tgt, relation=rel.get("relation", "relacionado_con"))

            try:
                centrality = nx.betweenness_centrality(G)
                sorted_concepts = sorted(centrality.keys(), key=lambda k: centrality[k], reverse=True)
                if sorted_concepts:
                    key_concepts = sorted_concepts[:4]
            except Exception as exc:
                logger.warning("Error computing betweenness centrality in GraphRAG: %s", exc)
            return G, key_concepts, prerequisites

        return None, key_concepts, prerequisites
