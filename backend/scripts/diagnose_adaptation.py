"""
diagnose_adaptation.py

Script de diagnóstico profundo y validación de calidad para NuevaMente Backend.
Ejecuta la tubería real de adaptación con msJava.pdf, evalúa combinaciones,
caché por prompt_hash, detecta contenido de relleno, fallbacks silenciosos
y evalúa la diferenciación entre salidas.

Uso:
    python backend/scripts/diagnose_adaptation.py
"""

import os
import sys
import json
import time
import re
import hashlib
import difflib
import unicodedata
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Inserción de ruta raíz del backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import certifi
    os.environ["SSL_CERT_FILE"] = certifi.where()
    os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
except ImportError:
    pass

# Cargar variables de entorno
try:
    from dotenv import load_dotenv
    backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if os.path.exists(backend_env):
        load_dotenv(backend_env)
    else:
        load_dotenv()
except ImportError:
    pass

from app.schemas.adaptation import AdaptationRequest, AdaptationResponse
from app.services.ingester_service import IngesterService
from app.services.hybrid_rag_service import HybridRAGService
from app.services.graph_rag_service import GraphRAGService
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.embedding_service import EmbeddingService
from app.services.pdf_parser_service import PdfParserService

PDF_PATH = Path(__file__).parent.parent / "storage_mock" / "nuevamente-documentos-fuente" / "msJava.pdf"

# Cadenas prohibidas que indican relleno o plantillas fijas
FORBIDDEN_PATTERNS = [
    "Aumenta la eficiencia",
    "Punto Clave #",
    "(Módulo",
    "VCN",
    "Subredes",
    "Security Lists"
]

MAIN_COMBINATIONS = [
    {
        "id": "a",
        "name": "Principiante · Flashcards · Salud · Didáctico · Breve",
        "profile": "Principiante",
        "format": "Flashcards",
        "niche": "Salud",
        "detail": "Didactico",
        "quantity_level": "Breve",
        "target_quantity": None,
        "expected_items": 10
    },
    {
        "id": "b",
        "name": "Desarrollador · Flashcards · Fintech · Técnico · Exhaustivo",
        "profile": "Desarrollador",
        "format": "Flashcards",
        "niche": "Fintech",
        "detail": "Tecnico",
        "quantity_level": "Exhaustivo",
        "target_quantity": None,
        "expected_max_items": 70
    },
    {
        "id": "c",
        "name": "Líder Técnico · Tutorial · E-commerce · Exhaustivo · Amplio",
        "profile": "Líder Técnico",
        "format": "Tutorial",
        "niche": "E-commerce",
        "detail": "Exhaustivo",
        "quantity_level": "Amplio",
        "target_quantity": None,
        "expected_max_items": 12
    },
    {
        "id": "d",
        "name": "Ejecutivo · Resumen · General · Conciso · Estándar",
        "profile": "Ejecutivo",
        "format": "Resumen Ejecutivo",
        "niche": "General",
        "detail": "Conciso",
        "quantity_level": "Estandar",
        "target_quantity": None,
        "expected_max_items": 6
    }
]

EXTRA_COMBINATIONS = [
    {
        "id": "e",
        "name": "Flashcards 25 explícito",
        "profile": "Desarrollador",
        "format": "Flashcards",
        "niche": "Fintech",
        "detail": "Tecnico",
        "quantity_level": "Personalizado",
        "target_quantity": 25
    },
    {
        "id": "f",
        "name": "Quiz 15 explícito",
        "profile": "Líder Técnico",
        "format": "Quiz",
        "niche": "General",
        "detail": "Didactico",
        "quantity_level": "Personalizado",
        "target_quantity": 15
    }
]

INVALID_COMBINATION = {
    "id": "g",
    "name": "Flashcards 500 (Inválido)",
    "profile": "Principiante",
    "format": "Flashcards",
    "niche": "General",
    "detail": "Didactico",
    "quantity_level": "Personalizado",
    "target_quantity": 500
}


def normalize_text_for_search(text: str) -> str:
    """Normaliza texto para búsqueda case-insensitive sin acentos ni ligaduras."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower().strip()


def extract_item_text_only(item: Any) -> str:
    """Extrae únicamente los valores de texto de un ítem, ignorando claves JSON."""
    if isinstance(item, dict):
        texts = []
        for k, v in item.items():
            if k == "fuentes":
                continue
            if isinstance(v, str):
                texts.append(v)
            elif isinstance(v, list):
                texts.extend([str(x) for x in v if isinstance(x, str)])
        return " ".join(texts)
    elif hasattr(item, "__dict__"):
        return extract_item_text_only(item.__dict__)
    return str(item)


def run_adaptation_diagnostics(save_report: bool = True) -> Tuple[bool, List[str], str]:
    """
    Ejecuta el diagnóstico completo de adaptación.
    Retorna (is_passed: bool, failures: List[str], report_md: str).
    """
    print("=" * 80)
    print("      DIAGNÓSTICO PROFUNDO DE ADAPTACIÓN V2 - MSJAVA.PDF")
    print("=" * 80 + "\n")

    failures: List[str] = []

    if not PDF_PATH.exists():
        msg = f"Archivo PDF no encontrado en: {PDF_PATH}"
        print(f"CRITICAL: {msg}")
        return False, [msg], ""

    # Inicializar servicios reales
    pdf_parser = PdfParserService()
    ingester = IngesterService()
    embedding_service = EmbeddingService()
    hybrid_rag = HybridRAGService(embedding_service=embedding_service)
    graph_rag = GraphRAGService()
    orchestrator = AgentOrchestrator()
    orchestrator._response_cache.clear()

    # 1. Ingesta y Extracción de Documento Completo
    print(">> Ingestionando msJava.pdf...")
    try:
        raw_markdown, resumen_ingesta = pdf_parser.parse_pdf_to_markdown(str(PDF_PATH))
        ingested_doc = ingester.process_document(PDF_PATH)
        rag_data = ingester.build_rag_chunks(ingested_doc)
        parent_chunks = rag_data.get("parent_chunks", [])
        child_chunks = rag_data.get("child_chunks", [])
    except Exception as exc:
        msg = f"Fallo al ingestar PDF {PDF_PATH.name}: {exc}"
        print(f"CRITICAL: {msg}")
        return False, [msg], ""

    num_pages = resumen_ingesta.get("paginas", 0)
    total_chars = resumen_ingesta.get("caracteres", 0)
    chars_per_page = resumen_ingesta.get("caracteres_por_pagina", 0)
    print(f"Páginas: {num_pages} | Caracteres: {total_chars} | Caracteres/Pág: {chars_per_page}")
    print(f"Parent Chunks: {len(parent_chunks)} | Child Chunks: {len(child_chunks)}\n")

    # 2. GraphRAG sobre el documento COMPLETO
    print(">> Construyendo Grafo de Conocimiento (GraphRAG) sobre documento completo...")
    graph, key_concepts, prerequisites = graph_rag.build_concept_dag(raw_markdown)
    print(f"Conceptos clave extraídos del grafo ({len(key_concepts)}): {key_concepts}\n")

    # Verificar que cada concepto clave aparezca en el texto del PDF
    norm_pdf_text = normalize_text_for_search(raw_markdown)
    missing_concepts = []
    for concept in key_concepts:
        norm_concept = normalize_text_for_search(concept)
        if norm_concept and norm_concept not in norm_pdf_text:
            missing_concepts.append(concept)
    if missing_concepts:
        print(f"WARNING: Conceptos clave no encontrados exactamente en el texto fuente: {missing_concepts}")

    # 3. Procesar Combinaciones Principales
    results: List[Dict[str, Any]] = []
    all_outputs_text: Dict[str, List[str]] = {}

    for comb in MAIN_COMBINATIONS:
        print(f"--> Procesando Combinación ({comb['id'].upper()}): {comb['name']}...")
        req = AdaptationRequest(
            documento_titulo="msJava.pdf",
            documento_contenido=raw_markdown,
            perfil_destinatario=comb["profile"],
            formato_salida=comb["format"],
            nicho_sector=comb["niche"],
            nivel_detalle=comb["detail"],
            nivel_cantidad=comb["quantity_level"],
            cantidad_objetivo=comb["target_quantity"],
            forzar_regenerar=True
        )

        top_passages = hybrid_rag.retrieve_top_passages(
            query=f"{comb['profile']} {comb['format']} {comb['niche']}",
            child_chunks=child_chunks,
            parent_chunks=parent_chunks,
            top_k=5
        )

        t0 = time.time()
        response = orchestrator.run_pipeline(
            request=req,
            top_passages=top_passages,
            key_concepts=key_concepts,
            prerequisites=prerequisites
        )
        elapsed = round(time.time() - t0, 2)

        meta = response.metadata
        eval_q = response.quality_evaluation
        items = response.adapted_content.items or []

        # Extraer texto de items para detectores y comparación
        items_text = [extract_item_text_only(it) for it in items]
        all_outputs_text[comb["id"]] = items_text

        results.append({
            "comb": comb,
            "response": response,
            "metadata": meta,
            "quality": eval_q,
            "elapsed": elapsed,
            "items": items,
            "items_text": items_text
        })

    # 4. Probar Caché (Llamada repetida con forzar_regenerar=False)
    print("\n>> Probando recuperación desde CACHÉ (forzar_regenerar=False)...")
    comb_a = MAIN_COMBINATIONS[0]
    req_cache = AdaptationRequest(
        documento_titulo="msJava.pdf",
        documento_contenido=raw_markdown,
        perfil_destinatario=comb_a["profile"],
        formato_salida=comb_a["format"],
        nicho_sector=comb_a["niche"],
        nivel_detalle=comb_a["detail"],
        nivel_cantidad=comb_a["quantity_level"],
        cantidad_objetivo=comb_a["target_quantity"],
        forzar_regenerar=False
    )
    t_cache = time.time()
    resp_cache = orchestrator.run_pipeline(
        request=req_cache,
        top_passages=[],
        key_concepts=key_concepts,
        prerequisites=prerequisites
    )
    elapsed_cache = round(time.time() - t_cache, 4)
    origin_cache = getattr(resp_cache.metadata, "origin", getattr(resp_cache.metadata, "origen", "llm"))
    hash_a = results[0]["metadata"].prompt_hash
    hash_cache = resp_cache.metadata.prompt_hash

    print(f"Resultado Caché -> Origen: '{origin_cache}' | Prompt Hash coincidente: {hash_a == hash_cache} ({elapsed_cache}s)\n")
    if origin_cache != "cache":
        failures.append("FALLO: La llamada repetida con forzar_regenerar=False no retornó origen: 'cache'.")

    # 5. Probar Combinaciones Extra
    print(">> Procesando Combinaciones Extra (E y F)...")
    for comb_ex in EXTRA_COMBINATIONS:
        req_ex = AdaptationRequest(
            documento_titulo="msJava.pdf",
            documento_contenido=raw_markdown,
            perfil_destinatario=comb_ex["profile"],
            formato_salida=comb_ex["format"],
            nicho_sector=comb_ex["niche"],
            nivel_detalle=comb_ex["detail"],
            nivel_cantidad=comb_ex["quantity_level"],
            cantidad_objetivo=comb_ex["target_quantity"],
            forzar_regenerar=True
        )
        t0 = time.time()
        resp_ex = orchestrator.run_pipeline(
            request=req_ex,
            top_passages=hybrid_rag.retrieve_top_passages(
                query=f"{comb_ex['profile']} {comb_ex['format']} {comb_ex['niche']}",
                child_chunks=child_chunks,
                parent_chunks=parent_chunks,
                top_k=5
            ),
            key_concepts=key_concepts,
            prerequisites=prerequisites
        )
        elapsed_ex = round(time.time() - t0, 2)
        results.append({
            "comb": comb_ex,
            "response": resp_ex,
            "metadata": resp_ex.metadata,
            "quality": resp_ex.quality_evaluation,
            "elapsed": elapsed_ex,
            "items": resp_ex.adapted_content.items or [],
            "items_text": [extract_item_text_only(it) for it in (resp_ex.adapted_content.items or [])]
        })

    # 6. Probar Caso Inválido (Flashcards 500)
    print(">> Probando caso inválido (Flashcards 500)...")
    try:
        req_invalid = AdaptationRequest(
            documento_titulo="msJava.pdf",
            documento_contenido=raw_markdown,
            perfil_destinatario=INVALID_COMBINATION["profile"],
            formato_salida=INVALID_COMBINATION["format"],
            nicho_sector=INVALID_COMBINATION["niche"],
            nivel_detalle=INVALID_COMBINATION["detail"],
            nivel_cantidad=INVALID_COMBINATION["quantity_level"],
            cantidad_objetivo=INVALID_COMBINATION["target_quantity"]
        )
        failures.append("FALLO: La solicitud con cantidad_objetivo = 500 debió ser rechazada con validación/error 422.")
    except Exception as exc:
        print(f"Caso inválido rechazado correctamente: {exc}\n")

    # 7. EJECUCIÓN DE DETECTORES DE RELLENO Y FALLO
    grounding_scores: List[float] = []

    for res in results[:4]:  # Evaluar las 4 principales
        comb = res["comb"]
        meta = res["metadata"]
        quality = res["quality"]
        items = res["items"]
        items_text = res["items_text"]
        full_text = " ".join(items_text)
        origin = getattr(meta, "origin", getattr(meta, "origen", "llm"))
        fallback_used = getattr(meta, "fallback_used", getattr(meta, "fallback_usado", False))

        # Detector 1: Patrones de relleno o plantillas fijas
        for pat in FORBIDDEN_PATTERNS:
            if pat in full_text:
                failures.append(f"FALLO ({comb['id'].upper()}): Se detectó el patrón prohibido '{pat}' en el contenido generado.")

        # Detector 2: Fallback usado o modo demo
        if fallback_used or origin == "demo":
            failures.append(f"FALLO ({comb['id'].upper()}): Se utilizó fallback silencioso o modo demo (origen='{origin}', fallback_usado={fallback_used}).")

        # Detector 3: Ítems duplicados dentro de la misma salida
        if len(items_text) != len(set(items_text)) and len(items_text) > 0:
            from collections import Counter
            counts = Counter(items_text)
            dupes = [txt[:80] for txt, count in counts.items() if count > 1]
            print(f"DEBUG DUPES ({comb['id'].upper()}): {dupes}")
            failures.append(f"FALLO ({comb['id'].upper()}): Se detectaron ítems duplicados dentro de la misma generación.")

        # Detector 4: Ítems sin fuentes
        for idx_it, it in enumerate(items):
            fuentes = it.get("fuentes") if isinstance(it, dict) else getattr(it, "fuentes", None)
            if not fuentes:
                failures.append(f"FALLO ({comb['id'].upper()}): El ítem #{idx_it+1} carece de la lista 'fuentes'.")

        # Guardar score de anclaje
        score = getattr(quality, "source_grounding_score", getattr(quality, "anclaje_fuente_score", None))
        if score is not None:
            grounding_scores.append(score)

        # Detector 6: Cantidad generada mayor que la efectiva o menor sin aviso
        gen_count = meta.generated_items
        req_count = meta.requested_items or comb.get("target_quantity", 10)
        warning_msg = meta.quantity_warning

        if "expected_items" in comb and gen_count != comb["expected_items"]:
            failures.append(f"FALLO ({comb['id'].upper()}): Cantidad generada {gen_count} difiere de la esperada {comb['expected_items']} para el nivel {comb['quantity_level']}.")

    # Detector 5: Anclaje de fuente idéntico o fijo en 0.98 / 0.85
    if len(set(grounding_scores)) <= 1 and len(grounding_scores) > 1:
        failures.append(f"FALLO: Los scores de anclaje de fuente son idénticos en todas las combinaciones ({grounding_scores}). Debe ser dinámico.")
    if 0.98 in grounding_scores or 0.85 in grounding_scores:
        failures.append(f"FALLO: Se detectaron scores de anclaje fijos hardcodeados (0.98 o 0.85) en {grounding_scores}.")

    # Detector 6: Similitud entre combinaciones distintas >= 0.70
    pairwise_similarities: List[float] = []
    for i in range(4):
        for j in range(i + 1, 4):
            id1, id2 = results[i]["comb"]["id"].upper(), results[j]["comb"]["id"].upper()
            txt1 = " ".join(results[i]["items_text"])
            txt2 = " ".join(results[j]["items_text"])
            sim = difflib.SequenceMatcher(None, txt1, txt2).ratio()
            pairwise_similarities.append(sim)
            if sim >= 0.70:
                failures.append(f"FALLO: Similitud excesiva ({sim:.2%}) entre las combinaciones {id1} y {id2} (límite < 70%).")

    avg_similarity = sum(pairwise_similarities) / max(1, len(pairwise_similarities))
    max_similarity = max(pairwise_similarities) if pairwise_similarities else 0.0

    is_passed = len(failures) == 0

    # 8. CONSTRUCCIÓN DEL REPORTE MARKDOWN
    md_lines = []
    md_lines.append("# Reporte de Diagnóstico y Validación de Adaptación Educativa V2\n")
    md_lines.append(f"**Archivo:** `msJava.pdf` | **Páginas:** {num_pages} | **Caracteres Total:** {total_chars} | **Fecha:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    md_lines.append("## 📊 Tabla Comparativa por Combinación\n")
    md_lines.append("| Comb | Perfil | Formato | Origen | Proveedor & Modelo LLM | Fallback | Embeddings | Modo Rec. | Items (Sol/Gen) | Score Anclaje | Prompt Hash | Latencia |")
    md_lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")

    for res in results:
        comb = res["comb"]
        m = res["metadata"]
        q = res["quality"]
        origin = getattr(m, "origin", getattr(m, "origen", "llm"))
        fallback = getattr(m, "fallback_used", getattr(m, "fallback_usado", False))
        score = getattr(q, "source_grounding_score", getattr(q, "anclaje_fuente_score", "-"))
        prov_llm = getattr(m, "llm_provider", getattr(m, "proveedor_llm", "gemini"))
        mod_llm = getattr(m, "llm_model", getattr(m, "modelo_llm", "gemini-2.5-flash"))
        prov_emb = getattr(m, "embedding_provider", getattr(m, "proveedor_embeddings", "gemini"))
        modo_rec = getattr(m, "retrieval_mode", getattr(m, "modo_recuperacion", "semantico"))
        p_hash = getattr(m, "prompt_hash", "-")
        hash_short = p_hash[:10] + "..." if p_hash and len(p_hash) > 10 else str(p_hash)

        md_lines.append(
            f"| **{comb['id'].upper()}** | {comb['profile']} | {comb['format']} | `{origin}` | {prov_llm} ({mod_llm}) | `{fallback}` | {prov_emb} | `{modo_rec}` | {m.requested_items}/{m.generated_items} | `{score}` | `{hash_short}` | {res['elapsed']}s |"
        )

    md_lines.append("\n## 🔄 Verificación de Caché")
    md_lines.append(f"- **Origen devuelto:** `{origin_cache}`")
    md_lines.append(f"- **Prompt Hash coincidente:** `{hash_a == hash_cache}`")
    md_lines.append(f"- **Latencia en caché:** `{elapsed_cache}s`\n")

    md_lines.append("## 🔍 Análisis de Comparación de Contenido Real")
    md_lines.append(f"- **Similitud Media entre Salidas:** `{avg_similarity:.2%}`")
    md_lines.append(f"- **Similitud Máxima entre Salidas:** `{max_similarity:.2%}`\n")

    md_lines.append("### Primer Ítem Completo por Combinación:")
    for res in results[:4]:
        comb = res["comb"]
        first_it = res["items"][0] if res["items"] else {}
        first_json = json.dumps(first_it, ensure_ascii=False, indent=2)
        md_lines.append(f"\n#### Combinación ({comb['id'].upper()}): {comb['name']}\n```json\n{first_json}\n```")

    md_lines.append("\n## 🏁 Dictamen Final")
    if is_passed:
        md_lines.append("\n### STATUS: **APROBADO** (0 problemas detectados)")
        md_lines.append("Todas las verificaciones de contenido, diferenciación, caché y anclaje a fuentes pasaron exitosamente.")
    else:
        md_lines.append(f"\n### STATUS: **FALLÓ ({len(failures)} problemas detectados)**\n")
        for f_err in failures:
            md_lines.append(f"- ❌ {f_err}")

    report_md = "\n".join(md_lines)

    # Imprimir en stdout
    print(report_md)

    if save_report:
        docs_dir = Path(__file__).parent.parent / "docs"
        docs_dir.mkdir(exist_ok=True)
        report_file = docs_dir / "diagnostico-adaptacion-v2.md"
        report_file.write_text(report_md, encoding="utf-8")
        print(f"\nReporte guardado exitosamente en: {report_file}")

    return is_passed, failures, report_md


if __name__ == "__main__":
    passed, failures, _ = run_adaptation_diagnostics()
    if not passed:
        print(f"\nEJECUCIÓN FINALIZADA CON FALLOS: {len(failures)} problemas.")
        sys.exit(1)
    else:
        print("\nEJECUCIÓN FINALIZADA EXITOSAMENTE: APROBADO.")
        sys.exit(0)
