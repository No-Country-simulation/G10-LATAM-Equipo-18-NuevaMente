"""
run_parameter_variation_matrix.py

Purpose:
    Fast CLI test to inspect agent outputs across varying generation parameters:
    1. Output Formats (Flashcards, Quiz, Tutorial, Resumen Ejecutivo, Guion de Clase).
    2. Recipient Profiles (Principiante, Desarrollador, Líder Técnico, Ejecutivo).
    3. Niches (Fintech, Salud, E-commerce, General).
    4. Quantity Levels (Breve, Estandar, Amplio).

Inputs:
    None (uses structured technical sample document).

Outputs:
    Prints structured matrix of decisions, LLM provider selected, effective item count,
    and first generated item to verify content adaptation without launching any UI.
"""

import asyncio
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.adaptation import AdaptationRequest
from app.services.agent_orchestrator import AgentOrchestrator

SAMPLE_DOC = """
Microservicios y Arquitecturas Basadas en Eventos:
Una arquitectura de microservicios divide una aplicación en servicios autónomos e independientes.
La comunicación entre microservicios puede ser sincrónica (REST HTTP, gRPC) o asincrónica basada en eventos (Apache Kafka, RabbitMQ).
En entornos financieros (Fintech), el uso de Event Sourcing y CQRS garantiza auditoría transaccional estricta y cumplimiento PCI-DSS.
En sistemas de salud (Healthtech), la alta disponibilidad y la privacidad bajo normativa HIPAA son fundamentales.
El despliegue automatizado con contenedores Docker y orquestación con Kubernetes permite escalabilidad horizontal elástica.
"""

TEST_SCENARIOS = [
    {
        "desc": "Escenario 1: Flashcards para Principiante en Salud (Breve)",
        "perfil": "Principiante",
        "formato": "Flashcards",
        "nicho": "Salud",
        "detalle": "Didactico",
        "cantidad": "Breve",
    },
    {
        "desc": "Escenario 2: Quiz para Desarrollador en Fintech (Estandar)",
        "perfil": "Desarrollador",
        "formato": "Quiz",
        "nicho": "Fintech",
        "detalle": "Tecnico",
        "cantidad": "Estandar",
    },
    {
        "desc": "Escenario 3: Resumen Ejecutivo para Ejecutivo en E-commerce (Breve)",
        "perfil": "Ejecutivo",
        "formato": "Resumen Ejecutivo",
        "nicho": "E-commerce",
        "detalle": "Conciso",
        "cantidad": "Breve",
    },
    {
        "desc": "Escenario 4: Tutorial para Líder Técnico en General (Amplio)",
        "perfil": "Líder Técnico",
        "formato": "Tutorial",
        "nicho": "General",
        "detalle": "Exhaustivo",
        "cantidad": "Amplio",
    },
]


async def run_variation_matrix():
    print("================================================================================")
    print("   NUEVAMENTE — MATRIZ DE VARIACIÓN MULTIAGENTE Y PARÁMETROS (CLI)")
    print("================================================================================\n")

    orchestrator = AgentOrchestrator()
    top_passages = [
        {
            "id": "chunk-ms-01",
            "content": SAMPLE_DOC,
            "title": "Arquitecturas de Microservicios y Eventos",
        }
    ]
    key_concepts = ["Microservicios", "Apache Kafka", "CQRS", "PCI-DSS", "HIPAA", "Kubernetes"]

    for sc in TEST_SCENARIOS:
        print(f"▶ {sc['desc']}")
        print(f"  • Solicitud: Perfil={sc['perfil']} | Formato={sc['formato']} | Nicho={sc['nicho']} | Nivel={sc['cantidad']}")

        req = AdaptationRequest(
            documento_titulo="Arquitecturas de Microservicios",
            documento_contenido=SAMPLE_DOC,
            perfil_destinatario=sc["perfil"],
            formato_salida=sc["formato"],
            nicho_sector=sc["nicho"],
            nivel_detalle=sc["detalle"],
            nivel_cantidad=sc["cantidad"],
            forzar_regenerar=True,
        )

        resp = await orchestrator.run_pipeline(
            request=req,
            top_passages=top_passages,
            key_concepts=key_concepts,
            prerequisites=["Contenedores", "Redes"],
        )

        meta = resp.metadata
        content = resp.adapted_content
        first_item = (content.items or [{}])[0]

        print(f"  ✔ Proveedor LLM Ejecutor: [{meta.llm_provider.upper()}]")
        print(f"  ✔ Cantidad Generada: {meta.generated_items} items (Solicitados: {meta.requested_items})")
        if meta.quantity_warning:
            print(f"  ⚠ Aviso de Capacidad: {meta.quantity_warning}")

        # Show snippet of how the first item adapted to the niche/profile
        if "flashcard" in sc["formato"].lower():
            print(f"  📄 Muestra Q: {first_item.get('frente')}")
            print(f"  📄 Muestra A: {first_item.get('dorso')}")
            print(f"  💡 Pista: {first_item.get('pista_didactica')}")
        elif "quiz" in sc["formato"].lower():
            print(f"  📄 Pregunta: {first_item.get('pregunta')}")
            print(f"  ✔ Correcta: {first_item.get('respuesta_correcta')}")
            print(f"  📖 Justificación: {first_item.get('justificacion_didactica') or first_item.get('justificacion')}")
        elif "resumen" in sc["formato"].lower():
            print(f"  📄 Punto Clave: {first_item.get('punto_clave')}")
            print(f"  💼 Impacto de Negocio: {first_item.get('impacto_negocio')}")
        elif "tutorial" in sc["formato"].lower():
            print(f"  📄 Paso: {first_item.get('titulo')}")
            print(f"  🛠 Instrucción: {first_item.get('instruccion')[:120]}...")

        print("-" * 80)

    print("\n[✔] Matriz de prueba completada exitosamente.")


if __name__ == "__main__":
    asyncio.run(run_variation_matrix())
