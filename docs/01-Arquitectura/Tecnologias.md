# Tecnologías

> `docs/01-Arquitectura/` · [Volver al README](../../README.md)

Stack tecnológico de NuevaMente.

---

## 1. Backend

| Tecnología | Uso |
| :--- | :--- |
| **Python 3.11+** | Lenguaje del backend. |
| **FastAPI** | API REST (incluye SSE para el progreso de ingesta). |
| **Uvicorn** | Servidor ASGI. |
| **Pydantic** | Validación de esquemas de entrada/salida. |
| **uv** | Gestión de entorno y dependencias (fuente de verdad: `pyproject.toml` / `uv.lock`). |
| **LangGraph** | Orquestación multi-agente de la generación. |
| **FAISS (CPU)** | Índice vectorial local, uno por documento. |
| **BM25 (`rank_bm25`)** | Búsqueda léxica complementaria a la densa. |
| **intfloat/multilingual-e5-base** | Modelo de embeddings local (último respaldo). |

## 2. Frontend

| Tecnología | Uso |
| :--- | :--- |
| **Angular 17** | SPA standalone (`bootstrapApplication`). |
| **TypeScript** | Lenguaje del frontend. |
| **RxJS / HttpClient** | Estado y comunicación con la API. |
| **Gradio** | UI mínima de pruebas (`frontend_gradio/`). |

## 3. Modelos de IA (principales)

| Tipo | Proveedor | Modelo |
| :--- | :--- | :--- |
| LLM (flash) | Google Gemini | `gemini-3.6-flash` |
| LLM (flash-lite) | Google Gemini | `gemini-3.5-flash-lite` |
| LLM | Groq | `openai/gpt-oss-20b` / `qwen/qwen3.8-27b` |
| LLM | OpenRouter | `mistralai/mistral-small-3.2-24b-instruct` / `nvidia/nemotron-3.5-lightning:free` |
| Embeddings | Google Gemini | `models/gemini-embedding-001` (768 dim) |
| Embeddings | Jina AI | `jina-embeddings-v3` (768 dim) |
| Embeddings | Local (sentence-transformers) | `intfloat/multilingual-e5-base` (768 dim) |
| Reranking | Jina AI | `jina-reranker-v2-base-multilingual` |
| Reranking | Cohere | `rerank-multilingual-v3.0` |

> Los identificadores de modelo están centralizados en `backend/app/core/config.py`.

> **Alcance de almacenamiento:** OCI es el backend completo del MVP. Supabase
> cubre solo documentos originales y su metadata; el selector por tipo de dato
> y la integración completa están en
> [Mejoras Post-MVP](../05-Roadmap/Mejoras_Post_MVP.md).

## 4. Almacenamiento e infraestructura

| Tecnología | Uso |
| :--- | :--- |
| **OCI Object Storage** | Almacenamiento completo del MVP: documentos, artefactos y cola. |
| **Supabase** | Modo parcial: Storage de documentos originales y metadata en Postgres. No guarda aún artefactos, biblioteca ni vectores. |
| **SQLite** | Usuarios, autenticación, contenidos, auditoría y cola de trabajos. Convive con Supabase en el modo parcial. |
| **FAISS en disco** | Índices vectoriales locales (`vector_store/{document_id}/`); persistencia remota pendiente. |
| **Docker Compose** | Backend (contenedor, puerto 8000) + frontend (nginx, puerto 80). |

## 5. Herramientas de desarrollo

| Herramienta | Uso |
| :--- | :--- |
| **uv** | Ejecutar el backend y sus dependencias. |
| **npm / Angular CLI** | Ejecutar y compilar el frontend. |
| **pytest** | Pruebas del backend. |
| **Docker / nginx** | Empaquetado y proxy en producción. |

---

<div align="right">

[Volver al README](../../README.md)

</div>

