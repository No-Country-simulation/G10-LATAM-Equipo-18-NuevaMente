# Componentes

> `docs/01-Arquitectura/` · [Volver al README](../../README.md)

Inventario de las piezas que forman NuevaMente. Para el detalle de ejecución,
ver [Arquitectura](Arquitectura.md) y
[04-Documentacion](../04-Documentacion/backend/architecture/Arquitectura_del_Backend.md).

---

## 1. Backend (`backend/`)

```text
app/
├── api/v1/endpoints/   # documents, contents, health, auth, anki, trash,
│                       # storage, multimodal, export
├── services/           # pipeline RAG + orquestación multi-agente
│   └── storage/        # adaptadores local, OCI y Supabase
├── infrastructure/     # clientes: gemini, groq, jina, cohere, oci, supabase
├── schemas/            # contratos Pydantic (adaptation, document_record, …)
├── core/               # configuración central (config.py)
├── prompts/            # plantillas de prompt
└── domain/             # tipos y reglas de negocio puras
```

| Componente | Función |
| :--- | :--- |
| **API REST** | Expone ingestión, documentos, contenidos, Anki, papelera, storage, extracción multimodal y exportación. |
| **Pipeline RAG** | Ingesta → embeddings → índice → recuperación → reranking. |
| **Orquestación** | Router de proveedores + agentes LangGraph que generan el contenido. |
| **Anclaje** | Verificación de fidelidad de cada elemento contra las fuentes citadas. |
| **Almacenamiento** | Documentos originales y artefactos, con backend intercambiable. |
| **Exportación** | PDF (`pdf_export_service`) y mazos de Anki (`genanki`). |

---

## 2. Frontend (`frontend/`)

SPA en Angular con *features* autocontenidas:

| Feature | Función |
| :--- | :--- |
| `auth` | Login, registro y recuperación. |
| `workspace` | Flujo de adaptación en pasos. |
| `process` | Pantalla de progreso del procesamiento (SSE). |
| `documents` | Subida y estado de documentos. |
| `library` | Biblioteca de contenidos generados. |
| `compare` | Comparación de variantes. |
| `shared` | Componentes reutilizables entre features. |
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

