"""
upload_test_ui.py (frontend_temp)

Purpose:
    Gradio web interface for testing document ingestion, chunking, embedding
    generation, and vector store indexing. Displays live pipeline progress
    (batches, waits, retries, provider switches), active model identification,
    and samples of generated chunks and vectors.

Input:
    Uploaded document file (.pdf, .md, .markdown, .txt) and optional title,
    or document identifier for existing indexed stores.

Output:
    Live progress messages while processing, then document processing status,
    active embedding model details, and formatted inspection samples (first,
    second, penultimate, and final chunks with vector values).
"""

import json
import queue
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_pipeline_service import process_and_index_document
from app.services.document_repository import get_document_repository
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import get_store
from app.services.retrieval_service import retrieve_context
from app.services.agent_orchestrator import AgentOrchestrator
from app.schemas.adaptation import AdaptationRequest
from app.core.labels import PROFILE_LABELS_ES, FORMAT_LABELS_ES, NICHE_LABELS_ES

DOCUMENT_TABLE_HEADERS = [
    "document_id", "title", "status", "total_parents", "total_children", "created_at",
]

# Icon shown next to each pipeline stage in the live progress list.
STAGE_ICONS = {
    "uploading": "📤",
    "ingesting": "📄",
    "embedding": "🧮",
    "waiting": "⏸️",
    "retrying": "🔁",
    "switching_provider": "🔀",
    "indexing": "🗂️",
    "ready": "✅",
    "failed": "❌",
}


def select_sample_indices(total_count: int) -> List[Tuple[str, int]]:
    """Selects up to four representative indices (first, second, penultimate, last)."""
    if total_count <= 0:
        return []
    if total_count == 1:
        return [("Initial / Only", 0)]
    if total_count == 2:
        return [("Initial (0)", 0), ("Final (1)", 1)]
    if total_count == 3:
        return [("Initial (0)", 0), ("Second (1)", 1), ("Final (2)", 2)]

    return [
        ("Initial (0)", 0),
        ("Second (1)", 1),
        (f"Penultimate ({total_count - 2})", total_count - 2),
        (f"Final ({total_count - 1})", total_count - 1),
    ]


def extract_vector_sample(index, idx: int) -> Optional[np.ndarray]:
    """Reconstructs vector array at index from FAISS IndexFlatIP."""
    try:
        return index.reconstruct(int(idx))
    except Exception:
        return None


def format_vector_snippet(vector: Optional[np.ndarray]) -> str:
    """Formats a concise representation of vector elements and L2 norm."""
    if vector is None:
        return "*Vector data unavailable for direct inspection.*"

    dimension = len(vector)
    norm = float(np.linalg.norm(vector))
    start_vals = [f"{float(v):.4f}" for v in vector[:5]]
    end_vals = [f"{float(v):.4f}" for v in vector[-3:]]

    start_str = ", ".join(start_vals)
    end_str = ", ".join(end_vals)
    omitted = max(0, dimension - 8)

    return (
        f"`[{start_str}, ... ({omitted} values omitted) ..., {end_str}]`\n"
        f"  - **Dimensions:** `{dimension}` | **L2 Norm:** `{norm:.4f}`"
    )


def format_document_inspection(document_id: str) -> str:
    """Generates Markdown inspection report with model tags and chunk/vector samples."""
    store = get_store(document_id)
    if store is None or not store.child_documents:
        return f"⚠️ No indexed vector store found for `document_id`: `{document_id}`."

    child_chunks = store.child_documents
    total_children = len(child_chunks)
    model_tag = store.model_name or "Unknown"

    # Identify provider from model identifier
    lower_tag = model_tag.lower()
    if "gemini" in lower_tag:
        provider_name = "Google Gemini"
    elif "jina" in lower_tag:
        provider_name = "Jina AI"
    elif "sentence-transformers" in lower_tag or "mpnet" in lower_tag:
        provider_name = "Local (SentenceTransformers)"
    else:
        provider_name = "Configured Default"

    lines = [
        "### 🧠 Active Embedding Model & Vector Store",
        f"- **Model Identifier:** `{model_tag}`",
        f"- **Detected Provider:** **{provider_name}**",
        f"- **Configured Vector Dimension:** `{store.dimension}`",
        f"- **Total Indexed Vectors:** `{store.index.ntotal if store.index else 0}`",
        f"- **Total Child Chunks:** `{total_children}`",
        f"- **Total Parent Chunks:** `{len(store.parent_documents)}`",
        "",
        f"### 🔍 Chunk & Embedding Samples ({min(4, total_children)} of {total_children})",
        "",
    ]

    samples = select_sample_indices(total_children)
    for sample_label, idx in samples:
        chunk = child_chunks[idx]
        chunk_id = chunk.get("id", f"chunk_{idx}")
        breadcrumb = chunk.get("breadcrumb", "N/A")
        content = chunk.get("content", "").strip()
        char_count = len(content)

        vector = extract_vector_sample(store.index, idx) if store.index else None
        vector_str = format_vector_snippet(vector)

        # Truncate content for clean UI rendering if text is long
        display_content = content if len(content) <= 300 else f"{content[:300]}..."

        lines.extend([
            f"#### 📌 Sample: {sample_label} (Index {idx} of {total_children})",
            f"- **Chunk ID:** `{chunk_id}`",
            f"- **Breadcrumb:** `{breadcrumb}`",
            f"- **Length:** `{char_count}` characters",
            f"- **Content Excerpt:**",
            f"> {display_content}",
            f"- **Vector Sample:**",
            f"  {vector_str}",
            "",
        ])

    return "\n".join(lines)


def format_progress_line(event: Dict[str, Any]) -> str:
    """Formats one pipeline event as a Markdown line, with a text progress bar when counts are present."""
    icon = STAGE_ICONS.get(event.get("stage", ""), "•")
    line = f"{icon} {event.get('message', '')}"

    current, total = event.get("current"), event.get("total")
    if event.get("stage") == "embedding" and current is not None and total:
        filled = round(10 * current / total)
        line += f"  `{'█' * filled}{'░' * (10 - filled)}` {round(100 * current / total)}%"
    return line


def render_progress(lines: List[str], working: bool) -> str:
    """Builds the live progress Markdown: the history so far, marked as running while work continues."""
    header = "### ⏳ Procesando documento…" if working else "### 🧾 Registro del proceso"
    return header + "\n\n" + "\n\n".join(lines)


def handle_upload(file_path: str, title: str):
    """Runs the ingestion pipeline in a worker thread and yields live progress, then the final report."""
    if not file_path:
        yield "⚠️ No se seleccionó ningún archivo."
        return

    events: "queue.Queue[Optional[Dict[str, Any]]]" = queue.Queue()
    outcome: Dict[str, Any] = {}

    def run_pipeline() -> None:
        try:
            outcome["record"] = process_and_index_document(
                local_path=file_path,
                title=title or None,
                on_progress=events.put,
            )
        except Exception as exc:
            outcome["error"] = exc
        finally:
            events.put(None)  # Sentinel: the pipeline finished (successfully or not).

    threading.Thread(target=run_pipeline, daemon=True).start()

    progress_lines: List[str] = []
    last_stage: Optional[str] = None
    yield render_progress(["⏳ Iniciando…"], working=True)

    while True:
        event = events.get()
        if event is None:
            break

        line = format_progress_line(event)
        # Consecutive embedding events update one line instead of listing every batch.
        if event.get("stage") == "embedding" and last_stage == "embedding":
            progress_lines[-1] = line
        else:
            progress_lines.append(line)
        last_stage = event.get("stage")

        yield render_progress(progress_lines, working=True)

    progress_log = render_progress(progress_lines, working=False)

    if "error" in outcome:
        yield (
            f"❌ **El pipeline falló:**\n\n{outcome['error']}\n\n"
            "Si el documento ya se había registrado, quedó con estado `failed` "
            "en la pestaña *Documentos existentes*.\n\n---\n\n" + progress_log
        )
        return

    record = outcome["record"]
    summary_lines = [
        "### 📄 Document Pipeline Summary",
        f"- **document_id:** `{record.document_id}`",
        f"- **status:** `{record.status}`",
        f"- **title:** {record.title}",
        f"- **object_key:** `{record.object_key}`",
        f"- **total_parents:** `{record.total_parents}`",
        f"- **total_children:** `{record.total_children}`",
    ]
    if record.error_message:
        summary_lines.append(f"- **error_message:** `{record.error_message}`")

    full_output = "\n".join(summary_lines)
    if record.status == "ready":
        full_output += "\n\n---\n\n" + format_document_inspection(record.document_id)

    yield full_output + "\n\n---\n\n" + progress_log


def list_documents_table():
    """Retrieves all registered document records for display."""
    repo = get_document_repository()
    documents = repo.list_documents()
    return [
        [doc.document_id, doc.title, doc.status, doc.total_parents, doc.total_children, doc.created_at]
        for doc in documents
    ]


def inspect_selected_document(doc_id: str) -> str:
    """Inspects chunks and vectors for an existing document ID."""
    if not doc_id or not doc_id.strip():
        return "⚠️ Ingrese un `document_id` válido para inspeccionar."
    return format_document_inspection(doc_id.strip())


def handle_agent_generation(
    doc_id: str,
    profile_label: str,
    format_label: str,
    niche_label: str,
    language: str,
    quantity_level: str,
    target_quantity: Optional[int],
) -> Tuple[str, str]:
    """Retrieves document context with RAG and generates educational content with multi-stage agents."""
    if not doc_id or not doc_id.strip():
        return "⚠️ Ingrese un `document_id` válido.", ""

    clean_id = doc_id.strip()
    repo = get_document_repository()
    doc_record = repo.get_document(clean_id)
    if not doc_record:
        return f"❌ No se encontró ningún documento con ID `{clean_id}` en la base de datos.", ""
    if doc_record.status != "ready":
        return f"⚠️ El documento está en estado `{doc_record.status}`. Debe estar en estado `ready` para consultar.", ""

    # Reverse lookup from label to internal key
    profile_rev = {v: k for k, v in PROFILE_LABELS_ES.items()}
    format_rev = {v: k for k, v in FORMAT_LABELS_ES.items()}
    niche_rev = {v: k for k, v in NICHE_LABELS_ES.items()}

    profile_key = profile_rev.get(profile_label, "junior_developer")
    format_key = format_rev.get(format_label, "flashcards")
    niche_key = niche_rev.get(niche_label, "general")

    query = f"{profile_label} {format_label} {niche_label}"

    try:
        # 1. Retrieve RAG context (dense + BM25 + RRF + reranker)
        top_passages = retrieve_context(
            document_id=clean_id,
            query=query,
            top_k=5,
        )
    except Exception as exc:
        return f"❌ Error en la etapa de recuperación RAG: {exc}", ""

    if not top_passages:
        return "⚠️ No se encontraron fragmentos relevantes en el índice para esta consulta.", ""

    # 2. Build AdaptationRequest
    request = AdaptationRequest(
        title=doc_record.title,
        content="\n\n".join(p.get("content", "") for p in top_passages),
        recipient_profile=profile_label,
        output_format=format_key,
        niche=niche_label,
        quantity_level=quantity_level,
        target_quantity=int(target_quantity) if target_quantity else None,
        language=language,
    )

    # 3. Execute multi-stage agents
    try:
        import asyncio
        orchestrator = AgentOrchestrator()
        loop = asyncio.new_event_loop()
        try:
            response = loop.run_until_complete(
                orchestrator.run_pipeline(
                    request=request,
                    top_passages=top_passages,
                    key_concepts=[],
                    prerequisites=[],
                )
            )
        finally:
            loop.close()
    except Exception as exc:
        return f"❌ Error durante la generación con agentes: {exc}", ""

    # 4. Format Visual Output
    meta = response.metadata
    adapted = response.adapted_content
    eval_info = response.quality_evaluation

    md_lines = [
        f"## 🎓 {adapted.title}",
        f"*{adapted.contextualized_introduction}*",
        "",
        "| Métrica | Valor |",
        "| :--- | :--- |",
        f"| **Proveedor LLM** | `{meta.llm_provider}` |",
        f"| **Items Generados** | `{meta.generated_items}` (solicitados: `{meta.requested_items}`) |",
        f"| **Score de Anclaje RAG** | `{eval_info.source_grounding_score * 100:.0f}%` (Citas verificadas) |",
        f"| **Tiempo de Estudio Estimado** | `{meta.estimated_study_time_minutes} minutos` |",
        f"| **Ubicación en Storage** | `{response.oci_storage.bucket}/{response.oci_storage.object_id}` |",
        "",
    ]

    if meta.quantity_warning:
        md_lines.append(f"> ⚠️ **Aviso de Capacidad:** {meta.quantity_warning}\n")

    def format_source_badges(fuentes: List[Any]) -> str:
        """Formats citation sources cleanly for the user, hiding internal chunk IDs."""
        formatted = []
        for f in fuentes:
            if not isinstance(f, dict):
                continue
            parts = []
            sec = f.get("seccion")
            bc = f.get("breadcrumb")
            if sec and bc and sec != bc:
                parts.append(f"**{bc}** &rsaquo; *{sec}*")
            elif sec:
                parts.append(f"**{sec}**")
            elif bc:
                parts.append(f"*{bc}*")
            else:
                parts.append("Documento base")

            page_val = f.get("pagina")
            if isinstance(page_val, int) and page_val > 0:
                parts.append(f"Pág. {page_val}")

            extract = f.get("extracto")
            if extract and len(extract.strip()) > 0:
                clean_extract = extract.strip().replace("\n", " ")
                if len(clean_extract) > 85:
                    clean_extract = clean_extract[:82] + "..."
                parts.append(f'&laquo;{clean_extract}&raquo;')

            formatted.append(" | ".join(parts))
        return " &bull; ".join(formatted) if formatted else ""

    # Format specific item views
    if "flashcard" in format_key.lower():
        md_lines.append("### 🗂️ Mazo de Flashcards Generadas\n")
        items = adapted.items or []
        for i, card in enumerate(items, 1):
            front = card.get("frente") or card.get("front", "")
            back = card.get("dorso") or card.get("back", "")
            hint = card.get("pista_didactica") or card.get("hint", "")
            fuentes = card.get("fuentes") or card.get("sources") or []

            md_lines.append(f"**🃏 Tarjeta {i:02d}**")
            md_lines.append(f"* **Pregunta / Frente:** {front}")
            md_lines.append(f"* **Respuesta / Dorso:** {back}")
            if hint:
                md_lines.append(f"* **Pista didáctica:** 💡 *{hint}*")
            src_str = format_source_badges(fuentes)
            if src_str:
                md_lines.append(f"* **Fuente:** 🔍 {src_str}")
            md_lines.append("\n---\n")

    elif "quiz" in format_key.lower():
        md_lines.append("### 📝 Preguntas de Quiz Interactivas\n")
        quizzes = adapted.quizzes or adapted.items or []
        for i, q in enumerate(quizzes, 1):
            if isinstance(q, dict):
                pregunta = q.get("pregunta", "")
                opciones = q.get("opciones", [])
                correcta = q.get("respuesta_correcta", "")
                justif = q.get("justificacion_didactica") or q.get("justificacion", "")
                fuentes = q.get("fuentes") or q.get("sources") or []
            else:
                pregunta = q.question
                opciones = q.options
                correcta = q.correct_answer
                justif = q.didactic_justification or q.justification or ""
                fuentes = getattr(q, "sources", []) or getattr(q, "fuentes", [])

            md_lines.append(f"**🎯 Pregunta {i:02d}:** {pregunta}\n")
            md_lines.append("**Opciones:**")
            for opt in opciones:
                mark = "✅ **[Correcta]** " if opt == correcta else "⚪ "
                md_lines.append(f"  * {mark}{opt}")
            if justif:
                md_lines.append(f"\n* **Justificación Didáctica:** 📖 {justif}")
            src_str = format_source_badges(fuentes)
            if src_str:
                md_lines.append(f"* **Fuente:** 🔍 {src_str}")
            md_lines.append("\n---\n")

    elif "tutorial" in format_key.lower():
        md_lines.append("### 📖 Guía Paso a Paso (Tutorial)\n")
        sections = adapted.tutorial_sections or adapted.items or []
        for i, sec in enumerate(sections, 1):
            encabezado = sec.get("encabezado") or sec.get("titulo") or f"Paso {i}"
            contenido = sec.get("contenido") or sec.get("instruccion", "")
            ejemplo = sec.get("ejemplo", "")
            fuentes = sec.get("fuentes") or sec.get("sources") or []

            md_lines.append(f"#### 📌 {encabezado}\n")
            md_lines.append(f"{contenido}\n")
            if ejemplo:
                md_lines.append(f"```text\n{ejemplo}\n```\n")
            src_str = format_source_badges(fuentes)
            if src_str:
                md_lines.append(f"* **Fuente:** 🔍 {src_str}")
            md_lines.append("\n---\n")

    elif "guion" in format_key.lower() or "video" in format_key.lower():
        md_lines.append("### 🎬 Guion de Clase / Video Educativo\n")
        for sc in (adapted.items or []):
            escena_num = sc.get("escena", 1)
            duracion = sc.get("duracion_seg", 30)
            narracion = sc.get("narracion", "")
            apoyo = sc.get("apoyo_visual", "")
            fuentes = sc.get("fuentes") or sc.get("sources") or []

            md_lines.append(f"#### 🎬 Escena {escena_num} (Duración: {duracion} seg)\n")
            md_lines.append(f"* **🎙️ Narración (Voz en off):**\n  > {narracion}\n")
            if apoyo:
                md_lines.append(f"* **🎥 Apoyo Visual:** {apoyo}")
            src_str = format_source_badges(fuentes)
            if src_str:
                md_lines.append(f"* **Fuente:** 🔍 {src_str}")
            md_lines.append("\n---\n")

    elif "resumen" in format_key.lower():
        md_lines.append("### 📋 Resumen Ejecutivo (TL;DR)\n")
        items = adapted.items or []
        if items:
            for i, it in enumerate(items, 1):
                punto = it.get("punto_clave", "")
                impacto = it.get("impacto_negocio", "")
                fuentes = it.get("fuentes") or it.get("sources") or []
                md_lines.append(f"**📌 Punto {i:02d}: {punto}**")
                md_lines.append(f"* **Impacto Operativo / Negocio:** {impacto}")
                src_str = format_source_badges(fuentes)
                if src_str:
                    md_lines.append(f"* **Fuente:** 🔍 {src_str}")
                md_lines.append("\n---\n")
        elif adapted.executive_summary:
            md_lines.append(adapted.executive_summary)
            md_lines.append("\n---\n")

    json_str = json.dumps(response.model_dump(), ensure_ascii=False, indent=2)
    return "\n".join(md_lines), json_str


with gr.Blocks(title="NuevaMente — Suite de Ingestión y Agentes") as demo:
    gr.Markdown(
        "# 🧠 NuevaMente — Prueba de Ingesta, RAG y Agentes Educativos\n"
        "Suite integral para probar el pipeline completo: desde la carga del documento técnico hasta la generación agéntica."
    )

    with gr.Tab("1. Subir documento"):
        file_input = gr.File(
            label="Documento (.pdf, .md, .txt)",
            file_types=[".pdf", ".md", ".markdown", ".txt"],
            type="filepath",
        )
        title_input = gr.Textbox(label="Título (opcional)")
        submit_button = gr.Button("Procesar documento", variant="primary")
        result_output = gr.Markdown()

        submit_button.click(fn=handle_upload, inputs=[file_input, title_input], outputs=result_output)

    with gr.Tab("2. Documentos existentes"):
        refresh_button = gr.Button("Actualizar listado")
        documents_table = gr.Dataframe(headers=DOCUMENT_TABLE_HEADERS, label="Documentos procesados")

        refresh_button.click(fn=list_documents_table, outputs=documents_table)
        demo.load(fn=list_documents_table, outputs=documents_table)

        gr.Markdown("---")
        gr.Markdown("### Inspeccionar Chunks y Embeddings de un Documento Existente")
        with gr.Row():
            doc_id_input = gr.Textbox(label="ID del Documento (document_id)", placeholder="Pegue aquí el document_id")
            inspect_button = gr.Button("Inspeccionar Chunks y Vectores")

        inspection_output = gr.Markdown()
        inspect_button.click(
            fn=inspect_selected_document,
            inputs=[doc_id_input],
            outputs=inspection_output,
        )

    with gr.Tab("3. 🤖 Generar con Agentes (RAG)"):
        gr.Markdown("### Adaptación Pedagógica con Agentes Multimodales e Híbridos (RAG + Cross-Encoder)")
        with gr.Row():
            agent_doc_id = gr.Textbox(
                label="Document ID",
                placeholder="Pegue aquí el ID del documento en estado 'ready'",
                scale=2,
            )
            agent_language = gr.Dropdown(
                label="Idioma de Salida",
                choices=["Spanish", "English", "Portuguese"],
                value="Spanish",
                scale=1,
            )

        with gr.Row():
            profile_dropdown = gr.Dropdown(
                label="Perfil del Estudiante",
                choices=list(PROFILE_LABELS_ES.values()),
                value=PROFILE_LABELS_ES.get("junior_developer", "Desarrollador Junior / Semi Senior"),
            )
            format_dropdown = gr.Dropdown(
                label="Formato de Salida",
                choices=list(FORMAT_LABELS_ES.values()),
                value=FORMAT_LABELS_ES.get("flashcards", "Flashcards de Memorización"),
            )
            niche_dropdown = gr.Dropdown(
                label="Sector / Nicho",
                choices=list(NICHE_LABELS_ES.values()),
                value=NICHE_LABELS_ES.get("general", "General"),
            )

        with gr.Row():
            quantity_radio = gr.Radio(
                label="Nivel de Cantidad",
                choices=["Breve", "Estandar", "Amplio", "Exhaustivo"],
                value="Estandar",
            )
            target_qty_input = gr.Number(
                label="Cantidad Específica (Opcional)",
                value=None,
                precision=0,
            )

        generate_button = gr.Button("🚀 Iniciar Generación Agéntica", variant="primary")

        with gr.Tabs():
            with gr.TabItem("Visualización Didáctica"):
                agent_visual_output = gr.Markdown()
            with gr.TabItem("JSON Completo del Artefacto"):
                agent_json_output = gr.Code(language="json")

        generate_button.click(
            fn=handle_agent_generation,
            inputs=[
                agent_doc_id,
                profile_dropdown,
                format_dropdown,
                niche_dropdown,
                agent_language,
                quantity_radio,
                target_qty_input,
            ],
            outputs=[agent_visual_output, agent_json_output],
        )


if __name__ == "__main__":
    local_available, local_message = EmbeddingService().check_local_available()
    print(f"[Fallback local] {'OK' if local_available else 'NO DISPONIBLE'}: {local_message}")

    demo.queue()
    demo.launch()
