"""
adaptation.py

Purpose:
    FastAPI router handling educational content adaptation requests.
    Integrates Layout-Aware ingestion, Graph RAG, Hybrid RAG,
    and Gemini agent orchestration.

Input:
    AdaptationRequest payload via HTTP POST.

Output:
    AdaptationResponse with structured educational artifacts and OCI storage metadata.
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.adaptation import AdaptationRequest, AdaptationResponse
from app.services.ingester_service import IngesterService
from app.services.hybrid_rag_service import HybridRAGService
from app.services.graph_rag_service import GraphRAGService
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.embedding_service import EmbeddingService

router = APIRouter()

ingester_service = IngesterService()
embedding_service = EmbeddingService()
hybrid_rag_service = HybridRAGService(embedding_service=embedding_service)
graph_rag_service = GraphRAGService()
agent_orchestrator = AgentOrchestrator()


@router.post("/adapt-content", response_model=AdaptationResponse, status_code=status.HTTP_200_OK)
async def adapt_content(request: AdaptationRequest):
    """
    Main adaptation endpoint: receives technical content and personalization options,
    runs Graph RAG + Hybrid RAG + Gemini Agent Orchestration, and returns
    structured educational package saved to OCI Object Storage Always Free.
    """
    try:
        # 1. Document parsing and AST segmentation with dynamic chunk size
        target_chunk_size = request.chunk_size or 500
        custom_ingester = IngesterService(child_chunk_size=target_chunk_size)
        doc_data = custom_ingester.parse_and_chunk_document(
            content=request.content,
            title=request.title,
        )

        # 2. Graph RAG (Extract Key Concepts & Prerequisites via DAG)
        _, key_concepts, prerequisites = graph_rag_service.build_concept_dag(request.content)

        # 3. Hybrid RAG (BM25 + Dense Embeddings + Cross-Encoder Re-ranker)
        top_passages = hybrid_rag_service.retrieve_top_passages(
            query=f"{request.recipient_profile} {request.output_format} {request.niche}",
            child_chunks=doc_data["child_chunks"],
            parent_chunks=doc_data["parent_chunks"],
        )

        # 4. Agentic Orchestration with Gemini
        response = agent_orchestrator.run_pipeline(
            request=request,
            top_passages=top_passages,
            key_concepts=key_concepts,
            prerequisites=prerequisites,
        )

        return response

    except Exception as error:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en la adaptación de contenido: {str(error)}",
        )
