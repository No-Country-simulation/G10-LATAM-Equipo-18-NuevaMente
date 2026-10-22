# Arquitectura del Backend

> `docs/04-Documentacion/backend/architecture/` · [Volver al README](../../../../README.md)

Este documento describe cómo está organizado el backend de NuevaMente: la capa
HTTP, los servicios del pipeline, los clientes de infraestructura y los
esquemas. El detalle de cada etapa vive en los archivos hermanos de
`04-Documentacion/backend/`.

---

## 1. Capas del backend

El backend sigue los principios de **Clean Architecture** y separación de
responsabilidades. El árbol de `backend/app/` es:

| Carpeta | Rol |
| :--- | :--- |
| `api/v1/endpoints/` | Superficie HTTP (routers FastAPI). No contiene lógica de negocio. |
| `services/` | Núcleo del proyecto: ingesta, embeddings, indexado, recuperación y orquestación. |
| `infrastructure/` | Clientes de servicios externos (Gemini, Jina, Groq, OpenRouter, Cohere, OCI, Supabase). |
| `schemas/` | Contratos Pydantic de entrada/salida (`adaptation`, `document_record`, `ingestion`, `rag_chunks`). |
| `core/` | Configuración central (`config.py`): modelos, límites y banderas de entorno. |
| `prompts/` | Plantillas de prompt (en español) que consumen los agentes. |
| `domain/` | Tipos y reglas de negocio puras, sin dependencias de infraestructura. |

El principio se repite en toda la app: **los endpoints no hablan con las APIs
externas ni con FAISS; los servicios tampoco conocen el HTTP**. Cada capa
depende solo de la interfaz de la capa inferior.

---

## 2. Superficie HTTP (`app/api/v1/endpoints/`)

`app/api/v1/api.py` compone el router v1; `main.py` lo monta bajo `/api/v1`
(y, por compatibilidad, también bajo `/api`, `/api/api/v1` y `/api/api`).

| Módulo | Responsabilidad |
| :--- | :--- |
| `documents.py` | Ingesta (`POST /documents`), listado/consulta, borrado (`DELETE /documents/{id}`) y generación (`POST /documents/{id}/adapt`). Es el corazón funcional. |
| `contents.py` | Biblioteca de contenidos generados. |
| `health.py` | Estado del sistema. |
| `auth.py` | Autenticación de usuarios. |
| `anki.py` | Exportación de flashcards a Anki (`.apkg`). |
| `trash.py` | Papelera y borrado lógico. |
| `storage.py` | Operaciones sobre OCI Object Storage. |
| `multimodal.py` | Extracción de diagramas de una imagen (`POST /extract-diagram`). |
| `export.py` | Exportación a PDF (`POST /export/pdf`). |

---

## 3. Servicios del pipeline (`app/services/`)

Los servicios se agrupan por etapa de ejecución. Cada grupo se documenta en su
propio archivo de `04-Documentacion/backend/`.

| Etapa | Servicios | Documento |
| :--- | :--- | :--- |
| **1. Ingesta** | `document_pipeline_service`, `pdf_parser_service`, `text_cleaner`, `noise_filter_service`, `ingester_service`, `pdf_image_extractor`, `pdf_vision_service` | [Ingesta y Chunking](../ingestion/Ingesta_y_Chunking.md) |
| **2. Embeddings** | `embedding_service`, `embedding_rate_limiter` | [Embeddings](../embeddings/Embeddings.md) |
| **3. Indexación** | `vector_store_service` | [Almacén Vectorial](../embeddings/Almacen_Vectorial.md) |
| **4. Recuperación** | `retrieval_service`, `reranker_service` | [Recuperación](../retrieval/Recuperacion.md) · [Reranking](../retrieval/Reranking.md) |
| **5. Orquestación y salida** | `langgraph_orchestrator`, `pipeline_stages`, `multi_agent_router`, `coverage_planner`, `rate_guard`, `source_context`, `summary_composer`, `pdf_export_service` | este documento (§4) · [Anclaje técnico](../quality/Anclaje_Tecnico.md) |

Servicios de soporte transversal:

- `document_storage_service` y los adaptadores de `services/storage/`
  (`local_backend`, `oci_backend`): mueven bytes del documento original y de
  los artefactos generados. Supabase se resuelve en
  `document_storage_service` para documentos originales; todavía no existe un
  `supabase_backend` de bajo nivel → [Storage](../storage/Almacenamiento_OCI.md).
- `document_repository`: metadata y estados del documento en SQLite o Supabase,
  según el backend de documentos.
- `document_deletion_service`: borrado permanente en todas las capas
  (metadatos, storage, índice FAISS, caché).
- `storage_queue_service`, `trash_service`: cola de subida de artefactos
  (OCI/local) y borrado lógico; la papelera aún no soporta Supabase.

---

## 4. Orquestación multi-agente y generación

El contenido educativo se produce con **LangGraph** (`langgraph_orchestrator.py`)
sobre un router de proveedores (`multi_agent_router.py`):

1. **Recuperación de contexto** — `retrieval_service.retrieve_context()` devuelve
   los *parent chunks* más relevantes del documento (densa + BM25 + rerank).
2. **Planificación de cobertura** — `coverage_planner.py` decide qué conceptos
   debe cubrir el contenido.
3. **Generación** — los agentes redactan según el formato solicitado
   (flashcards, quiz, tutorial, …), con prompts en `app/prompts/`.
4. **Deduplicación** — se eliminan elementos casi idénticos.
5. **Anclaje** — cada elemento debe citar sus fragmentos; se verifica por vía
   léxica y por un crítico LLM. Detalle en
   [Anclaje técnico](../quality/Anclaje_Tecnico.md).
6. **Reparación / refinamiento** — los elementos no verificados se reescriben y
   se re-auditan, dentro de un presupuesto de revisiones.
7. **Validación** — el resultado se valida contra los esquemas Pydantic
   (`AdaptationResponse`) antes de responder.

Los clientes de LLM viven en `app/infrastructure/` (`gemini_client`,
`groq_client`, `cohere_client`). El router elige el proveedor preferido por
formato y define una **cascada de respaldo** para tolerar caídas o cuotas
agotadas. El detalle de cada nodo, el estado compartido y el bucle de
reparación está en
[Orquestación multi-agente](Orquestacion_Multi_Agente.md).

---

## 5. Componentes externos

```mermaid
flowchart LR
    UI["Frontend Angular"] -->|REST / SSE| API["API FastAPI"]
    GR["Frontend Gradio (pruebas)\nimporta servicios in-process"] --> PIPE
    API --> PIPE["Servicios del pipeline"]
    PIPE --> FAISS["Índice FAISS (local)"]
    PIPE --> SUP["Supabase parcial\n(documentos originales + metadata)"]
    PIPE --> OCI["OCI Object Storage\n(artefactos generados + cola)"]
    PIPE --> EXT["Gemini · Jina · Groq · OpenRouter · Cohere"]
```

---

<div align="right">

[Volver al README](../../../../README.md)

</div>

