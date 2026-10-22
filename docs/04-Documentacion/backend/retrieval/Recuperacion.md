# Módulo de Recuperación (Retrieval)

> `docs/04-Documentacion/backend/retrieval/` · [Volver al README](../../../../README.md)

Este documento describe la etapa de recuperación del pipeline RAG: la búsqueda
dentro de un documento ya indexado. El reordenamiento de resultados se detalla
en [Reranking](Reranking.md).

---

## 1. Explicación simple: ¿cómo funciona?

Una vez que un documento fue ingerido, embebido e indexado (ver
[Ingesta](../ingestion/Ingesta_y_Chunking.md) y
[Almacén Vectorial](../embeddings/Almacen_Vectorial.md)), la app no hace
consultas libres del usuario: arma internamente sus propias búsquedas a partir
del perfil, formato y nicho elegidos, para encontrar los fragmentos más
relevantes con los que generar contenido.

```text
[ Consulta interna, ej. "conceptos clave de VCN" ]
               │
               ▼
1. Búsqueda Densa (FAISS)
   - Vectoriza la consulta y busca en el índice del documento (get_store).
   - Ordena TODOS los fragmentos hijo por similitud coseno.
               │
               ▼
2. Búsqueda Léxica (BM25)
   - Ordena los mismos fragmentos hijo por coincidencia de palabras.
   - Cacheada por documento: no se reconstruye si el número de chunks no cambió.
               │
               ▼
3. Fusión RRF (Reciprocal Rank Fusion)
   - Combina las dos listas de POSICIONES (no de scores crudos) en un único orden.
               │
               ▼
4. Resolución de Padres Únicos
   - Recorre el orden fusionado y junta hasta N fragmentos PADRE distintos.
               │
               ▼
5. Reranking (Jina, con Cohere como respaldo) → ver Reranking.md
```

### Conceptos clave

- **Todo dentro de un documento:** esta etapa siempre recibe un `document_id` y
  trabaja solo con su índice; nunca busca entre varios documentos a la vez.
- **RRF por posición, no por score:** un score denso (coseno) y uno léxico (BM25)
  viven en escalas distintas, así que no se suman. RRF usa la *posición* de cada
  fragmento (`1 / (60 + posición)`).
- **El reranker no usa embeddings:** compara el texto de la consulta con el de
  cada candidato (cross-encoder) y no depende de `EMBEDDING_DIMENSIONS`.
- **Esta etapa no genera contenido:** solo devuelve texto ordenado por
  relevancia; redactar es responsabilidad del orquestador de agentes.

---

## 2. Guía rápida para desarrolladores

```python
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService

# RetrievalService detecta el store.model_name del índice y vectoriza la
# consulta con el modelo correspondiente (aunque hubo fallback a Jina o Local).
embedding_svc = EmbeddingService()
retrieval_svc = RetrievalService(embedding_service=embedding_svc)

resultados = retrieval_svc.retrieve(
    document_id="un-uuid-de-documento-ya-indexado",
    query="conceptos clave de configuración de subredes en OCI",
    top_k=5,             # parent chunks finales devueltos
    rerank_pool_size=10, # candidatos únicos que se le pasan al reranker
)

for parent in resultados:
    print(parent["title"], "->", parent.get("relevance_score"))
```

> `retrieve()` acepta `rerank_pool_size` (por defecto `10`), pero el atajo
> `retrieve_context(document_id, query, top_k)` **no**: siempre usa el valor por
> defecto. Si necesitas otro tamaño de pool, instancia `RetrievalService`.

### Qué hace `retrieve()` internamente

1. Abre el índice con `vector_store_service.get_store(document_id)`. Si no hay
   nada indexado, devuelve una lista vacía en vez de fallar.
2. Calcula el ranking denso (`_dense_ranks`) y el léxico (`_lexical_ranks`) sobre
   `store.child_documents`.
3. Fusiona ambos con RRF (`_fuse_rrf`).
4. Resuelve fragmentos padre únicos (`_resolve_unique_parents`).
5. Reordena con `_rerank`, probando cada proveedor de
   `reranker_service.get_default_rerankers()` hasta que uno responda.

---

## 3. Configuración

Esta etapa no agrega variables propias; hereda las de
[Embeddings](../embeddings/Embeddings.md) y [Reranking](Reranking.md).

---

## 4. Pruebas

**Pendiente de crear:** `tests/manual/test_retrieval.py`. Debería cubrir, como
mínimo:

1. Recuperación de extremo a extremo sobre un documento ya indexado.
2. Que el orden RRF cambie coherentemente si se altera el peso denso vs. léxico.
3. Que si `JinaReranker` falla, `CohereReranker` tome el relevo.
4. Que si ambos rerankers fallan, `retrieve()` devuelva el orden de RRF sin lanzar.

---

<div align="right">

[Volver al README](../../../../README.md)

</div>

