import json
import logging
import re
from typing import List, Dict, Any, Tuple

try:
    import networkx as nx
except ImportError:
    nx = None

from app.infrastructure.gemini_client import GeminiClient
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger("GraphRAGService")

STOP_WORDS = {
    "Página", "Pagina", "Page", "Pág", "Pag", "Figura", "Figure", "Tabla", "Table", 
    "Sección", "Section", "Abstract", "Introduction", "Autor", "Author", "Et", "Al",
    "Vol", "No", "Pp", "Pages", "Doi", "Http", "Https", "Org", "Pdf", "Text", "Documento"
}

class GraphRAGService:
    def __init__(self):
        self.gemini_client = GeminiClient()

    def build_concept_dag(self, document_text: str) -> Tuple[Any, List[str], List[str]]:
        """
        Construye el Grafo Acíclico Dirigido (DAG) de conceptos y relaciones.
        Utiliza Gemini para extraer entidades y relaciones de manera semántica, 
        convirtiéndolo en un verdadero grafo de conocimiento, filtrando stop words.
        Retorna (Grafo NetworkX/dict, Conceptos Clave por Centralidad, Prerrequisitos).
        """
        prompt = f"""
        Analiza el siguiente texto y extrae un Knowledge Graph. 
        Identifica los conceptos clave y las relaciones entre ellos, enfocándote en dependencias o prerrequisitos.
        Devuelve el resultado ÚNICAMENTE en formato JSON estricto con la siguiente estructura:
        {{
            "concepts": ["Concepto 1", "Concepto 2", ...],
            "relationships": [
                {{"source": "Concepto 1", "target": "Concepto 2", "relation": "prerrequisito_de"}}
            ]
        }}
        Solo incluye un máximo de 10 conceptos más relevantes para ahorrar tokens.
        
        Texto:
        {document_text[:3000]}
        """
        
        key_concepts = ["VCN", "Subredes", "Security Lists", "Internet Gateway"]
        prerequisites = ["VCN", "Subredes"]
        
        try:
            response_text = self.gemini_client.generate_content(
                prompt=prompt,
                system_instruction="Eres un experto en extracción de conocimiento. Devuelve siempre JSON válido.",
                json_output=True
            )
            
            response_text = response_text.strip().removeprefix("```json").removesuffix("```").strip()
            data = json.loads(response_text)
            unique_concepts = [c for c in data.get("concepts", []) if c not in STOP_WORDS]
            relationships = data.get("relationships", [])
            
            if unique_concepts:
                key_concepts = unique_concepts[:4]
                prerequisites = unique_concepts[:2]
        except Exception as e:
            logger.error(f"Error al extraer grafo con Gemini: {e}. Activando Fallback.")
            # Fallback de filtrado semántico
            raw_words = re.findall(r'\b[A-Z][a-zA-Z0-9\-]{2,}\b', document_text or '')
            filtered_concepts = []
            for w in raw_words:
                if w not in STOP_WORDS and not w.isnumeric() and len(w) > 3:
                    if w not in filtered_concepts:
                        filtered_concepts.append(w)
                        
            if len(filtered_concepts) < 2:
                filtered_concepts = ["VCN", "Subredes", "Security Lists", "Internet Gateway"]
                
            unique_concepts = filtered_concepts[:10]
            key_concepts = unique_concepts[:4]
            prerequisites = unique_concepts[:2]
            relationships = [{"source": unique_concepts[i], "target": unique_concepts[i+1], "relation": "prerrequisito_de"} for i in range(len(unique_concepts)-1)]

        if nx is not None:
            G = nx.DiGraph()
            for concept in unique_concepts:
                G.add_node(concept)
                
            for rel in relationships:
                src = rel.get("source")
                tgt = rel.get("target")
                if src and tgt:
                    G.add_edge(src, tgt, relation=rel.get("relation", "relacionado_con"))

            try:
                centrality = nx.betweenness_centrality(G)
                sorted_concepts = sorted(centrality.keys(), key=lambda k: centrality[k], reverse=True)
                if sorted_concepts:
                    key_concepts = sorted_concepts[:4]
            except Exception:
                pass
            return G, key_concepts, prerequisites

        return None, key_concepts, prerequisites
