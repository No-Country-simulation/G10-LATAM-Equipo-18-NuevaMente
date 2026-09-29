# Módulo de Recuperación (Retrieval) — NuevaMente

Este documento describe la arquitectura, funcionamiento e instrucciones de uso de la etapa de recuperación del pipeline RAG: búsqueda dentro de un documento ya indexado, y reordenamiento (reranking) de los resultados.

---

## 1. Explicación Simple: ¿Cómo Funciona?

Una vez que un documento fue ingerido, embebido e indexado (ver los documentos de Ingestión y de Embeddings/Vector Store), la app no hace consultas libres del usuario — arma internamente sus propias búsquedas a partir del perfil, formato y nicho elegidos, para encontrar los fragmentos más relevantes con los que generar contenido.

```
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
   - Combina las dos listas de POSICIONES (no de scores crudos, que no son
     comparables entre sí) en un único orden de relevancia.
               │
               ▼
4. Resolución de Padres Únicos
   - Recorre el orden fusionado y junta hasta N fragmentos PADRE distintos
     (deduplicados), que es lo que realmente se usará como contexto.
               │
               ▼
5. Reranking (Jina, con Cohere como respaldo)
   - Reordena esos candidatos con un modelo especializado en relevancia.
   - Si Jina falla, se intenta con Cohere. Si ambos fallan, se conserva el
     orden de RRF sin reordenar — nunca se detiene la generación por esto.
```

### Conceptos Clave
- **Todo dentro de un documento:** esta etapa nunca busca entre varios documentos a la vez — siempre recibe un `document_id` y trabaja solo con su índice.
- **RRF por posición, no por score:** un score denso (similitud coseno) y uno léxico (BM25) no se pueden sumar directamente porque viven en escalas distintas. RRF resuelve esto usando la *posición* de cada fragmento en cada ranking (`1 / (60 + posición)`), no el valor del score.
- **El reranker no usa embeddings:** a diferencia de la búsqueda densa, el reranker recibe el texto de la consulta y el de cada candidato directamente, y devuelve un score de relevancia por comparación (modelo cross-encoder). No depende de `EMBEDDING_DIMENSIONS` ni de qué proveedor de embeddings se usó para indexar.
- **Cadena de reranking con respaldo:** Jina es el proveedor principal (mismo ecosistema que los embeddings); si falla, se reintenta con Cohere. Solo si ambos fallan se usa el orden de RRF tal cual, sin reordenar — la recuperación nunca se detiene por un proveedor caído.
- **Esta etapa no genera contenido:** `retrieval_service.py` solo devuelve texto ordenado por relevancia. Llamar al LLM para redactar el contenido final es responsabilidad de la etapa siguiente (el orquestador de agentes), no de este módulo.

---

## 2. Guía Rápida para Desarrolladores: ¿Cómo Usarlo?

### Uso Directo en Python

```python
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService

# RetrievalService detecta automáticamente el store.model_name guardado en el
# índice del documento y vectoriza la consulta con el modelo correspondiente,
# garantizando compatibilidad semántica incluso si hubo fallback a Jina o Local.
embedding_svc = EmbeddingService()
retrieval_svc = RetrievalService(embedding_service=embedding_svc)

document_id = "un-uuid-de-documento-ya-indexado"
query = "conceptos clave de configuración de subredes en OCI"

resultados = retrieval_svc.retrieve(
    document_id=document_id,
    query=query,
    top_k=5,            # cuántos parent chunks finales se devuelven
    rerank_pool_size=10, # cuántos candidatos únicos se le pasan al reranker
)

for parent in resultados:
    print(parent["title"], "->", parent.get("relevance_score"))
```

### Qué hace `retrieve()` internamente
1. Abre el índice del documento con `vector_store_service.get_store(document_id)`. Si no hay nada indexado, devuelve una lista vacía en vez de fallar.
2. Calcula el ranking denso (`_dense_ranks`) y el léxico (`_lexical_ranks`) sobre `store.child_documents` — no recibe los chunks por parámetro, los toma directamente del store, para no duplicar datos que ya están ahí desde la ingesta.
3. Fusiona ambos con RRF (`_fuse_rrf`).
4. Resuelve fragmentos padre únicos desde `store.parent_documents` (`_resolve_unique_parents`).
5. Reordena con `_rerank`, probando cada proveedor de `reranker_service.get_default_rerankers()` en orden hasta que uno responda.

### Usar el reranker de forma aislada

```python
from app.services.reranker_service import get_default_rerankers

rerankers = get_default_rerankers()  # [JinaReranker(), CohereReranker()]

query = "¿qué es una VCN?"
documentos = [
    "Una VCN es una red virtual privada en OCI.",
    "Las listas de seguridad funcionan como firewalls virtuales.",
]

for reranker in rerankers:
    try:
        resultados = reranker.rerank(query=query, documents=documentos, top_n=2)
        print(type(reranker).__name__, "respondió:", resultados)
        break
    except Exception as exc:
        print(type(reranker).__name__, "falló:", exc)
```

Cada resultado tiene la forma `{"index": <posición en documentos>, "relevance_score": float}`, sin importar si respondió Jina o Cohere — `retrieval_service` depende de esa forma común para no acoplarse a un proveedor específico.

---

## 3. Configuración del Entorno

```python
# Defaults en app/core/config.py
JINA_API_KEY = ""      # requerido para JinaReranker (y para embeddings vía Jina)
```

Cohere se configura en `app/infrastructure/cohere_client.py` (no documentado aquí — es un archivo de otro integrante del equipo). Si su API key no está configurada, `CohereReranker.rerank()` lanza un error y `retrieval_service` simplemente lo salta y usa el orden de RRF.

---

## 4. Pruebas Manuales

**Pendiente de crear:** `tests/manual/test_retrieval.py`, siguiendo el mismo formato que `test_vector_store.py`. Debería cubrir, como mínimo:
1. Recuperación de extremo a extremo sobre un documento ya indexado (ingesta → embeddings → índice → `retrieve()`).
2. Que el orden RRF cambie coherentemente si se altera artificialmente el peso denso vs. léxico (usando documentos de prueba donde el resultado esperado es conocido).
3. Que si `JinaReranker` falla (por ejemplo, con una API key inválida a propósito), `CohereReranker` tome el relevo.
4. Que si ambos rerankers fallan, `retrieve()` devuelva el orden de RRF sin lanzar una excepción.