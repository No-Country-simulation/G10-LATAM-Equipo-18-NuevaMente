from typing import List, Dict, Any
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from loguru import logger

class RobustMarkdownSplitter:
    """
    Usa el MarkdownHeaderTextSplitter de LangChain para crear chunks que respetan la estructura
    lógica de los documentos técnicos (H1, H2, H3), en lugar de cortar ciegamente por caracteres.
    """
    def __init__(self, child_chunk_size: int = 500, child_overlap: int = 50):
        # Cabeceras que queremos detectar y convertir en metadatos para preservar el contexto
        self.headers_to_split_on = [
            ("#", "Header_1"),
            ("##", "Header_2"),
            ("###", "Header_3"),
            ("####", "Header_4"),
        ]
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.headers_to_split_on,
            strip_headers=False
        )
        # Fallback splitter por si un Header es absurdamente largo (ej. no había subtítulos)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_chunk_size,
            chunk_overlap=child_overlap
        )

    def split_document(self, markdown_text: str) -> List[Dict[str, Any]]:
        """
        Divide un texto Markdown en chunks estructurados y luego asegura que
        ningún chunk exceda el tamaño máximo usando RecursiveCharacterTextSplitter.
        """
        try:
            logger.info("Dividiendo documento preservando jerarquía Markdown...")
            # 1. División Semántica (por títulos)
            md_header_splits = self.markdown_splitter.split_text(markdown_text)
            
            # 2. División de Respaldo (para secciones demasiado largas)
            final_splits = self.text_splitter.split_documents(md_header_splits)
            
            # 3. Formateamos la salida
            chunks = []
            for i, split in enumerate(final_splits):
                chunks.append({
                    "chunk_id": f"chunk_md_{i}",
                    "content": split.page_content,
                    "metadata": split.metadata # Esto contendrá {"Header_1": "Introducción", ...}
                })
            
            logger.success(f"Documento dividido exitosamente en {len(chunks)} fragmentos coherentes.")
            return chunks
        except Exception as e:
            logger.error(f"Error al fragmentar documento: {str(e)}")
            raise
