import os
from app.schemas.adaptation import AdaptedContent, FlashcardItem, QuizItem
from app.services.pdf_export_service import PDFExportService

def test_generate_pdf():
    # Creamos contenido de prueba (Mock)
    content = AdaptedContent(
        titulo="Dominando Redes en la Nube (VCN) desde Cero",
        introduccion_contextualizada="Imagina la VCN como tu propio barrio privado y seguro dentro de la nube de Oracle, donde tú decides quién entra y quién sale.",
        resumen_ejecutivo="La VCN es la base de toda red en OCI. Permite aislar recursos, conectar con redes on-premise y asegurar el tráfico.",
        items=[
            FlashcardItem(
                frente="¿Qué es una VCN en Oracle Cloud?",
                dorso="Es tu red virtual privada y personalizada dentro de la nube de Oracle.",
                pista_didactica="Piensa en ella como el terreno cercado donde residen tus servidores."
            ),
            FlashcardItem(
                frente="¿Para qué sirven las Security Lists?",
                dorso="Son como guardias virtuales con listas de reglas que definen el tráfico permitido.",
                pista_didactica="Reglas de entrada (ingress) y reglas de salida (egress)."
            )
        ],
        quizzes=[
            QuizItem(
                pregunta="¿Cuál es el componente principal para conectar una VCN a Internet?",
                opciones=["Internet Gateway", "NAT Gateway", "Local Peering Gateway", "Dynamic Routing Gateway"],
                respuesta_correcta="Internet Gateway",
                justificacion_didactica="El Internet Gateway es el enrutador virtual que permite que el tráfico pase de una subred pública hacia Internet."
            )
        ]
    )

    # Inicializamos el servicio y generamos el PDF
    exporter = PDFExportService()
    output_filename = "resultado_ejemplo.pdf"
    
    # Generar
    exporter.generate_pdf(content, output_filename)
    
    print(f"✅ ¡Prueba exitosa! Revisa el archivo: {os.path.abspath(output_filename)}")

if __name__ == "__main__":
    test_generate_pdf()
