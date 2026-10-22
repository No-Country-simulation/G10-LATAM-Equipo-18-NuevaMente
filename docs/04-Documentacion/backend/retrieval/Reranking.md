# Módulo de Reranking

> `docs/04-Documentacion/backend/retrieval/` · [Volver al README](../../../../README.md)

Última etapa de la recuperación: reordena los candidatos que devuelve
[Recuperación](Recuperacion.md) para quedarse con los más relevantes.

---

## 1. Explicación simple: ¿cómo funciona?

Tras la fusión RRF quedan varios *parent chunks* candidatos. Un modelo
**cross-encoder** especializado compara la consulta con cada candidato y devuelve
un score de relevancia más fino que la similitud vectorial.

```text
[ Candidatos ordenados por RRF ]
               │
               ▼
1. Jina Reranker (proveedor principal)
   - recibe query + lista de documentos, devuelve relevancia por documento.
               │
       (si falla)
               ▼
2. Cohere Reranker (respaldo)
               │
       (si también falla)
               ▼
3. Se conserva el orden de RRF sin reordenar
   - la generación nunca se detiene por un proveedor caído.
```

### Conceptos clave

- **No usa embeddings:** el reranker trabaja con texto, no depende de
  `EMBEDDING_DIMENSIONS` ni del proveedor que indexó.
- **Cadena con respaldo:** Jina → Cohere → orden de RRF.
- **Forma de resultado común:** `{"index": <posición>, "relevance_score": float}`,
  sin importar qué proveedor respondió. Así `retrieval_service` no se acopla a
  ninguno.

---

## 2. Guía rápida para desarrolladores

El reranker rara vez se usa de forma aislada; normalmente lo invoca
`retrieval_service`. Aun así, puede probarse solo:

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

---

## 3. Configuración del entorno

Jina reutiliza la misma API key que los embeddings:

```python
# Defaults en app/core/config.py
JINA_API_KEY = ""   # requerido para JinaReranker (y para embeddings vía Jina)
```

Cohere se configura en `app/infrastructure/cohere_client.py`. Si su API key no
está configurada, `CohereReranker.rerank()` lanza un error y `retrieval_service`
simplemente lo salta y usa el orden de RRF.

Modelos exactos:

| Proveedor | Modelo | Dónde |
| :--- | :--- | :--- |
| Jina | `jina-reranker-v2-base-multilingual` | `app/services/reranker_service.py` |
| Cohere | `rerank-multilingual-v3.0` | `app/infrastructure/cohere_client.py` |

Los identificadores son constantes del código; se cambian editando el archivo,
no por `.env`.

---

<div align="right">

[Volver al README](../../../../README.md)

</div>

