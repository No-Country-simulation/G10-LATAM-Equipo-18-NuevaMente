"""
ingester_service.py

Purpose:
    Robust document ingestion and layout-aware chunking service.
    Loads and processes technical documents (PDF, Markdown, Plain Text),
    removes header/footer noise, extracts section structure, and produces
    both flat document chunks and Parent-Child hierarchical data for the
    RAG pipeline. Also accepts raw text directly (no file), for requests
    that send document content inline instead of uploading a file.

Input:
    A file path (process_document) or raw text (process_text), plus
    optional IngestionOptions.

Output:
    An IngestedDocument. Call build_rag_chunks() on that result to get
    the parent/child structure the RAG retrieval layer expects.
"""

import re
import uuid
import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from pypdf import PdfReader
from app.core.config import settings
from app.schemas.ingestion import IngestedDocument, DocumentChunk, IngestionOptions


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
    ):
        # Both sizes are measured in characters, same unit as chunk_text(),
        # so parent and child chunks are produced with identical splitting
        # quality — only the target size differs.
        self.child_chunk_size = child_chunk_size
        self.parent_chunk_size = parent_chunk_size
        self.overlap = overlap

    # ---------------------------------------------------------------------------
    # File validation
    # ---------------------------------------------------------------------------
    @staticmethod
    def validate_file(filepath: Path) -> None:
        """Validates extension and file size."""
        extension = filepath.suffix.lower()
        if extension not in settings.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {extension}. "
                f"Supported types: {settings.SUPPORTED_EXTENSIONS}"
            )

        size_mb = filepath.stat().st_size / (1024 * 1024)
        if size_mb > settings.MAX_FILE_SIZE_MB:
            raise ValueError(
                f"File too large: {size_mb:.1f}MB. Limit is {settings.MAX_FILE_SIZE_MB}MB."
            )

    # ---------------------------------------------------------------------------
    # Noise removal (repeated headers/footers in PDFs)
    # ---------------------------------------------------------------------------
    @staticmethod
    def remove_repeated_lines(pages_text: List[str], min_repetition_ratio: float = 0.4) -> List[str]:
        """Detects and strips boilerplate lines repeating across multiple pages."""
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
    def extract_text_from_pdf(self, filepath: Path) -> str:
        """Extracts text from PDF, preferentially using PdfParserService (pymupdf4llm) for Markdown structure."""
        from app.services.pdf_parser_service import PdfParserService # noqa: PLC0415
        
        pdf_parser = PdfParserService()
        if pdf_parser.is_available:
            return pdf_parser.parse_pdf_to_markdown(str(filepath))
            
        # Legacy fallback
        from pypdf import PdfReader # noqa: PLC0415
        reader = PdfReader(str(filepath))
        pages_text = [page.extract_text() or "" for page in reader.pages]
        cleaned_pages = self.remove_repeated_lines(pages_text)

        pages_with_metadata = [
            f"\n[PÁGINA {i + 1}]\n{page_str}"
            for i, page_str in enumerate(cleaned_pages) if page_str.strip()
        ]
        return "\n".join(pages_with_metadata)

    @staticmethod
    def extract_text_from_markdown(filepath: Path) -> str:
        return filepath.read_text(encoding="utf-8")

    @staticmethod
    def extract_text_from_txt(filepath: Path) -> str:
        return filepath.read_text(encoding="utf-8")

    def load_file(self, filepath: Path, options: Optional[IngestionOptions] = None) -> str:
        """Validates and extracts raw text from the given file."""
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
                raise ValueError(f"No extractor registered for {extension}")
        except Exception as error:
            raise ValueError(f"Failed to read {filepath.name}: {error}") from error

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
                # Extraído vía pymupdf4llm (Markdown)
                return self.parse_markdown_sections(text)
        elif extension in (".md", ".markdown"):
            return self.parse_markdown_sections(text)
        elif extension == ".txt":
            return self.parse_txt_sections_heuristic(text)
        return [Section(title=None, level=0, content=text)]

    # ---------------------------------------------------------------------------
    # Paragraph-aware chunking
    # ---------------------------------------------------------------------------
    @staticmethod
    def split_into_paragraphs(text: str) -> List[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        return [p.strip() for p in paragraphs if p.strip()]

    @staticmethod
    def split_by_characters(text: str, chunk_size: int, overlap: int) -> List[str]:
        """Sliding window fallback for a single paragraph longer than
        chunk_size. Both ends of every piece are aligned to the nearest
        whitespace so a piece never begins or ends mid-word."""
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

    def chunk_text(self, text: str, chunk_size: Optional[int] = None) -> List[str]:
        """Groups paragraphs into pieces up to chunk_size, keeping paragraph
        boundaries intact. Defaults to parent_chunk_size, but accepts a
        different size so the same, already-validated splitting logic can
        also produce child chunks — instead of a separate, cruder pass."""
        size = chunk_size or self.parent_chunk_size

        if not text.strip():
            return []

        paragraphs = self.split_into_paragraphs(text)
        chunks: List[str] = []
        current_chunk = ""

        for paragraph in paragraphs:
            if len(paragraph) > size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                chunks.extend(self.split_by_characters(paragraph, size, self.overlap))
                continue

            candidate = f"{current_chunk}\n\n{paragraph}".strip() if current_chunk else paragraph
            if len(candidate) <= size:
                current_chunk = candidate
            else:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def build_chunks_from_sections(self, sections: List[Section], document_id: str) -> List[DocumentChunk]:
        """Builds the flat (parent-level) chunk list from detected sections."""
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
    # Parent/child RAG structure
    # ---------------------------------------------------------------------------
    def build_rag_chunks(self, document: IngestedDocument) -> Dict[str, Any]:
        """Takes an already-ingested document and produces the parent/child
        structure the retrieval layer expects."""
        
        # Inicializar KeyBERT para extraer conceptos gratis y rápido
        try:
            from keybert import KeyBERT
            import logging
            logging.getLogger().info("Cargando modelo KeyBERT ligero...")
            kw_model = KeyBERT(model="all-MiniLM-L6-v2")
        except ImportError:
            kw_model = None
        parent_chunks: List[Dict[str, Any]] = []
        child_chunks: List[Dict[str, Any]] = []

        for idx, chunk in enumerate(document.chunks):
            parent_id = f"parent_{idx}"
            section_title = chunk.section_title or f"Sección {idx + 1}"

            # Extracción de Conceptos Clave en Tiempo de Ingesta (Costo 0 de API)
            key_concepts = []
            if kw_model and len(chunk.text) > 50:
                # Extraemos 4 frases/palabras clave en inglés o español
                keywords = kw_model.extract_keywords(chunk.text, keyphrase_ngram_range=(1, 2), stop_words=None, top_n=4)
                key_concepts = [kw[0] for kw in keywords]

            parent_chunks.append({
                "id": parent_id,
                "title": section_title,
                "breadcrumb": f"{document.title} > {section_title}",
                "content": chunk.text,
                "metadata": {
                    "source_title": document.title,
                    "section_index": idx,
                    "page_number": chunk.page_number,
                    "heading_level": chunk.heading_level,
                    "key_concepts": key_concepts,
                },
            })

            child_pieces = (
                [chunk.text]
                if len(chunk.text) <= self.child_chunk_size
                else self.chunk_text(chunk.text, chunk_size=self.child_chunk_size)
            )

            for child_idx, child_text in enumerate(child_pieces):
                child_chunks.append({
                    "id": f"{parent_id}_child_{child_idx}",
                    "parent_id": parent_id,
                    "breadcrumb": f"[{document.title} > {section_title}]",
                    "content": child_text,
                    "metadata": {
                        "parent_id": parent_id,
                        "source": document.title,
                    },
                })

        return {
            "title": document.title,
            "parent_chunks": parent_chunks,
            "child_chunks": child_chunks,
            "total_parents": len(parent_chunks),
            "total_children": len(child_chunks),
        }

    # ---------------------------------------------------------------------------
    # Main entry points
    # ---------------------------------------------------------------------------
    def process_document(
        self,
        filepath: Union[str, Path],
        title: Optional[str] = None,
        options: Optional[IngestionOptions] = None,
    ) -> IngestedDocument:
        """Processes a file path into an IngestedDocument."""
        path = Path(filepath)
        options = options or IngestionOptions()
        document_id = str(uuid.uuid4())

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
        """Processes raw text sent inline (e.g. a JSON request body with
        content, no file upload) the same way process_document()
        handles a file. No file extension is available, so section
        detection uses the TXT heuristic."""
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
        """Backward-compatible adapter that processes raw text and produces
        the parent/child RAG structure expected by HybridRAGService."""
        doc = self.process_text(content=content, title=title)
        return self.build_rag_chunks(doc)