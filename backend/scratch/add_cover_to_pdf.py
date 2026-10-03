from fpdf import FPDF
from pypdf import PdfReader, PdfWriter
import os

# 1. Crear PDF temporal con carátula e índice
pdf = FPDF()
pdf.add_page()
pdf.set_fill_color(41, 128, 185)
pdf.rect(0, 0, 210, 297, "F")
pdf.set_y(100)
pdf.set_font("helvetica", "B", 24)
pdf.set_text_color(255, 255, 255)
pdf.multi_cell(0, 15, "MANUAL TECNICO:\nSISTEMA NUEVAMENTE", align="C", new_x="LMARGIN", new_y="NEXT")

# Índice
pdf.add_page()
pdf.set_font("helvetica", "B", 18)
pdf.set_text_color(0, 0, 0)
pdf.cell(0, 15, "Indice de Contenidos", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("helvetica", "", 12)
for i, section in enumerate(["1. Introduccion", "2. Que es RAG?", "3. Ingesta y Chunking", "4. Embeddings y Vector Store", "5. Casos de Uso", "6. Metricas"]):
    pdf.cell(0, 10, section, new_x="LMARGIN", new_y="NEXT")

temp_pdf = "scratch/temp_cover.pdf"
pdf.output(temp_pdf)

# 2. Unir PDF temporal con el original
original_pdf = "tests/manual/sample_docs/Nueva Mente.pdf"
output_pdf = "tests/manual/sample_docs/Nueva Mente_modificado.pdf"

writer = PdfWriter()

# Añadir portada e índice
reader_cover = PdfReader(temp_pdf)
for page in reader_cover.pages:
    writer.add_page(page)

# Añadir contenido original
if os.path.exists(original_pdf):
    reader_orig = PdfReader(original_pdf)
    for page in reader_orig.pages:
        writer.add_page(page)
    
    with open(original_pdf, "wb") as fp:
        writer.write(fp)
    print("PDF original modificado exitosamente con carátula e índice.")
else:
    print(f"No se encontró el archivo original: {original_pdf}")

