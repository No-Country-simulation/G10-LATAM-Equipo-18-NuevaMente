# Configuración de LLMs

> `docs/02-Instalacion/` · [Volver al README](../../README.md)

Cómo se configuran los modelos de lenguaje y de embeddings que usa NuevaMente.

> **Importante:** los **identificadores de modelo están centralizados en
> `backend/app/core/config.py`**. Cambiarlos por `.env` no surte efecto; lo que
> sí se configura por `.env` son las **claves de API** y algunos límites.

---

## 1. Claves de API (`backend/.env`)

```dotenv
# LLMs
GEMINI_API_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=

COHERE_API_KEY=        # usado por el reranker de Cohere
JINA_API_KEY=       # Embeddings
```

Nunca se versionan; parten de `backend/.env.example`.

---

## 2. Proveedores y cascadas de LLM

El router (`app/services/multi_agent_router.py`) elige el proveedor preferido
según el **formato de salida** y define una **cascada de respaldo** para tolerar
caídas o cuotas agotadas. Las cascadas viven en `settings.LLM_CASCADES`
(`config.py`) y hay una por formato:

- `flashcards`, `quiz`, `tutorial`, `executive_summary`, `class_script` — y una cascada `CRITIC_CASCADE` para la revisión crítica.

Modelos de referencia (según `config.py`):

| Rol | Modelo |
| :--- | :--- |
| Gemini (flash) | `gemini-3.6-flash` |
| Groq | `openai/gpt-oss-20b` |
| OpenRouter | `mistralai/mistral-small-3.2-24b-instruct` |

Cada entrada de la cascada es `{"provider": ..., "model": ...}`; si un proveedor
falla, se pasa al siguiente de la lista sin intervención manual.

---

## 3. Embeddings

Se configuran por variables (con defaults razonables):

```dotenv
EMBEDDING_PROVIDER_ORDER=gemini,jina,local
DEFAULT_GEMINI_MODEL_FLASH=gemini-flash-lite-latest
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

Modelos usados (centralizados): `models/gemini-embedding-001`,
`jina-embeddings-v3` y el modelo local `intfloat/multilingual-e5-base`, todos a
768 dimensiones. El detalle de cuotas y fallbacks está en
[Embeddings](../04-Documentacion/backend/embeddings/Embeddings.md).

---

## 4. Reranking

- **Jina** reutiliza `JINA_API_KEY`.
- **Cohere** se configura en `app/infrastructure/cohere_client.py`. Si no hay key
  válida, el reranker de Cohere se salta y se conserva el orden de RRF →
  [Reranking](../04-Documentacion/backend/retrieval/Reranking.md).

---

## 5. Cómo verificar la configuración

```bash
cd backend
uv run python scripts/check_services.py
```

Revisa el estado de las conexiones y claves configuradas.

---

<div align="right">

[Volver al README](../../README.md)

</div>

