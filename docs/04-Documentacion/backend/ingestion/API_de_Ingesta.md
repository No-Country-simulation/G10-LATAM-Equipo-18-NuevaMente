# Contrato de la API de Ingesta

> `docs/04-Documentacion/backend/ingestion/` · [Volver al README](../../../../README.md)

Este documento define la interfaz y contrato de comunicación de la ingesta, el
procesamiento, la generación de embeddings y la indexación vectorial en
**NuevaMente**. Está dirigido a los equipos de **Frontend** y de desarrollo de
**Agentes**.

El módulo HTTP vive en `app/api/v1/endpoints/documents.py` y se expone bajo
`settings.API_V1_STR` (`/api/v1`). La ingesta ya **no** usa un prefijo
`/ingestion` ni un esquema de *polling*: un único `POST /documents` ejecuta el
pipeline completo y reporta el avance por **Server-Sent Events (SSE)**.

---

## 1. Flujo general de ingesta

Extraer texto de un PDF, limpiarlo, hacer *chunking* jerárquico Padre/Hijo,
calcular embeddings en lote y guardar el índice FAISS toma varios segundos o
minutos. Por eso el endpoint hace **streaming del progreso**: el cliente abre la
petición y recibe eventos `stage`/`message` hasta que el documento queda
`ready` (o `failed`).

```mermaid
sequenceDiagram
    autonumber
    actor Cliente as Frontend / Cliente
    participant API as API (/api/v1/documents)
    participant Storage as Almacenamiento (OCI/local; Supabase parcial)
    participant Vector as Índice FAISS

    Cliente->>API: POST /documents (multipart: file | text)
    API->>Storage: Guarda archivo original (register_document, status="processing")
    API-->>Cliente: SSE: staging/uploading/embedding/...
    API->>API: Chunking jerárquico + Limpieza
    API->>API: Embeddings (Gemini -> Jina -> Local)
    API->>API: Indexación en FAISS (por document_id)
    API-->>Cliente: SSE "done" (document_id, status="ready", conteos)
    Note over Cliente: Con status="ready" ya se puede generar contenido con POST /documents/{id}/adapt
```

---

## 2. Endpoints disponibles

Base URL: `/api/v1` (en local, `http://localhost:8001/api/v1` si usas el `APP_PORT`
por defecto; en Docker, `http://localhost:8000/api/v1`).

---

### 2.1 Subir un documento e indexarlo

Registra el documento, guarda el archivo en el storage activo y ejecuta el
pipeline completo de ingesta + embeddings + indexado.

- **Método:** `POST`
- **Ruta:** `/documents`
- **Content-Type:** `multipart/form-data`

#### Parámetros del formulario

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :--- | :--- |
| `file` | File | Condicional | Archivo `.pdf`, `.md` o `.txt`. Requerido si no se envía `text`. |
| `text` | string | Condicional | Texto pegado directamente. Se guarda como `texto_pegado.txt`. |
| `title` | string | No | Título legible. Si no se envía, se deduce del nombre del archivo. |
| `use_ai_vision` | bool | No | Activa el análisis de imágenes del PDF (`pdf_vision_service`). Default `false`. |
| `user_id` | string (UUID) | No | Propietario. `null` hasta que exista login real. |

#### Query params

| Parámetro | Tipo | Default | Descripción |
| :--- | :--- | :--- | :--- |
| `stream` | bool | `true` | `true` devuelve un stream SSE de progreso; `false` devuelve el `DocumentRecord` final en JSON. |

#### Respuesta con `stream=true` — `200 OK` (`text/event-stream`)

Cada evento tiene la forma `data: {json}\n\n`:

```text
data: {"stage": "uploading", "message": "Preparando la ingesta…"}
data: {"stage": "embedding", "message": "Vectorizando lote 2/5…", "current": 2, "total": 5}
data: {"stage": "done", "document_id": "c39b33a7-...", "status": "ready", "title": "Manual OCI", "total_parents": 14, "total_children": 68, "storage_backend": "oci"}
```

Si el pipeline falla, el último evento lo indica explícitamente:

```text
data: {"stage": "failed", "message": "Error extracting text: PDF sin capa de texto."}
```

#### Respuesta con `stream=false` — `200 OK` (`DocumentRecord`)

```json
{
  "document_id": "c39b33a7-0275-4078-a3f2-187b5a198de2",
  "user_id": null,
  "title": "Manual de Arquitectura y Redes",
  "source_filename": "manual_redes.pdf",
  "object_key": "documents/c39b33a7-0275-4078-a3f2-187b5a198de2/manual_redes.pdf",
  "status": "ready",
  "storage_backend": "oci",
  "total_parents": 14,
  "total_children": 68,
  "error_message": null,
  "created_at": "2026-10-02T15:30:00Z",
  "updated_at": "2026-10-02T15:30:45Z"
}
```

#### Errores

| Código | Causa |
| :--- | :--- |
| `400 Bad Request` | Ni `file` ni `text`; formato no soportado (`Unsupported format: .docx`) o archivo mayor a `MAX_FILE_SIZE_MB`. |
| `422 Unprocessable Entity` | Faltan campos del formulario (`file`/`text`). |

---

### 2.2 Listar documentos

- **Método:** `GET`
- **Ruta:** `/documents`
- **Query params:** `user_id` (opcional) — filtra por propietario.

Devuelve una lista de `DocumentRecord` (los más recientes primero). Es la
fuente de la pantalla **Biblioteca**.

---

### 2.3 Consultar un documento

- **Método:** `GET`
- **Ruta:** `/documents/{document_id}`

Devuelve el `DocumentRecord` del documento o `404` si no existe. Se usa para
conocer `status` (`processing` / `ready` / `failed`), conteos y `object_key`.

---

### 2.4 Generar contenido a partir de un documento

Es la segunda llamada, rápida: la ingesta y los embeddings ya ocurrieron en el
`POST /documents`. Aquí solo se recupera contexto (`retrieval_service`) y se
ejecuta el orquestador multi-agente.

- **Método:** `POST`
- **Ruta:** `/documents/{document_id}/adapt`
- **Body (JSON):** parámetros de generación con alias en español.

```json
{
  "perfil_destinatario": "Estudiante universitario",
  "formato_salida": "flashcards",
  "nicho_sector": "general",
  "nivel_detalle": "didactic",
  "cantidad_generar": 5
}
```

Devuelve un `AdaptationResponse` (el mismo contrato que el frontend ya renderiza
para cada formato de salida). Requiere que el documento esté en estado `ready` y
con índice vectorial (`409 Conflict` en caso contrario; `404` si no existe).

---

### 2.5 Eliminar un documento

- **Método:** `DELETE`
- **Ruta:** `/documents/{document_id}`

Borra el documento de forma permanente en todas las capas (metadatos, storage
activo, índice FAISS y caché) mediante `document_deletion_service`. Devuelve la
confirmación de borrado o `404` si el documento no existe.

---

## 3. Consultar estado del procesamiento

> **Nota histórica:** en versiones anteriores existía un `GET /ingestion/status/{document_id}`
> para *polling*. Ese esquema fue reemplazado por el stream SSE del `POST /documents`
> y por `GET /documents/{document_id}`. Si necesitas consultar el estado después de
> cortar la conexión, usa `GET /documents/{document_id}`.

---

## 4. Ejemplos de integración

### JavaScript (navegador, sin dependencias)

```javascript
const form = new FormData();
form.append("file", fileInput.files[0]);
form.append("title", "Manual OCI");

const response = await fetch("http://localhost:8001/api/v1/documents?stream=true", {
  method: "POST",
  body: form,
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { value, done } = await reader.read();
  if (done) break;
  for (const line of decoder.decode(value).split("\n")) {
    if (line.startsWith("data: ")) {
      const event = JSON.parse(line.slice(6));
      // {stage, message} … "done" / "failed" al final
      console.log(event.stage, event.message);
    }
  }
}
```

---

## 5. Integración para el grupo de Agentes

Cuando el documento alcanza el estado `ready`:

1. El índice FAISS y sus metadatos jerárquicos quedan persistidos bajo la clave
   del `document_id` (`vector_store/{document_id}/`).
2. Cada `ChildChunk` y `ParentChunk` incluye `breadcrumb` con la ruta completa
   (ej. `Manual BX-200 > Capítulo 1 > 1.1 Descripción general`).
3. Para recuperar contexto relevante:

   ```python
   from app.services.retrieval_service import retrieve_context

   resultados = retrieve_context(
       document_id="c39b33a7-...",
       query="procedimiento de arranque",
       top_k=4,
   )
   for parent in resultados:
       print(parent["breadcrumb"])
   ```

---

<div align="right">

[Volver al README](../../../../README.md)

</div>

