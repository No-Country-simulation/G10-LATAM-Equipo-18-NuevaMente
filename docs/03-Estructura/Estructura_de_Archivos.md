# Estructura de Archivos

> `docs/03-Estructura/` · [Volver al README](../../README.md)

Mapa del repositorio de NuevaMente. Para el detalle de cada pieza, ver
[Componentes](../01-Arquitectura/Componentes.md) y
[04-Documentacion](../04-Documentacion/backend/architecture/Arquitectura_del_Backend.md).

---

## 1. Raíz del proyecto

```text
NuevaMente/
├── backend/               # API FastAPI + pipeline RAG + agentes
├── frontend/              # SPA Angular 17
├── frontend_gradio/       # UI mínima de pruebas (Gradio)
├── docs/                  # documentación (ver §3)
├── README.md              # punto de entrada del repositorio
└── .gitignore/            # reglas locales (git-ignored)
```

---

## 2. `backend/`

```text
backend/
├── main.py                # crea la app FastAPI y monta el router v1
├── pyproject.toml         # dependencias (fuente de verdad con uv.lock)
├── .env.example           # plantilla de variables de entorno
├── migrations/            # SQL de Supabase (se aplican a mano)
├── scripts/               # utilidades (p. ej. check_services.py)
├── tests/                 # pruebas (pytest) y tests/manual/
├── vector_store/          # índices FAISS generados (por document_id)
└── app/
    ├── api/v1/
    │   ├── api.py         # composición del router v1
    │   └── endpoints/     # documents, contents, health, auth, anki, trash, storage
    ├── services/          # núcleo: pipeline RAG + orquestación
    ├── infrastructure/    # clientes externos (gemini, groq, jina, cohere, oci, supabase)
    ├── schemas/           # contratos Pydantic
    ├── core/              # config.py (modelos, límites, banderas)
    ├── prompts/           # plantillas de prompt (en español)
    └── domain/            # tipos y reglas de negocio puras
```

---

## 3. `frontend/`

```text
frontend/
├── nginx.conf             # proxy de producción (/api/v1/ → backend)
├── package.json
└── src/
    ├── main.ts            # bootstrapApplication (standalone)
    ├── environments/      # environment.ts / environment.prod.ts
    └── app/
        ├── app.routes.ts
        ├── core/          # api, config, guards, interceptors, models, services, store
        └── features/      # auth, workspace, documents, library, compare, trash
```

---

## 4. `docs/`

```text
docs/
├── 01-Arquitectura/       # Arquitectura, Componentes, Tecnologías
├── 02-Instalacion/        # Uso local, configuración de LLM y de storage
├── 03-Estructura/         # este documento
├── 04-Documentacion/      # documentación técnica por etapa
│   ├── backend/
│   │   ├── ingestion/     # ingesta y API
│   │   ├── embeddings/    # embeddings y almacén vectorial
│   │   ├── storage/       # OCI y Supabase
│   │   ├── retrieval/     # recuperación y reranking
│   │   └── architecture/  # arquitectura y flujo de servicios
│   └── frontend/          # Angular y Gradio
└── old/                   # documentación archivada (revisión pendiente)
```

---

<div align="right">

[Volver al README](../../README.md)

</div>

