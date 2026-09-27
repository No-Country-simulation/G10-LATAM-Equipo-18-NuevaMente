# Módulo de Ingestión y Chunking — NuevaMente

Este documento describe la arquitectura, funcionamiento e instrucciones de uso del módulo de carga, limpieza y segmentación de documentos técnicos en NuevaMente.

---

## 1. Explicación para Principiantes: ¿Cómo Funciona?

Cuando un usuario sube un archivo (manual técnico, documentación o guía) al sistema, el texto no se puede enviar directamente a un modelo de lenguaje porque suele ser demasiado largo, tener contenido basura (como números de página o cabeceras repetitivas) y carecer de estructura clara.

El módulo de ingestión realiza **3 pasos esenciales**:

```
[ Archivo Crudo ] 
       │ (.pdf, .md, .txt)
       ▼
1. Validación y Extracción
   - Verifica extensión permitida y límite de tamaño (máx. 20MB).
   - PDF: se extrae preferentemente con un parser consciente de Markdown
     (tablas, encabezados, listas). Si esa librería no está instalada, o si
     falla al procesar un PDF puntual, se cae automáticamente a una
     extracción de texto plano con pypdf — un PDF problemático ya no
     interrumpe toda la ingesta.
   - Elimina ruido visual en PDFs extraídos en modo plano (cabeceras y pies
     de página repetidos).
       │
       ▼
2. Detección de Secciones
   - En Markdown: reconoce encabezados jerárquicos (#, ##, ###).
   - En Texto plano: detecta patrones de capítulos y mayúsculas.
   - En PDF: etiqueta y divide el contenido por número de página (modo
     plano) o por encabezados Markdown (modo parser).
       │
       ▼
3. Segmentación Inteligente (Chunking)
   - Corta el texto respetando párrafos y límites de oraciones (sin cortar palabras a la mitad).
   - Prepara los datos en formato jerárquico Padre-Hijo (Parent-Child) listo para RAG.
   - Opcionalmente, extrae de 0 a 4 conceptos clave por sección (ver más abajo).
```

### Conceptos Clave
- **Sección (Parent Chunk):** Es el bloque temático completo (por ejemplo, todo el apartado *"Configuración de Subredes"*). Aporta todo el contexto educativo al LLM.
- **Fragmento (Child Chunk):** Subdivisión más pequeña dentro de la sección. Sirve para calcular vectores (embeddings) con alta precisión matemática.
- **Conceptos clave (opcional, KeyBERT):** Cada Parent Chunk puede incluir una lista corta de frases clave extraídas automáticamente de su propio texto, útiles como pistas para el prompt del LLM en la etapa de generación. Está **desactivado por defecto** (`USE_KEYBERT_CONCEPTS=false`) porque carga su propio modelo local y añade tiempo a la ingesta; se activa por variable de entorno cuando se quiera medir su aporte. El modelo se carga una sola vez por instancia de `IngesterService`, no en cada documento procesado.

---

## 2. Guía Rápida para Desarrolladores: ¿Cómo Usarlo?

Esta sección está pensada para que cualquier miembro del equipo continúe implementando sobre este módulo sin fricción.

### Ingesta Directa en Python
```python
from pathlib import Path
from app.services.ingester_service import IngesterService

# Inicializar servicio
ingester = IngesterService()

# Procesar archivo (.pdf, .md o .txt)
doc = ingester.process_document(Path("ruta/a/mi_documento.pdf"), title="Mi Manual")
# document_id es opcional (por defecto genera uno nuevo); document_pipeline_service.py
# pasa el suyo propio, para que el mismo ID quede compartido entre el archivo
# subido, la fila de la tabla documents y el índice FAISS del documento.

# 1. Acceso a los atributos del documento
print(f"ID: {doc.document_id}")
print(f"Título: {doc.title}")
print(f"Total de chunks: {len(doc.chunks)}")

# 2. Conversión para el pipeline de RAG (Parent-Child)
rag_payload = ingester.build_rag_chunks(doc)
# Contiene: rag_payload["parent_chunks"] y rag_payload["child_chunks"]
```

> **Nota:** la versión anterior de este documento mostraba `doc.to_rag_format()`. Ese método no existe — `app/schemas/ingestion.py` es explícito en que la conversión Parent-Child se movió deliberadamente al servicio (un esquema describe datos, no los procesa). La forma correcta y vigente es `ingester.build_rag_chunks(doc)`, como en el ejemplo de arriba.

### Estructura de los Objetos
- **`doc.chunks`** (`List[DocumentChunk]`, definido en `schemas/ingestion.py`):
  - `chunk_id`: Identificador único (ej. `uuid-0`).
  - `text`: Texto limpio del fragmento.
  - `section_title`: Título de la sección de origen (o `None`).
  - `heading_level`: Nivel jerárquico (1 para `#`, 2 para `##`, etc.).
  - `page_number`: Número de página (específico para PDFs en modo plano).
  - Este esquema describe únicamente la salida cruda de la ingesta — no incluye ningún campo de embeddings, que pertenece a una etapa posterior (ver más abajo).
- **`rag_payload`** (`dict`), construido a partir de los modelos tipados en **`schemas/rag_chunks.py`** (`ParentChunk` y `ChildChunk`):
  - `parent_chunks`: cada elemento se valida como `ParentChunk` — `{"id", "title", "breadcrumb", "content", "metadata"}`, donde `metadata` (`ParentChunkMetadata`) incluye `source_title`, `section_index`, `page_number`, `heading_level` y `key_concepts` (lista vacía si `USE_KEYBERT_CONCEPTS=false`).
  - `child_chunks`: cada elemento se valida como `ChildChunk` — `{"id", "parent_id", "breadcrumb", "content", "metadata"}`, donde `metadata` (`ChildChunkMetadata`) incluye `parent_id` y `source`.
  - `build_rag_chunks()` construye estos modelos y los valida al crearlos, pero devuelve diccionarios planos (`.model_dump()`) — así `vector_store_service`, `retrieval_service` y `reranker_service`, que ya operan sobre dicts, no necesitan cambios. La validación ocurre en el origen, no en cada consumidor.
  - **Por qué un archivo aparte de `schemas/ingestion.py`:** los chunks Padre/Hijo son un dato de la etapa RAG (se embeben, se indexan, se recuperan y se reordenan), no de la ingesta cruda del documento — mezclarlos en el mismo esquema que `IngestedDocument` difuminaba esa frontera.

### Endpoint HTTP (FastAPI)
- **Ruta:** `POST /api/v1/parse-document` (también compatible con `/api/v1/parse-pdf`)
- **Parámetro:** `file` (multipart/form-data)
- **Formatos aceptados:** `.pdf`, `.md`, `.markdown`, `.txt` (hasta 20 MB).
- **Respuesta (JSON):**
  ```json
  {
    "status": "exito",
    "filename": "manual_oci.pdf",
    "titulo_sugerido": "Manual Oci",
    "total_chunks": 12,
    "texto_extraido": "...",
    "chunks": [ ... ]
  }
  ```

> ⚠️ **Este endpoint solo parsea y trocea el documento.** No genera embeddings, no indexa en el vector store y no sube nada a OCI/Supabase — es decir, un documento pasado por aquí todavía no queda "listo para generar" contenido. Esa responsabilidad completa (subir → registrar metadata → ingestar → embeber → indexar) ya existe en **`document_pipeline_service.py`** (`process_and_index_document()`, ver el documento de Almacenamiento de Documentos con Supabase). Este endpoint probablemente se reemplace por uno que llame a ese pipeline en vez de solo a `IngesterService`.

---

## 3. Pruebas Manuales con `uv`

Para verificar el funcionamiento del procesador sin necesidad de levantar el servidor web:

```powershell
cd backend
uv run python tests/manual/test_ingester.py
```
El script procesará los archivos de muestra ubicados en `backend/tests/manual/sample_docs/` e imprimirá la estructura de chunks detectada.

**Pendiente de agregar** a este test:
1. Un PDF donde el parser Markdown (`pymupdf4llm`) falle a propósito, para confirmar que la ingesta cae a la extracción de texto plano en vez de abortar.
2. Una corrida con `USE_KEYBERT_CONCEPTS=true` que confirme que aparecen `key_concepts` no vacíos en los Parent Chunks, y otra con el flag en `false` que confirme que la lista queda vacía sin cargar el modelo.