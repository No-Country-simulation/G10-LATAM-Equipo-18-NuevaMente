"""
upload_test_ui.py (frontend_temp)

Purpose:
    Minimal, throwaway Gradio UI to manually test the document upload
    pipeline (process_and_index_document) without waiting for the real
    frontend or an HTTP endpoint. Calls the backend's Python code directly
    — it is not a client of an API, and is not meant to be the final UI.

    Deliberately NOT named app.py: backend/app/ is itself a package called
    "app", and a script with that same name sitting in sys.path can shadow
    it — Python then resolves "import app.services" against this very
    script (a plain file, not a package) instead of the real one.

Input:
    A file (.pdf, .md, .markdown, .txt) uploaded through the browser, plus
    an optional title.

Output:
    A summary of the resulting DocumentRecord (status, object_key, chunk
    counts, or the error message if the pipeline failed), and a table
    listing every document already processed.
"""

import sys
from pathlib import Path

import gradio as gr

# frontend_temp/ is a sibling of backend/ — add backend/ to sys.path so the
# app.* package (config, services, schemas) can be imported regardless of
# which directory this script is launched from.
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_pipeline_service import process_and_index_document
from app.services.document_repository import get_document_repository

DOCUMENT_TABLE_HEADERS = [
    "document_id", "title", "status", "total_parents", "total_children", "created_at",
]


def handle_upload(file_path: str, title: str):
    """Runs the full pipeline on the uploaded file. Yields an immediate
    'processing' message before running anything — without this, Gradio's
    output stays blank until the entire pipeline (upload + ingestion +
    embeddings + indexing) finishes, which can take a while and looks
    frozen with no feedback."""
    if not file_path:
        yield "⚠️ No se seleccionó ningún archivo."
        return

    yield "⏳ Procesando documento... esto puede tardar varios segundos (subida, ingesta, embeddings e indexado)."

    try:
        record = process_and_index_document(local_path=file_path, title=title or None)
    except Exception as exc:
        yield f"❌ **El pipeline falló antes de crear el registro del documento:**\n\n{exc}"
        return

    lines = [
        f"**document_id:** `{record.document_id}`",
        f"**status:** {record.status}",
        f"**title:** {record.title}",
        f"**object_key:** `{record.object_key}`",
        f"**total_parents:** {record.total_parents}",
        f"**total_children:** {record.total_children}",
    ]
    if record.error_message:
        lines.append(f"**error_message:** {record.error_message}")
    yield "\n\n".join(lines)


def list_documents_table():
    """Fetches every document row for display — there's no login yet, so
    nothing is filtered by user."""
    repo = get_document_repository()
    documents = repo.list_documents()
    return [
        [doc.document_id, doc.title, doc.status, doc.total_parents, doc.total_children, doc.created_at]
        for doc in documents
    ]


with gr.Blocks(title="NuevaMente — Prueba de carga") as demo:
    gr.Markdown(
        "# NuevaMente — Prueba de carga de documentos\n"
        "Interfaz temporal para probar el pipeline de subida e indexado. No es el frontend final."
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


if __name__ == "__main__":
    demo.queue()  # required for handle_upload's intermediate "processing" message to actually stream
    demo.launch()