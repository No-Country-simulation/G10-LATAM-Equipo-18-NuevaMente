from __future__ import annotations
from typing import Optional
from fpdf import FPDF
from pathlib import Path
import logging
from app.schemas.adaptation import AdaptedContent
from app.services.summary_composer import (
    compose_summary_paragraphs,
    is_summary_content,
    paragraphs_from_legacy_text,
    split_summary_text,
)

logger = logging.getLogger("pdf_export_service")

class EducationalPDF(FPDF):
    def __init__(self, title: str):
        super().__init__()
        self.doc_title = title
        
        # Agregamos color de fondo a todo el PDF (opcional, o podemos dejarlo en header)
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        # Evitar encabezado en la portada
        if self.page_no() == 1:
            return
        # Header simple en el resto de páginas
        self.set_font("helvetica", "B", 10)
        self.set_text_color(100, 100, 100) # Gris
        self.cell(0, 10, self.doc_title, align="R")
        self.ln(10)

    def footer(self):
        # Evitar footer en portada
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

class PDFExportService:
    """
    Servicio para exportar el contenido generado a un PDF didáctico formateado
    con carátula, índice y colores, cumpliendo el requisito diferencial de exportación.
    """
    def __init__(self):
        self.color_primary = (41, 128, 185) # Azul OCI/Tech
        self.color_secondary = (52, 73, 94) # Gris oscuro
        self.color_accent = (231, 76, 60) # Rojo sutil para alertas/hints

    @staticmethod
    def _safe_text(text: Optional[str]) -> str:
        if not text:
            return ""
        t = (
            str(text)
            .replace("“", '"')
            .replace("”", '"')
            .replace("‘", "'")
            .replace("’", "'")
            .replace("—", "-")
            .replace("–", "-")
            .replace("…", "...")
            .replace("✓", "[OK]")
            .replace("⚠️", "[!]")
            .replace("💡", "[*]")
            .replace("📄", "")
            .replace("☁️", "")
            .replace("🛡️", "")
            .replace("👤", "")
            .replace("🎯", "")
            .replace("⏱️", "")
            .replace("🖨️", "")
        )
        return t.encode("latin-1", "replace").decode("latin-1")

    def generate_pdf(self, content: AdaptedContent, output_path: str):
        try:
            pdf = EducationalPDF(title=self._safe_text(content.title))
            pdf.add_page()
            
            self._create_cover(pdf, self._safe_text(content.title))
            if self._is_summary(content):
                # Executive summaries are exported as one continuous flow of
                # paragraphs: no index, no numbered sections, no item cards.
                self._create_summary_flow(pdf, content)
            else:
                self._create_index(pdf, content)
                self._create_content_pages(pdf, content)
            
            pdf.output(output_path)
            logger.info("PDF generated successfully at: %s", output_path)
            return output_path
        except Exception as e:
            logger.error("Error generating PDF: %s", e)
            raise

    def generate_pdf_bytes(self, content: AdaptedContent) -> bytes:
        try:
            pdf = EducationalPDF(title=self._safe_text(content.title))
            pdf.add_page()
            
            self._create_cover(pdf, self._safe_text(content.title))
            if self._is_summary(content):
                self._create_summary_flow(pdf, content)
            else:
                self._create_index(pdf, content)
                self._create_content_pages(pdf, content)
            
            out = pdf.output()
            return bytes(out)
        except Exception as e:
            logger.error("Error generating PDF bytes: %s", e)
            raise

    @staticmethod
    def _is_summary(content: AdaptedContent) -> bool:
        """True when the content is an executive summary (punto_clave blocks)."""
        return is_summary_content(content.items or [])

    @staticmethod
    def _summary_paragraphs(content: AdaptedContent) -> list:
        """Summary body as paragraphs, built from items or from legacy stored text."""
        stored = (content.executive_summary or "").strip()
        if stored:
            # The stored summary is the canonical text: it already carries the
            # reference numbers and ends with the reference list.
            body, references = split_summary_text(stored)
            return body + references
        paragraphs = compose_summary_paragraphs(content.items or [])
        if paragraphs:
            return paragraphs
        return paragraphs_from_legacy_text(content.executive_summary or "")

    def _create_summary_flow(self, pdf: EducationalPDF, content: AdaptedContent):
        """Render the executive summary as a single document of flowing paragraphs."""
        pdf.add_page()

        paragraphs = self._summary_paragraphs(content)
        if content.contextualized_introduction:
            self._add_body_text(pdf, self._safe_text(content.contextualized_introduction))
            pdf.ln(4)
        for paragraph in paragraphs:
            self._add_body_text(pdf, self._safe_text(paragraph))
            pdf.ln(4)

    def _create_cover(self, pdf: EducationalPDF, title: str):
        # Fondo de carátula
        pdf.set_fill_color(*self.color_primary)
        pdf.rect(0, 0, 210, 297, "F")
        
        pdf.set_y(100)
        pdf.set_font("helvetica", "B", 24)
        pdf.set_text_color(255, 255, 255) # Blanco
        pdf.multi_cell(0, 15, title.upper(), align="C", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_y(140)
        pdf.set_font("helvetica", "I", 14)
        pdf.multi_cell(0, 10, "Generado por NuevaMente AI", align="C", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_y(250)
        pdf.set_font("helvetica", "", 10)
        pdf.cell(0, 10, "Hackathon ONE - G10 LATAM", align="C")
        
    def _create_index(self, pdf: EducationalPDF, content: AdaptedContent):
        pdf.add_page()
        pdf.set_font("helvetica", "B", 18)
        pdf.set_text_color(*self.color_primary)
        pdf.cell(0, 15, "Índice de Contenidos", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)
        
        pdf.set_font("helvetica", "", 12)
        pdf.set_text_color(*self.color_secondary)
        
        index_items = ["1. Introducción"]
        
        if content.executive_summary:
            index_items.append("2. Resumen Ejecutivo")
        
        if content.tutorial_sections:
            index_items.append("3. Secciones del Tutorial")
            
        if content.items: # Flashcards
            index_items.append("4. Tarjetas de Memorización (Flashcards)")
            
        if content.quizzes:
            index_items.append("5. Cuestionario Interactivo (Quiz)")
            
        for item in index_items:
            pdf.cell(0, 10, item, new_x="LMARGIN", new_y="NEXT")
            
        pdf.ln(10)

    def _create_content_pages(self, pdf: EducationalPDF, content: AdaptedContent):
        # 1. Introducción
        pdf.add_page()
        self._add_section_title(pdf, "1. Introducción")
        self._add_body_text(pdf, content.contextualized_introduction)
        
        # 2. Resumen (Si existe)
        if content.executive_summary:
            pdf.ln(10)
            self._add_section_title(pdf, "2. Resumen Ejecutivo")
            self._add_body_text(pdf, content.executive_summary)
            
        # 3. Tutoriales
        if content.tutorial_sections:
            pdf.add_page()
            self._add_section_title(pdf, "3. Secciones del Tutorial")
            for idx, section in enumerate(content.tutorial_sections, 1):
                pdf.set_font("helvetica", "B", 14)
                pdf.set_text_color(*self.color_secondary)
                if isinstance(section, dict):
                    sec_title = section.get('encabezado') or section.get('titulo', f"Paso {idx}")
                    sec_content = section.get('contenido', '')
                else:
                    sec_title = getattr(section, 'encabezado', getattr(section, 'titulo', f"Paso {idx}"))
                    sec_content = getattr(section, 'contenido', '')
                pdf.multi_cell(0, 10, self._safe_text(sec_title), new_x="LMARGIN", new_y="NEXT")
                self._add_body_text(pdf, sec_content)
                pdf.ln(5)
                
        # 4. Items (Flashcards / Quizzes / Tutoriales / Resumen)
        if content.items:
            pdf.add_page()
            self._add_section_title(pdf, "4. Material Educativo Adaptado")
            for idx, item in enumerate(content.items, 1):
                if isinstance(item, dict):
                    frente = item.get("frente") or item.get("front") or item.get("pregunta") or item.get("question") or item.get("titulo") or item.get("punto_clave") or f"Ítem {idx}"
                    dorso = item.get("dorso") or item.get("back") or item.get("respuesta_correcta") or item.get("instruccion") or item.get("impacto_negocio") or ""
                    pista = item.get("pista_didactica") or item.get("hint") or item.get("justificacion") or ""
                else:
                    frente = getattr(item, "frente", getattr(item, "front", getattr(item, "pregunta", getattr(item, "titulo", getattr(item, "punto_clave", f"Ítem {idx}")))))
                    dorso = getattr(item, "dorso", getattr(item, "back", getattr(item, "respuesta_correcta", getattr(item, "instruccion", getattr(item, "impacto_negocio", "")))))
                    pista = getattr(item, "pista_didactica", getattr(item, "hint", getattr(item, "justificacion", "")))

                pdf.set_font("helvetica", "B", 12)
                pdf.set_fill_color(240, 248, 255)
                pdf.set_text_color(*self.color_secondary)
                pdf.multi_cell(0, 10, self._safe_text(f"#{idx}: {frente}"), fill=True, new_x="LMARGIN", new_y="NEXT")

                if dorso:
                    pdf.set_font("helvetica", "", 12)
                    pdf.multi_cell(0, 10, self._safe_text(f"{dorso}"), new_x="LMARGIN", new_y="NEXT")

                if pista:
                    pdf.set_font("helvetica", "I", 10)
                    pdf.set_text_color(*self.color_accent)
                    pdf.multi_cell(0, 8, self._safe_text(f"Pista / Justificación: {pista}"), new_x="LMARGIN", new_y="NEXT")
                pdf.ln(5)
                
        # 5. Quizzes
        if content.quizzes:
            pdf.add_page()
            self._add_section_title(pdf, "5. Cuestionario (Quiz)")
            for idx, quiz in enumerate(content.quizzes, 1):
                pdf.set_font("helvetica", "B", 12)
                pdf.set_text_color(*self.color_secondary)
                pdf.multi_cell(0, 10, self._safe_text(f"Pregunta {idx}: {quiz.question}"), new_x="LMARGIN", new_y="NEXT")
                
                pdf.set_font("helvetica", "", 11)
                for opt in quiz.options:
                    pdf.set_x(pdf.l_margin + 10)
                    pdf.multi_cell(0, 8, self._safe_text(f"- {opt}"), new_x="LMARGIN", new_y="NEXT")
                    
                pdf.set_font("helvetica", "I", 11)
                pdf.set_text_color(*self.color_primary)
                pdf.multi_cell(0, 8, self._safe_text(f"Correcta: {quiz.correct_answer}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(*self.color_secondary)
                pdf.multi_cell(0, 8, self._safe_text(f"Explicación: {quiz.didactic_justification}"), new_x="LMARGIN", new_y="NEXT")
                pdf.ln(8)

    def _add_section_title(self, pdf: EducationalPDF, text: str):
        pdf.set_font("helvetica", "B", 16)
        pdf.set_text_color(*self.color_primary)
        pdf.cell(0, 12, self._safe_text(text), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def _add_body_text(self, pdf: EducationalPDF, text: str):
        pdf.set_font("helvetica", "", 12)
        pdf.set_text_color(*self.color_secondary)
        pdf.multi_cell(0, 8, self._safe_text(text), new_x="LMARGIN", new_y="NEXT")
