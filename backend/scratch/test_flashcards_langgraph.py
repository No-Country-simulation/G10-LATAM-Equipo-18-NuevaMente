import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# 1. Leer el documento de prueba
doc_path = Path("tests/manual/sample_docs/manual_rag.md")
content = doc_path.read_text(encoding="utf-8")

payload = {
    "documento_titulo": "Manual Técnico Sistema NuevaMente - RAG",
    "documento_contenido": content,
    "perfil_destinatario": "Principiante",
    "formato_salida": "Flashcards",
    "nicho_sector": "General",
    "nivel_detalle": "Didactico",
    "nivel_cantidad": "Estandar",
    "cantidad_objetivo": 10,
    "forzar_regenerar": True
}

print("=" * 60)
print("🚀 ENVIANDO DOCUMENTO AL ENDPOINT /api/v1/adapt-content")
print(f"📄 Documento: {payload['documento_titulo']} ({len(content)} caracteres)")
print(f"🎯 Formato: {payload['formato_salida']} | Perfil: {payload['perfil_destinatario']}")
print("=" * 60)

start_time = time.time()
response = client.post("/api/v1/adapt-content", json=payload)
elapsed = time.time() - start_time

if response.status_code != 200:
    print(f"❌ Error {response.status_code}: {response.text}")
    exit(1)

data = response.json()

print(f"\n✅ RESPUESTA EXITOSA EN {elapsed:.2f}s (HTTP {response.status_code})")
print("=" * 60)

# Metadatos del Grafo
meta = data.get("metadatos", {})
print("\n📊 METADATOS DE EJECUCIÓN DEL GRAFO (LangGraph):")
print(f"  • Orquestación por Grafo: {meta.get('orquestacion_grafo')}")
print(f"  • Nodos Ejecutados: {' ➔ '.join(meta.get('nodos_grafo_ejecutados', []))}")
print(f"  • Revisiones del Crítico: {meta.get('revisiones_grafo')}")
print(f"  • Proveedor LLM: {meta.get('proveedor_llm')} ({meta.get('modelo_llm')})")
print(f"  • Modelos Usados: {meta.get('modelos_usados')}")
print(f"  • Crítico / Auditor: {meta.get('proveedor_critico')} ({meta.get('modelo_critico')})")
print(f"  • Ítems Solicitados vs Generados: {meta.get('items_solicitados')} / {meta.get('items_generados')}")
print(f"  • Conceptos Clave Detectados: {meta.get('conceptos_clave')}")

# Evaluación de Calidad
eval_q = data.get("evaluacion_calidad", {})
print("\n🧐 EVALUACIÓN DEL CRÍTICO / AUDITOR:")
print(f"  • Score de Anclaje a Fuente (Grounding): {eval_q.get('anclaje_fuente_score') * 100:.1f}%")
print(f"  • Claridad Pedagógica: {eval_q.get('claridad_pedagogica')}")
print(f"  • Observaciones: {eval_q.get('observaciones')}")

# Almacenamiento OCI
oci = data.get("almacenamiento_oci", {})
print("\n☁️ ALMACENAMIENTO DE ARTEFACTOS (OCI / Mock):")
print(f"  • Bucket: {oci.get('bucket')}")
print(f"  • Objeto ID: {oci.get('objeto_id')}")
print(f"  • Estado: {oci.get('status_upload')}")

# Muestra de Flashcards
cont = data.get("contenido_adaptado", {})
items = cont.get("items", [])
print(f"\n🗂️ FLASHCARDS GENERADAS ({len(items)} ítems):")
for i, item in enumerate(items[:5], 1):
    print(f"\n--- [Tarjeta #{i}] ---")
    print(f"  ❓ Frente: {item.get('frente')}")
    print(f"  💡 Dorso:  {item.get('dorso')}")
    if item.get("pista_didactica"):
        print(f"  🔍 Pista:  {item.get('pista_didactica')}")
    fuentes = item.get("fuentes", [])
    if fuentes:
        fuente_ids = [f.get('chunk_id') for f in fuentes if f.get('chunk_id')]
        print(f"  🔗 Fuentes/Chunks Verificados: {fuente_ids}")

if len(items) > 5:
    print(f"\n... y {len(items) - 5} tarjetas más generadas exitosamente.")

# Guardar resultado para inspección si se desea
with open("scratch/sample_output_flashcards.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print("\n💾 Salida completa guardada en backend/scratch/sample_output_flashcards.json")
