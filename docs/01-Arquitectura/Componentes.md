# Componentes

> `docs/01-Arquitectura/` · [Volver al README](../../README.md)

Inventario de las piezas que forman NuevaMente. Para el detalle de ejecución,
ver [Arquitectura](Arquitectura.md) y
[04-Documentacion](../04-Documentacion/backend/architecture/Arquitectura_del_Backend.md).

---

## 1. Backend (`backend/`)

```text
app/
├── api/v1/endpoints/   # documents, contents, health, auth, anki, trash, storage
├── services/           # pipeline RAG + orquestación multi-agente
├── infrastructure/     # clientes: gemini, groq, jina, cohere, oci, supabase
├── schemas/            # contratos Pydantic (adaptation, document_record, …)
├── core/               # configuración central (config.py)
├── prompts/            # plantillas de prompt
└── domain/             # tipos y reglas de negocio puras
```

| Componente | Función |
| :--- | :--- |
| **API REST** | Expone ingestión, documentos, contenidos, Anki, papelera y storage. |
| **Pipeline RAG** | Ingesta → embeddings → índice → recuperación. |
| **Orquestación** | Router de proveedores + agentes LangGraph que generan el contenido. |
| **Almacenamiento** | Documentos originales y artefactos, con backend intercambiable. |

---

## 2. Frontend (`frontend/`)

SPA en Angular con *features* autocontenidas:

| Feature | Función |
| :--- | :--- |
| `auth` | Login, registro y recuperación. |
| `workspace` | Flujo de adaptación en pasos. |
| `documents` | Subida y estado de documentos. |
| `library` | Biblioteca de contenidos generados. |
| `compare` | Comparación de variantes. |
| `trash` | Papelera y borrado lógico. |

Detalle en [Frontend Angular](../04-Documentacion/frontend/Angular.md).

---

## 3. Interfaz de pruebas (`frontend_gradio/`)

UI mínima en Gradio para validar el pipeline sin la SPA. Detalle en
[Frontend Gradio](../04-Documentacion/frontend/Gradio.md).

---

## 4. Componentes externos

- **LLM:** Gemini, Groq, OpenRouter (y Cohere para reranking).
- **Embeddings:** Gemini, Jina y un modelo local (`sentence-transformers`) como
  último respaldo.
- **Almacenamiento:** Supabase Storage o OCI Object Storage.

---

<div align="right">

[Volver al README](../../README.md)

</div>

