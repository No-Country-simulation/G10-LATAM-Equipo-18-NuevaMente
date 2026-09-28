"""
upload_test_ui.py (frontend_temp)

Purpose:
    Gradio web interface for testing document ingestion, chunking, embedding
    generation, and vector store indexing. Displays real-time pipeline status,
    active model identification, and samples of generated chunks and vectors.

Input:
    Uploaded document file (.pdf, .md, .markdown, .txt) and optional title,
    or document identifier for existing indexed stores.

Output:
    Document processing status, active embedding model details, and formatted
    inspection samples (first, second, penultimate, and final chunks with vector values).
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr
import numpy as np

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_pipeline_service import process_and_index_document
from app.services.document_repository import get_document_repository
from app.services.vector_store_service import get_store

DOCUMENT_TABLE_HEADERS = [
    "document_id", "title", "status", "total_parents", "total_children", "created_at",
]


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


def handle_upload(file_path: str, title: str):
    """Executes ingestion pipeline and yields progress followed by inspection details."""
    if not file_path:
        yield "⚠️ No se seleccionó ningún archivo."
        return

    yield "⏳ Procesando documento... esto puede tardar varios segundos (subida, ingesta, embeddings e indexado)."

    try:
        record = process_and_index_document(local_path=file_path, title=title or None)
    except Exception as exc:
        yield f"❌ **El pipeline falló antes de crear el registro del documento:**\n\n{exc}"
        return

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

    if record.status == "ready":
        inspection_details = format_document_inspection(record.document_id)
        full_output = "\n".join(summary_lines) + "\n\n---\n\n" + inspection_details
    else:
        full_output = "\n".join(summary_lines)

    yield full_output


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


with gr.Blocks(title="NuevaMente — Prueba de carga") as demo:
    gr.Markdown(
        "# NuevaMente — Prueba de carga de documentos e inspección vectorial\n"
        "Interfaz para probar el pipeline de subida, extracción de chunks, generación de embeddings y persistencia en FAISS."
    )

    with gr.Tab("Subir documento"):
        file_input = gr.File(
            label="Documento (.pdf, .md, .txt)",
            file_types=[".pdf", ".md", ".markdown", ".txt"],
            type="filepath",
        )
        title_input = gr.Textbox(label="Título (opcional)")
        submit_button = gr.Button("Procesar documento", variant="primary")
        result_output = gr.Markdown()

        submit_button.click(fn=handle_upload, inputs=[file_input, title_input], outputs=result_output)

    with gr.Tab("Documentos existentes"):
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


if __name__ == "__main__":
    demo.queue()
    demo.launch()