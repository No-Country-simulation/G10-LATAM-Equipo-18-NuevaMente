"""
diagnose_adaptation.py

Script de diagnóstico profundo de adaptación contra msJava.pdf
Evalúa las 4 combinaciones especificadas utilizando la tubería real de RAG
y Gemini LLM (sin mocks silenciosos).
"""

import os
import sys
import json
import time
import hashlib
import difflib
from pathlib import Path
from typing import Dict, Any, List

# Inserción de ruta backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from dotenv import load_dotenv
    backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if os.path.exists(backend_env):
        load_dotenv(backend_env)
    else:
        load_dotenv()
except ImportError:
    pass

from app.schemas.adaptation import AdaptationRequest
from app.services.ingester_service import IngesterService
from app.services.hybrid_rag_service import HybridRAGService
from app.services.graph_rag_service import GraphRAGService
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.pdf_parser_service import PdfParserService

PDF_PATH = Path(__file__).parent.parent / "storage_mock" / "nuevamente-documentos-fuente" / "msJava.pdf"

COMBINATIONS = [
    {
        "id": "a",
        "name": "Principiante · Flashcards · Salud · Didáctico · Breve",
        "profile": "Principiante",
        "format": "Flashcards",
        "niche": "Salud",
        "detail": "Didactico",
        "quantity_level": "Breve",
        "target_quantity": 10
    },
    {
        "id": "b",
        "name": "Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo",
        "profile": "Desarrollador",
        "format": "Flashcards",
        "niche": "Fintech",
        "detail": "Tecnico",
        "quantity_level": "Exhaustivo",
        "target_quantity": 80
    },
    {
        "id": "c",
        "name": "Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio",
        "profile": "Líder Técnico",
        "format": "Tutorial",
        "niche": "E-commerce",
        "detail": "Exhaustivo",
        "quantity_level": "Amplio",
        "target_quantity": 15
    },
    {
        "id": "d",
        "name": "Ejecutivo · Resumen · General · Conciso · Estándar",
        "profile": "Ejecutivo",
        "format": "Resumen Ejecutivo",
        "niche": "General",
        "detail": "Conciso",
        "quantity_level": "Estandar",
        "target_quantity": 5
    }
]

def run_diagnostics():
    print("=" * 80)
    print("      DIAGNÓSTICO DE ADAPTACIÓN REAL - MSJAVA.PDF")
    print("=" * 80 + "\n")

    if not PDF_PATH.exists():
        print(f"Error: No se encontró el archivo PDF en {PDF_PATH}")
        sys.exit(1)

    from app.services.embedding_service import EmbeddingService
    embedding_service = EmbeddingService()
    ingester = IngesterService()
    hybrid_rag = HybridRAGService(embedding_service=embedding_service)
    graph_rag = GraphRAGService()
    orchestrator = AgentOrchestrator()
    pdf_parser = PdfParserService()

    # 1. Ingesta y Extracción
    print(">> Ingestionando msJava.pdf con PyMuPDF4LLM...")
    raw_markdown, resumen_ingesta = pdf_parser.parse_pdf_to_markdown(str(PDF_PATH))
    ingested_doc = ingester.process_document(PDF_PATH)
    parent_chunks, child_chunks, *_ = ingester.build_rag_chunks(ingested_doc)

    print(f"Páginas: {resumen_ingesta['paginas']} | Caracteres: {resumen_ingesta['caracteres']} | Caracteres/Pág: {resumen_ingesta['caracteres_por_pagina']}")
    print(f"Parent Chunks: {len(parent_chunks)} | Child Chunks: {len(child_chunks)}\n")

    # 2. GraphRAG
    graph, key_concepts, prerequisites = graph_rag.build_concept_dag(raw_markdown[:4000])

    results = []
    generated_first_items = []

    for comb in COMBINATIONS:
        print(f"--> Procesando Combinación ({comb['id']}): {comb['name']}...")
        
        req = AdaptationRequest(
            documento_titulo="msJava.pdf",
            documento_contenido=raw_markdown,
            perfil_destinatario=comb["profile"],
            formato_salida=comb["format"],
            nicho_sector=comb["niche"],
            nivel_detalle=comb["detail"],
            nivel_cantidad=comb["quantity_level"],
            cantidad_objetivo=comb["target_quantity"]
        )

        top_passages = hybrid_rag.retrieve_top_passages(
            query=f"{comb['profile']} {comb['format']} {comb['niche']}",
            child_chunks=child_chunks,
            parent_chunks=parent_chunks,
            top_k=5
        )

        start_t = time.time()
        response = orchestrator.run_pipeline(
            request=req,
            top_passages=top_passages,
            key_concepts=key_concepts,
            prerequisites=prerequisites
        )
        elapsed = round(time.time() - start_t, 2)

        meta = response.metadata
        first_item = response.adapted_content.items[0] if response.adapted_content.items else {}
        first_item_json = json.dumps(first_item, ensure_ascii=False)
        generated_first_items.append(first_item_json)

        results.append({
            "comb": comb,
            "metadata": meta,
            "elapsed": elapsed,
            "first_item": first_item,
            "first_item_json": first_item_json
        })

    # Imprimir tabla comparativa
    print("\n" + "=" * 80)
    print("                     TABLA COMPARATIVA DE RESULTADOS")
    print("=" * 80 + "\n")

    print("| Comb | Perfil | Formato | Items Solicitados | Items Generados | LLM Modelo | Latencia |")
    print("|---|---|---|---|---|---|---|")
    for r in results:
        c = r["comb"]
        m = r["metadata"]
        print(f"| {c['id'].upper()} | {c['profile']} | {c['format']} | {c['target_quantity']} | {m.generated_items} | {m.llm_model} | {r['elapsed']} s |")

    print("\n" + "=" * 80)
    print("               DIFERENCIACIÓN Y SIMILITUD ENTRE COMBINACIONES")
    print("=" * 80 + "\n")

    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            id1, id2 = results[i]["comb"]["id"].upper(), results[j]["comb"]["id"].upper()
            ratio = difflib.SequenceMatcher(None, results[i]["first_item_json"], results[j]["first_item_json"]).ratio()
            print(f"Similitud de salida entre ({id1}) y ({id2}): {ratio:.2%}")

    print("\nDIAGNÓSTICO FINALIZADO CON ÉXITO.")

if __name__ == "__main__":
    run_diagnostics()
