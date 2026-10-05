import gradio as gr
import asyncio
from app.services.ingester_service import IngesterService
from app.services.hybrid_rag_service import HybridRAGService
from app.services.embedding_service import EmbeddingService
from app.schemas.adaptation import AdaptationRequest, PerfilDestinatario, FormatoSalida, NichoSector
from app.services.langgraph_orchestrator import LangGraphOrchestrator

ingester = IngesterService()
embedding_service = EmbeddingService()
hybrid_rag = HybridRAGService(embedding_service=embedding_service)
orchestrator = LangGraphOrchestrator()

# Caché temporal para no hacer parsing a cada rato
DOC_CACHE = {}

def process_document(pdf_file, query, profile, output_format):
    if pdf_file is None:
        return "Por favor, sube un documento PDF."
        
    doc_path = pdf_file.name
    
    # 1. Ingestión (parsear y chunkear)
    if doc_path not in DOC_CACHE:
        # Aquí simulo leer el contenido completo o uso el path para pdfplumber
        # Como es una prueba, leo el texto extraído
        import pypdf
        with open(doc_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            full_text = "\n".join(page.extract_text() for page in reader.pages)
            
        doc_data = ingester.parse_and_chunk_document(full_text, "Documento Gradio")
        DOC_CACHE[doc_path] = doc_data
    else:
        doc_data = DOC_CACHE[doc_path]

    # 2. Recuperación Híbrida (BM25 + Denso + Rerank)
    top_passages = hybrid_rag.retrieve_top_passages(
        query=query,
        child_chunks=doc_data["child_chunks"],
        parent_chunks=doc_data["parent_chunks"],
        top_k=3
    )
    
    # 3. Orquestador Multi-Agente
    context_str = "\n".join([p["content"] for p in top_passages])
    
    req = AdaptationRequest(
        documento_titulo="Documento Custom Gradio",
        documento_contenido=context_str,
        perfil_destinatario=PerfilDestinatario(profile.lower()),
        formato_salida=FormatoSalida(output_format.lower()),
        nicho_sector=NichoSector.GENERAL
    )
    
    try:
        adapted_content = orchestrator.run(req, context_str)
        return f"### Documentos recuperados por RAG:\n{len(top_passages)} chunks clave encontrados.\n\n### Respuesta del Agente:\n```json\n{adapted_content.model_dump_json(indent=2)}\n```"
    except Exception as e:
        return f"Error en los agentes: {str(e)}"

# Interfaz Gradio
with gr.Blocks(title="Test RAG + Agentes") as demo:
    gr.Markdown("# 🤖 Probador de RAG Híbrido y Multi-Agentes de NuevaMente")
    
    with gr.Row():
        with gr.Column():
            file_input = gr.File(label="Sube tu PDF técnico", file_types=[".pdf"])
            query_input = gr.Textbox(label="Instrucción RAG (ej. 'explicar seguridad VCN')", lines=2)
            profile_input = gr.Dropdown(["principiante", "junior", "senior", "ejecutivo"], label="Perfil", value="principiante")
            format_input = gr.Dropdown(["tutorial", "flashcards", "quiz", "resumen"], label="Formato", value="tutorial")
            submit_btn = gr.Button("¡Adaptar Contenido!", variant="primary")
            
        with gr.Column():
            output_text = gr.Markdown(label="Salida del Sistema")
            
    submit_btn.click(
        fn=process_document,
        inputs=[file_input, query_input, profile_input, format_input],
        outputs=output_text
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
