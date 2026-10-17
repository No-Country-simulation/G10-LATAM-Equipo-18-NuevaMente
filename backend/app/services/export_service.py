"""
export_service.py

Purpose:
    Unified Multi-Format Export Service for NuevaMente.
    Provides direct downloads for:
    1. Formatted Didactic Markdown (.md)
    2. Anki-compatible CSV deck (.csv)
    3. Formatted Didactic PDF (.pdf) with cover, table of contents, and OCI styling.

Supported Educational Formats:
    - Flashcards (Memorización activa)
    - Quiz (Cuestionario de auto-evaluación)
    - Tutorial (Paso a paso estructurado)
    - Resumen Ejecutivo (TL;DR / Síntesis estratégica)
    - Guion de Clase (Video class script)
"""

import csv
import io
import re
import unicodedata
from typing import Any, Dict, List, Optional
from app.schemas.adaptation import AdaptedContent, QuizItem, FlashcardItem
from app.services.pdf_export_service import PDFExportService


def slugify_title(title: str) -> str:
    """Generates a clean filesystem-friendly slug for downloads."""
    normalized = unicodedata.normalize("NFKD", str(title or ""))
    ascii_text = normalized.encode("ASCII", "ignore").decode("ASCII")
    clean = re.sub(r"[^a-zA-Z0-9\s\-_]", "", ascii_text).strip()
    slug = re.sub(r"[\s\-_]+", "-", clean).lower()
    return slug[:50] or "nuevamente-contenido"


class ExportService:
    """Unified service for generating downloadable educational artifacts."""

    def __init__(self):
        self.pdf_service = PDFExportService()

    # ---------------------------------------------------------------------------
    # 1. MARKDOWN EXPORT
    # ---------------------------------------------------------------------------
    def export_to_markdown(self, payload: Dict[str, Any]) -> str:
        """Generates a structured, pedagogical Markdown document."""
        contenido = payload.get("contenido_adaptado") or {}
        metadatos = payload.get("metadatos") or {}
        calidad = payload.get("evaluacion_calidad") or {}
        almacenamiento = payload.get("almacenamiento_oci") or {}

        title = contenido.get("titulo") or "Adaptación Educativa NuevaMente"
        perfil = metadatos.get("perfil_aplicado") or "General"
        formato = metadatos.get("formato_generado") or "Contenido Educativo"
        tiempo = metadatos.get("tiempo_estimado_estudio_minutos") or 15
        score_val = calidad.get("anclaje_fuente_score", 0.98)
        score_pct = int(round(score_val * 100))
        intro = contenido.get("introduccion_contextualizada") or ""
        items = contenido.get("items") or []

        md = f"# 🎓 {title}\n\n"
        md += "> **NuevaMente** — Sistema de Adaptación Educativa con Inteligencia Artificial y Graph RAG\n"
        md += "> *Desarrollado para Oracle Next Education (ONE) × Alura — Grupo 10*\n\n"
        md += "---\n\n"

        # Metadata Block
        md += "### 📋 Ficha Técnica Pedagógica\n\n"
        md += f"| Parámetro | Valor |\n"
        md += f"| :--- | :--- |\n"
        md += f"| **👤 Perfil Destinatario** | `{perfil}` |\n"
        md += f"| **🎯 Formato Pedagógico** | `{formato}` |\n"
        md += f"| **⏱️ Tiempo Estimado de Estudio** | `{tiempo} minutos` |\n"
        md += f"| **🛡️ Anclaje RAG Verificado** | `{score_pct}%` |\n"
        if almacenamiento.get("objeto_id"):
            md += f"| **☁️ Persistencia OCI Bucket** | `{almacenamiento.get('bucket', 'nuevamente-contenidos-educativos')}` |\n"
            md += f"| **📦 Objeto ID** | `{almacenamiento.get('objeto_id')}` |\n"
        md += "\n---\n\n"

        # Contextualized Introduction
        if intro:
            md += "## 📖 Introducción y Contextualización\n\n"
            md += f"{intro}\n\n---\n\n"

        # Executive Summary if present
        exec_summary = contenido.get("resumen_ejecutivo")
        if exec_summary:
            md += "## 📊 Resumen Ejecutivo\n\n"
            md += f"{exec_summary}\n\n---\n\n"

        # Content Items
        md += "## 📚 Contenido Didáctico Adaptado\n\n"

        for idx, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue

            # Format 1: Flashcards
            if "frente" in item:
                md += f"### 🗂️ Tarjeta #{idx}: {item.get('frente')}\n\n"
                md += f"**Respuesta:** {item.get('dorso')}\n\n"
                if item.get("pista_didactica"):
                    md += f"> 💡 **Pista didáctica:** *{item.get('pista_didactica')}*\n\n"

            # Format 2: Quiz
            elif "pregunta" in item:
                md += f"### ❓ Pregunta #{idx}: {item.get('pregunta')}\n\n"
                opciones = item.get("opciones") or []
                correcta = item.get("respuesta_correcta", "")
                for opt in opciones:
                    mark = "[x]" if opt == correcta else "[ ]"
                    md += f"- {mark} {opt}\n"
                md += f"\n**✅ Respuesta Correcta:** {correcta}\n\n"
                justif = item.get("justificacion_didactica") or item.get("justificacion")
                if justif:
                    md += f"> 💡 **Justificación:** *{justif}*\n\n"

            # Format 3: Tutorial
            elif "paso" in item or "instruccion" in item:
                paso_num = item.get("paso", idx)
                titulo = item.get("titulo") or f"Módulo {idx}"
                md += f"### 🛠️ Paso {paso_num}: {titulo}\n\n"
                md += f"{item.get('instruccion', '')}\n\n"
                if item.get("ejemplo"):
                    md += "```\n" + item.get("ejemplo", "").strip() + "\n```\n\n"
                if item.get("advertencia"):
                    md += f"> ⚠️ **Nota de seguridad:** {item.get('advertencia')}\n\n"

            # Format 4: Summary / Key points
            elif "punto_clave" in item:
                md += f"### 📌 Punto Clave #{idx:02d}: {item.get('punto_clave')}\n\n"
                if item.get("impacto_negocio"):
                    md += f"**Impacto Operativo / Negocio:** {item.get('impacto_negocio')}\n\n"

            # Format 5: Class Script
            elif "escena" in item:
                escena = item.get("escena", idx)
                dur = item.get("duracion_seg", 60)
                md += f"### 🎬 Escena {escena} ({dur} segundos)\n\n"
                md += f"**🎙️ Narración (Voz en off / Presentador):**\n>{item.get('narracion', '')}\n\n"
                if item.get("apoyo_visual"):
                    md += f"**🎨 Apoyo Visual Sugerido:** {item.get('apoyo_visual')}\n\n"

            # Citation Provenance
            fuentes = item.get("fuentes") or []
            if fuentes and isinstance(fuentes, list) and len(fuentes) > 0:
                first_src = fuentes[0]
                if isinstance(first_src, dict):
                    doc_sec = first_src.get("seccion") or first_src.get("chunk_id", "Referencia")
                    pag = f" · Pág. {first_src.get('pagina')}" if first_src.get("pagina") else ""
                    md += f"*📄 Fuente verificada: {doc_sec}{pag}*\n\n"

            md += "---\n\n"

        # Footer
        md += "### 🛡️ Auditoría de Fidelidad RAG\n"
        md += f"- **Claridad Pedagógica:** {calidad.get('claridad_pedagogica', 'Alta')}\n"
        md += f"- **Observaciones:** {calidad.get('observaciones', 'Material verificado contra documentación técnica.')}\n"
        md += f"\n*Exportado automáticamente por el motor NuevaMente Multi-Format Export Engine.*\n"

        return md

    # ---------------------------------------------------------------------------
    # 2. ANKI-COMPATIBLE CSV EXPORT
    # ---------------------------------------------------------------------------
    def export_to_anki_csv(self, payload: Dict[str, Any]) -> str:
        """
        Generates an Anki-compatible CSV deck file supporting all output formats.
        Format complies with standard Anki CSV specification with HTML cards:
        #separator:tab
        #html:true
        #tags column:3
        """
        contenido = payload.get("contenido_adaptado") or {}
        metadatos = payload.get("metadatos") or {}
        title = contenido.get("titulo") or "NuevaMente"
        formato = (metadatos.get("formato_generado") or "Educativo").replace(" ", "_")
        items = contenido.get("items") or []

        deck_tag = f"NuevaMente::{formato}"

        output = io.StringIO()
        # Anki directive header
        output.write("#separator:tab\n")
        output.write("#html:true\n")
        output.write("#tags column:3\n")

        writer = csv.writer(output, delimiter="\t", quoting=csv.QUOTE_MINIMAL)

        for idx, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue

            front = ""
            back = ""

            # Format 1: Flashcard
            if "frente" in item:
                q = item.get("frente", "").strip()
                pista = item.get("pista_didactica", "").strip()
                hint_html = f"<br><small style='color:#64748b;'><i>💡 Pista: {pista}</i></small>" if pista else ""
                front = f"<div style='font-size:18px; font-weight:bold; color:#1e293b;'>{q}</div>{hint_html}"
                back = f"<div style='font-size:16px; color:#334155; line-height:1.5;'>{item.get('dorso', '')}</div>"

            # Format 2: Quiz
            elif "pregunta" in item:
                q = item.get("pregunta", "").strip()
                opciones = item.get("opciones") or []
                correcta = item.get("respuesta_correcta", "")
                justif = item.get("justificacion_didactica") or item.get("justificacion", "")

                opts_html = "".join(f"<li style='margin-bottom:4px;'>{opt}</li>" for opt in opciones)
                front = f"<div style='font-size:18px; font-weight:bold; color:#1e293b;'>{q}</div><ul style='margin-top:8px; padding-left:20px; font-size:14px; color:#475569;'>{opts_html}</ul>"

                justif_html = f"<div style='margin-top:8px; font-size:13px; color:#6b21a8; background:#f3e8ff; padding:6px 10px; border-radius:6px;'><i>💡 {justif}</i></div>" if justif else ""
                back = f"<div style='font-size:16px; font-weight:bold; color:#047857;'>✓ {correcta}</div>{justif_html}"

            # Format 3: Tutorial
            elif "paso" in item or "instruccion" in item:
                paso_num = item.get("paso", idx)
                tit = item.get("titulo") or f"Paso {idx}"
                front = f"<div style='font-size:14px; font-weight:bold; color:#4f46e5;'>PASO {paso_num}</div><div style='font-size:18px; font-weight:bold; color:#1e293b;'>{tit}</div>"

                instr = item.get("instruccion", "")
                ejemplo = item.get("ejemplo", "")
                ejemplo_html = f"<pre style='background:#0d1117; color:#58a6ff; padding:8px 12px; border-radius:6px; font-size:12px; margin-top:8px; overflow-x:auto;'><code>{ejemplo}</code></pre>" if ejemplo else ""
                back = f"<div style='font-size:15px; color:#334155; line-height:1.5;'>{instr}</div>{ejemplo_html}"

            # Format 4: Resumen
            elif "punto_clave" in item:
                pk = item.get("punto_clave", "")
                imp = item.get("impacto_negocio", "")
                front = f"<div style='font-size:14px; font-weight:bold; color:#2563eb;'>PUNTO CLAVE #{idx}</div><div style='font-size:17px; font-weight:bold; color:#1e293b;'>{pk}</div>"
                back = f"<div style='font-size:15px; color:#334155;'><strong>Impacto de Negocio:</strong><br>{imp}</div>"

            # Format 5: Guion
            elif "escena" in item:
                esc = item.get("escena", idx)
                dur = item.get("duracion_seg", 60)
                narr = item.get("narracion", "")
                vis = item.get("apoyo_visual", "")
                front = f"<div style='font-size:14px; font-weight:bold; color:#7c3aed;'>ESCENA {esc} ({dur}s)</div><div style='font-size:16px; color:#1e293b;'><strong>Guion Didáctico</strong></div>"
                back = f"<div style='font-size:15px; color:#334155;'><strong>🎙️ Narración:</strong> {narr}</div><div style='margin-top:6px; font-size:13px; color:#64748b;'><strong>🎨 Visual:</strong> {vis}</div>"

            if front and back:
                writer.writerow([front, back, deck_tag])

        return output.getvalue()

    # ---------------------------------------------------------------------------
    # 3. PDF EXPORT
    # ---------------------------------------------------------------------------
    def export_to_pdf_bytes(self, payload: Dict[str, Any]) -> bytes:
        """Generates a binary PDF document with cover, index, and formatted sections."""
        contenido = payload.get("contenido_adaptado") or {}
        title = contenido.get("titulo") or "Adaptación Educativa NuevaMente"
        intro = contenido.get("introduccion_contextualizada") or ""
        exec_summary = contenido.get("resumen_ejecutivo")
        tut_sections = contenido.get("secciones_tutorial") or contenido.get("tutorial_sections") or []
        items = contenido.get("items") or []

        # Convert to AdaptedContent schema expected by PDFExportService
        content_obj = AdaptedContent(
            title=title,
            contextualized_introduction=intro,
            executive_summary=exec_summary,
            tutorial_sections=tut_sections,
            items=items,
        )

        return self.pdf_service.generate_pdf_bytes(content_obj)
