import asyncio
from app.services.ingester_service import IngesterService
from app.services.hybrid_rag_service import HybridRAGService
from app.services.embedding_service import EmbeddingService
from app.schemas.adaptation import AdaptationRequest
from app.domain.enums import PerfilDestinatario, FormatoSalida, NichoSector
from app.services.langgraph_orchestrator import LangGraphOrchestrator
from loguru import logger

def main():
    logger.info("Iniciando prueba con Markdown...")
    ingester = IngesterService()
    embedding_service = EmbeddingService()
    hybrid_rag = HybridRAGService(embedding_service=embedding_service)
    orchestrator = LangGraphOrchestrator()

    with open("tests/manual/sample_docs/manual_rag.md", "r", encoding="utf-8") as f:
        md_content = f.read()
    
    logger.info("1. Ingestion y Chunking...")
    doc_data = ingester.parse_and_chunk_document(md_content, "Manual RAG MD")
    
    logger.info(f"Chunks Hijos Creados: {len(doc_data['child_chunks'])}")
    logger.info(f"Chunks Padres Creados: {len(doc_data['parent_chunks'])}")

    logger.info("2. RAG Híbrido: Recuperación...")
    query = "Explícame qué es el RAG y cómo funciona la base de datos vectorial"
    top_passages = hybrid_rag.retrieve_top_passages(
        query=query,
        child_chunks=doc_data["child_chunks"],
        parent_chunks=doc_data["parent_chunks"],
        top_k=3
    )

    context_str = "\n".join([p["content"] for p in top_passages])
    logger.info(f"Contexto Recuperado: {len(context_str)} caracteres.")
    
    req = AdaptationRequest(
        documento_titulo="Manual RAG",
        documento_contenido=context_str,
        perfil_destinatario=PerfilDestinatario.PRINCIPIANTE,
        formato_salida=FormatoSalida.TUTORIAL,
        nicho_sector=NichoSector.GENERAL
    )

    logger.info("3. Generación con LangGraph...")
    adapted = orchestrator.run(req, context_str)
    
    print("\n" + "="*50)
    print("✨ RESULTADO ADAPTADO ✨")
    print("="*50)
    print(adapted.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
