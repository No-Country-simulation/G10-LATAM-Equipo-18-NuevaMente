"""
ingester_service.py

Purpose:
    Robust document ingestion with Semantic Recursive Hybrid Chunking and
    Parent-Child hierarchical structure.
    Loads and processes technical documents (PDF, Markdown, Plain Text),
    removes header/footer noise, extracts section structure, and produces
    dynamically sized, semantically bounded parent and child chunks for the RAG pipeline.
"""

import logging
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Tuple

from pypdf import PdfReader
from app.core.config import settings
from app.schemas.ingestion import IngestedDocument, DocumentChunk, IngestionOptions
from app.schemas.rag_chunks import ParentChunk, ParentChunkMetadata, ChildChunk, ChildChunkMetadata

logger = logging.getLogger(__name__)


@dataclass
class Section:
    """Internal representation of one heading + its body text."""
    title: Optional[str]
    level: int
    content: str
    page_number: Optional[int] = None


class IngesterService:
    def __init__(
        self,
        child_chunk_size: int = settings.CHILD_CHUNK_SIZE,
        parent_chunk_size: int = settings.CHUNK_SIZE,
        overlap: int = settings.CHUNK_OVERLAP,
        child_overlap: int = settings.CHILD_CHUNK_OVERLAP,
    ):
        self.child_chunk_size = child_chunk_size
        self.parent_chunk_size = parent_chunk_size
        self.overlap = overlap
        self.child_overlap = child_overlap

        self._pdf_parser = None
        self._keybert_model = None

    # ---------------------------------------------------------------------------
    # File validation
    # ---------------------------------------------------------------------------
    @staticmethod
    def validate_file(filepath: Path) -> None:
        extension = filepath.suffix.lower()
        if extension not in settings.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Tipo de archivo no soportado: {extension}. "
                f"Soportados: {settings.SUPPORTED_EXTENSIONS}"
            )

        size_mb = filepath.stat().st_size / (1024 * 1024)
        if size_mb > settings.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"Archivo demasiado grande: {size_mb:.1f}MB. El límite es {settings.MAX_FILE_SIZE_MB}MB."
            )

    # ---------------------------------------------------------------------------
    # Noise removal
    # ---------------------------------------------------------------------------
    @staticmethod
    def remove_repeated_lines(pages_text: List[str], min_repetition_ratio: float = 0.4) -> List[str]:
        if len(pages_text) < 3:
            return pages_text

        line_counts = Counter()
        for page in pages_text:
            unique_lines_in_page = {line.strip() for line in page.split("\n") if line.strip()}
            line_counts.update(unique_lines_in_page)

        threshold = max(2, int(len(pages_text) * min_repetition_ratio))
        noisy_lines = {line for line, count in line_counts.items() if count >= threshold}

        cleaned_pages = []
        for page in pages_text:
            kept_lines = [line for line in page.split("\n") if line.strip() not in noisy_lines]
            cleaned_pages.append("\n".join(kept_lines))

        return cleaned_pages

    # ---------------------------------------------------------------------------
    # Text extractors
    # ---------------------------------------------------------------------------
    def _get_pdf_parser(self):
        if self._pdf_parser is None:
            from app.services.pdf_parser_service import PdfParserService
            self._pdf_parser = PdfParserService()
        return self._pdf_parser

    def _extract_text_from_pdf_legacy(self, filepath: Path) -> str:
        reader = PdfReader(str(filepath))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        cleaned_pages = self.remove_repeated_lines(pages_text)

        pages_with_metadata = [
            f"\n[PÁGINA {i + 1}]\n{page_str}"
            for i, page_str in enumerate(cleaned_pages) if page_str.strip()
        ]
        return "\n".join(pages_with_metadata)

    def extract_text_from_pdf(self, filepath: Path) -> str:
        pdf_parser = self._get_pdf_parser()
        if pdf_parser.is_available:
            try:
                return pdf_parser.parse_pdf_to_markdown(str(filepath))
            except Exception as exc:
                logger.warning(
                    "Extracción Markdown falló para %s (%s). Usando extracción plain-text.",
                    filepath.name, exc,
                )

        return self._extract_text_from_pdf_legacy(filepath)

    @staticmethod
    def extract_text_from_markdown(filepath: Path) -> str:
        return filepath.read_text(encoding="utf-8")

    @staticmethod
    def extract_text_from_txt(filepath: Path) -> str:
        return filepath.read_text(encoding="utf-8")

    def load_file(self, filepath: Path, options: Optional[IngestionOptions] = None) -> str:
        self.validate_file(filepath)
        extension = filepath.suffix.lower()

        try:
            if extension == ".pdf":
                return self.extract_text_from_pdf(filepath)
            elif extension in (".md", ".markdown"):
                return self.extract_text_from_markdown(filepath)
            elif extension == ".txt":
                return self.extract_text_from_txt(filepath)
            else:
                raise ValueError(f"No hay extractor registrado para {extension}")
        except Exception as error:
            raise ValueError(f"Error al leer {filepath.name}: {error}") from error

    # ---------------------------------------------------------------------------
    # Section detection
    # ---------------------------------------------------------------------------
    @staticmethod
    def clean_inline_markdown(text: str) -> str:
        return re.sub(r"[*_`>]", "", text)

    def parse_markdown_sections(self, text: str) -> List[Section]:
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
        matches = list(heading_pattern.finditer(text))

        if not matches:
            return [Section(title=None, level=0, content=self.clean_inline_markdown(text))]

        sections: List[Section] = []
        if matches[0].start() > 0:
            preamble = text[: matches[0].start()].strip()
            if preamble:
                sections.append(Section(title=None, level=0, content=self.clean_inline_markdown(preamble)))

        for index, match in enumerate(matches):
            level = len(match.group(1))
            title = match.group(2).strip()
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = self.clean_inline_markdown(text[start:end].strip())
            sections.append(Section(title=title, level=level, content=content))

        return sections

    def parse_txt_sections_heuristic(self, text: str) -> List[Section]:
        heading_label = re.compile(r"^(cap[ií]tulo|secci[oó]n|chapter|section)\s+\w+", re.IGNORECASE)
        heading_numbering = re.compile(r"^\d+(\.\d+)*[.)]?\s+\S")

        sections: List[Section] = []
        current_title: Optional[str] = None
        current_lines: List[str] = []

        def flush():
            content = "\n".join(current_lines).strip()
            if content:
                sections.append(Section(title=current_title, level=1 if current_title else 0, content=content))

        for line in text.split("\n"):
            stripped = line.strip()
            looks_like_heading = bool(stripped) and len(stripped) < 80 and (
                stripped.isupper() or heading_label.match(stripped) or heading_numbering.match(stripped)
            )

            if looks_like_heading:
                flush()
                current_title = stripped
                current_lines = []
            else:
                current_lines.append(line)

        flush()
        return sections or [Section(title=None, level=0, content=text.strip())]

    @staticmethod
    def parse_pdf_pages(text: str) -> List[Section]:
        page_marker = re.compile(r"\[PÁGINA (\d+)\]\n?")
        matches = list(page_marker.finditer(text))

        if not matches:
            return [Section(title=None, level=0, content=text.strip())]

        sections: List[Section] = []
        for index, match in enumerate(matches):
            page_number = int(match.group(1))
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            if content:
                sections.append(Section(title=None, level=0, content=content, page_number=page_number))

        return sections

    def detect_sections(self, text: str, extension: str) -> List[Section]:
        if extension == ".pdf":
            if "[PÁGINA" in text:
                return self.parse_pdf_pages(text)
            else:
                return self.parse_markdown_sections(text)
        elif extension in (".md", ".markdown"):
            return self.parse_markdown_sections(text)
        elif extension == ".txt":
            return self.parse_txt_sections_heuristic(text)
        return [Section(title=None, level=0, content=text)]

    # ---------------------------------------------------------------------------
    # SEMANTIC RECURSIVE HYBRID CHUNKING ALGORITHM
    # ---------------------------------------------------------------------------
    @staticmethod
    def calculate_adaptive_params(text: str) -> Tuple[int, int, int, int]:
        """Calcula dinámicamente los parámetros de chunking adaptativo (Parent/Child)
        basado en la densidad de código, presencia de tablas y longitud total."""
        total_len = len(text)
        code_matches = re.findall(r'```[\s\S]*?```', text)
        code_length = sum(len(m) for m in code_matches)
        code_ratio = (code_length / total_len) if total_len > 0 else 0

        # Alta densidad de código (ej: archivos técnicos, scripts)
        if code_ratio > 0.15:
            return 800, 120, 350, 35
        # Documentos cortos o concisos
        elif total_len < 4000:
            return 700, 100, 300, 30
        # Documentación estándar o extensa
        else:
            return 1200, 180, 450, 45

    def split_recursively_by_separators(
        self, text: str, target_size: int, overlap: int, separators: Optional[List[str]] = None
    ) -> List[str]:
        """Algoritmo de segmentación recursiva híbrida respetando jerarquía de separadores
        naturales (Encabezados, Bloques de Código, Párrafos, Oraciones y Palabras)."""
        if not text.strip():
            return []

        if separators is None:
            separators = ["\n# ", "\n## ", "\n### ", "\n```", "\n\n", "\n", ". ", " "]

        if len(text) <= target_size:
            return [text.strip()]

        # Buscar el separador de mayor jerarquía presente en el texto
        current_sep = ""
        for sep in separators:
            if sep in text:
                current_sep = sep
                break

        if not current_sep:
            # Fallback a ventana deslizante por caracteres si no hay separadores
            return self.split_by_characters(text, target_size, overlap)

        splits = text.split(current_sep)
        chunks: List[str] = []
        current_chunk = ""

        for idx, split in enumerate(splits):
            piece = (split + current_sep) if idx < len(splits) - 1 else split
            if len(piece.strip()) == 0:
                continue

            if len(piece) > target_size:
                # Si una sola pieza excede el tamaño objetivo, desciende al siguiente separador
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                sub_seps = separators[separators.index(current_sep) + 1 :] if current_sep in separators else None
                chunks.extend(self.split_recursively_by_separators(piece, target_size, overlap, sub_seps))
            else:
                candidate = (current_chunk + piece) if current_chunk else piece
                if len(candidate) <= target_size:
                    current_chunk = candidate
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = piece

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    @staticmethod
    def split_by_characters(text: str, chunk_size: int, overlap: int) -> List[str]:
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)
            if end < text_length:
                boundary = max(text.rfind(" ", start, end), text.rfind("\n", start, end))
                if boundary > start:
                    end = boundary

            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)

            next_start = end - overlap
            if next_start <= start:
                next_start = end

            if next_start < text_length:
                space_index = text.find(" ", next_start)
                newline_index = text.find("\n", next_start)
                candidates = [i for i in (space_index, newline_index) if i != -1]
                next_start = min(candidates) + 1 if candidates else next_start

            start = next_start

        return chunks

    def chunk_text(self, text: str, chunk_size: Optional[int] = None, overlap: Optional[int] = None) -> List[str]:
        """Aplica el algoritmo de Segmentación Semántica Recursiva Híbrida.
        Calcula parámetros adaptativos y desciende recursivamente por separadores."""
        if not text.strip():
            return []

        # Determinar tamaños adaptativos
        dyn_p_size, dyn_p_overlap, _, _ = self.calculate_adaptive_params(text)
        size = chunk_size or dyn_p_size
        effective_overlap = overlap if overlap is not None else dyn_p_overlap

        return self.split_recursively_by_separators(text, size, effective_overlap)

    def build_chunks_from_sections(self, sections: List[Section], document_id: str) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        index = 0

        for section in sections:
            for piece in self.chunk_text(section.content):
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{document_id}-{index}",
                        document_id=document_id,
                        text=piece,
                        section_title=section.title,
                        heading_level=section.level or None,
                        page_number=section.page_number,
                    )
                )
                index += 1

        return chunks

    # ---------------------------------------------------------------------------
    # Key-concept extraction (KeyBERT)
    # ---------------------------------------------------------------------------
    def _get_keybert_model(self):
        if self._keybert_model is None:
            from keybert import KeyBERT
            logger.info("Cargando modelo KeyBERT para extracción de conceptos clave.")
            self._keybert_model = KeyBERT(model="all-MiniLM-L6-v2")
        return self._keybert_model

    def _extract_key_concepts(self, text: str) -> List[str]:
        if not settings.USE_KEYBERT_CONCEPTS or len(text) <= 50:
            return []

        try:
            model = self._get_keybert_model()
            keywords = model.extract_keywords(
                text, keyphrase_ngram_range=(1, 2), stop_words=None, top_n=4
            )
            return [kw[0] for kw in keywords]
        except Exception as exc:
            logger.warning("Extracción de conceptos clave falló: %s", exc)
            return []

    # ---------------------------------------------------------------------------
    # Parent/child RAG structure
    # ---------------------------------------------------------------------------
    def build_rag_chunks(self, document: IngestedDocument) -> Dict[str, Any]:
        parent_chunks: List[Dict[str, Any]] = []
        child_chunks: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(document.chunks):
            parent_id = f"parent_{idx}"
            section_title = chunk.section_title or f"Sección {idx + 1}"

            parent = ParentChunk(
                id=parent_id,
                title=section_title,
                breadcrumb=f"{document.title} > {section_title}",
                content=chunk.text,
                metadata=ParentChunkMetadata(
                    source_title=document.title,
                    section_index=idx,
                    page_number=chunk.page_number,
                    heading_level=chunk.heading_level,
                    key_concepts=self._extract_key_concepts(chunk.text),
                ),
            )
            parent_chunks.append(parent.model_dump())

            # Adaptación dinámicas para los Child Chunks
            _, _, dyn_c_size, dyn_c_overlap = self.calculate_adaptive_params(chunk.text)
            c_size = self.child_chunk_size or dyn_c_size
            c_overlap = self.child_overlap or dyn_c_overlap

            child_pieces = (
                [chunk.text]
                if len(chunk.text) <= c_size
                else self.split_recursively_by_separators(
                    chunk.text,
                    target_size=c_size,
                    overlap=c_overlap,
                )
            )

            for child_idx, child_text in enumerate(child_pieces):
                child = ChildChunk(
                    id=f"{parent_id}_child_{child_idx}",
                    parent_id=parent_id,
                    breadcrumb=f"[{document.title} > {section_title}]",
                    content=child_text,
                    metadata=ChildChunkMetadata(
                        parent_id=parent_id,
                        source=document.title,
                    ),
                )
                child_chunks.append(child.model_dump())

        return {
            "title": document.title,
            "parent_chunks": parent_chunks,
            "child_chunks": child_chunks,
            "total_parents": len(parent_chunks),
            "total_children": len(child_children) if 'child_children' in locals() else len(child_chunks),
        }

    # ---------------------------------------------------------------------------
    # Main entry points
    # ---------------------------------------------------------------------------
    def process_document(
        self,
        filepath: Union[str, Path],
        title: Optional[str] = None,
        options: Optional[IngestionOptions] = None,
        document_id: Optional[str] = None,
    ) -> IngestedDocument:
        path = Path(filepath)
        options = options or IngestionOptions()
        document_id = document_id or str(uuid.uuid4())

        raw_text = self.load_file(path, options)
        sections = self.detect_sections(raw_text, path.suffix.lower())
        chunks = self.build_chunks_from_sections(sections, document_id)

        return IngestedDocument(
            document_id=document_id,
            title=title or path.stem,
            source_filename=path.name,
            raw_text=raw_text,
            chunks=chunks,
        )

    def process_text(self, content: str, title: str) -> IngestedDocument:
        document_id = str(uuid.uuid4())
        sections = self.detect_sections(content, ".txt")
        chunks = self.build_chunks_from_sections(sections, document_id)

        return IngestedDocument(
            document_id=document_id,
            title=title,
            source_filename="inline_text",
            raw_text=content,
            chunks=chunks,
        )

    def parse_and_chunk_document(self, content: str, title: str) -> Dict[str, Any]:
        doc = self.process_text(content=content, title=title)
        return self.build_rag_chunks(doc)