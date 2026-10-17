# Almacén Vectorial (FAISS)

> `docs/04-Documentacion/backend/embeddings/` · [Volver al README](../../../../README.md)

Este documento describe cómo se indexan y persisten los embeddings generados por
el [módulo de Embeddings](Embeddings.md). El motor es **FAISS**.

---

## 1. Explicación simple

Cada documento indexado tiene su **propio** índice FAISS aislado
(`vector_store/{document_id}/`), porque la generación de contenido siempre
trabaja sobre un único documento — nunca se busca entre varios a la vez.

El índice guarda:

- los **child chunks** con sus vectores (para la búsqueda semántica), y
- los **parent chunks** asociados (el contexto grande que se entrega al LLM).

En disco, un índice consta de dos archivos: `index.faiss` (los vectores) y
`metadata.json` (los textos, breadcrumbs y la etiqueta `model_name`).

---

## 2. Guía rápida para desarrolladores

### Fábrica por documento (recomendado)

```python
from app.services.vector_store_service import get_store, save_store

document_id = "un-uuid-de-documento"

# 1. Abre el índice si existe, o crea uno vacío con la dimensión configurada.
vector_store = get_store(document_id)

# 2. Indexa child chunks con sus vectores y registra los padres.
vector_store.add_documents(
    child_chunks=rag_payload["child_chunks"],
    embeddings=vectores_batch,
    parent_chunks=rag_payload["parent_chunks"],
    model_name=embedding_svc.model_name,
)

# 3. Persiste en vector_store/{document_id}/ y refresca el caché en memoria.
save_store(document_id, vector_store)
```

`rag_payload` ya llega validado: `IngesterService.build_rag_chunks()` lo
construye contra los modelos `ChildChunk` / `ParentChunk` de
`app/schemas/rag_chunks.py`. Ver [Ingesta y Chunking](../ingestion/Ingesta_y_Chunking.md).

### Uso directo de `FAISSVectorStore` (bajo nivel)

```python
from app.services.vector_store_service import FAISSVectorStore

vector_store = FAISSVectorStore(model_name=embedding_svc.model_name)
vector_store.add_documents(
    child_chunks=rag_payload["child_chunks"],
    embeddings=vectores_batch,
    parent_chunks=rag_payload["parent_chunks"],
    model_name=embedding_svc.model_name,
)

# Búsqueda semántica de fragmentos hijos
hijos_top = vector_store.similarity_search(
    query_embedding=vector_query,
    query_model_name=embedding_svc.model_name,
    top_k=3,
)

# Recuperación directa de Parent Chunks completos para el LLM
padres_top = vector_store.retrieve_parent_chunks(
    query_embedding=vector_query,
    query_model_name=embedding_svc.model_name,
    top_k_parents=2,
)

vector_store.save("vector_store/mi_indice")
cargado = FAISSVectorStore()
cargado.load("vector_store/mi_indice")
```

> Para búsquedas dentro del pipeline de RAG (no pruebas sueltas), usa
> `retrieval_service`, que combina esta búsqueda densa con BM25 y un reranker →
> ver [Recuperación](../retrieval/Recuperacion.md).

---

## 3. Configuración

```python
# Defaults en app/core/config.py
EMBEDDING_DIMENSIONS = 768
VECTOR_STORE_METHOD = "faiss"       # 'faiss' (por documento) o 'pgvector' (rama Supabase)
VECTOR_STORE_DIR = "vector_store"
```

---

## 4. Pruebas manuales

```powershell
cd backend
uv run python tests/manual/test_vector_store.py
```

Ejecuta la cadena completa: ingesta → embeddings reales (768 dimensiones) →
indexación en FAISS → similitud coseno → búsqueda semántica y resolución de
Parent Chunks → persistencia y recarga (`index.faiss` + `metadata.json`) →
bloqueo por intento de búsqueda con modelo incompatible.

**Pendiente:** una prueba de `get_store()` / `save_store()` que confirme que
abrir el mismo `document_id` dos veces reutiliza el índice del caché en memoria.

---

<div align="right">

[Volver al README](../../../../README.md)

</div>

