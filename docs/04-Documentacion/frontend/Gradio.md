# Frontend Gradio (interfaz de pruebas)

> `docs/04-Documentacion/frontend/` · [Volver al README](../../../README.md)

Interfaz mínima de pruebas (`frontend_gradio/app_gradio.py`) construida con
Gradio. Sirve para validar el pipeline completo (ingesta → chunking → embeddings
→ índice FAISS) y la generación, sin esperar a la SPA de Angular ni depender de
clientes externos como Postman o `cURL`. Importa los servicios del backend **en
el mismo proceso** (no consume la API REST).

---

## 1. Explicación simple: ¿para qué sirve?

```text
[ Archivo: PDF / MD / TXT ]
            │
            ▼
┌──────────────────────────────────────────────────────────────┐
│ UI Gradio (frontend_gradio/app_gradio.py)                     │
│ 1. Subir documento + ejecutar el pipeline (in-process)        │
│ 2. Documentos existentes: tabla e inspección de chunks        │
│ 3. Generar con agentes (RAG): adaptación pedagógica          │
└──────────────────────────────────────────────────────────────┘
```

Capacidades principales:

- **Pestaña 1 — Subir documento:** subir un archivo o pegar texto, título
  opcional y un checkbox de **visión multimodal** para analizar diagramas e
  imágenes del PDF. Muestra el avance del pipeline.
- **Pestaña 2 — Documentos existentes:** tabla de documentos indexados e
  inspección de chunks/vectores de un documento concreto.
- **Pestaña 3 — Generar con agentes (RAG):** elige documento, formato y
  parámetros; muestra el resultado didáctico, el JSON completo del artefacto, las
  fuentes con su marca de verificación y las revisiones del grafo.

---

## 2. Cómo ejecutarlo

> **Importante:** ejecutar **desde la carpeta `backend`**. Ahí vive el entorno
> `uv` con las dependencias y el `.env` con las claves.

1. Abre una terminal en la raíz del proyecto.
2. Entra a `backend`:

   ```powershell
   cd backend
   ```

3. Ejecuta la interfaz:

   ```powershell
   uv run python ../frontend_gradio/app_gradio.py
   ```

4. Abre la URL local que muestra la consola (Gradio usa
   `http://127.0.0.1:7860` por defecto).

5. La interfaz corre en proceso con los servicios del backend usando su mismo entorno Python y configuración `.env`; **no** hace peticiones HTTP a la API, así que no necesitas `uvicorn` activo para probar el pipeline y la adaptación en Gradio.

---

## 3. Uso

1. **Subir documento:** arrastra o selecciona un archivo `.pdf`, `.md` o `.txt`
   (o pega texto), agrega un título opcional y envía.
2. **Seguir el progreso:** la UI refleja las etapas del pipeline y, al terminar,
   el resumen del documento.
3. **Explorar:** consulta los documentos ya indexados y su estado.

---

## 4. Modo Supabase parcial

Gradio es la **interfaz recomendada** para probar el modo Supabase parcial
(documentos originales y metadata). Llama al pipeline con `user_id=None`, por lo
que evita la incompatibilidad entre los IDs `usr_*` de SQLite y el
`documents.user_id uuid` de Supabase que bloquea a Angular.

Ten en cuenta que, en este modo:

- El documento original y su metadata van a Supabase.
- Los artefactos generados (JSON/PDF) siguen yendo a OCI o a `storage_mock/`;
  **no** se guardan en Supabase.
- La biblioteca, la papelera y la cola siguen en SQLite.
- No hay login ni separación de usuarios.

Configuración completa en
[Configuración de Storages](../../02-Instalacion/Configuracion_de_Storages.md).
El reemplazo total de proveedor está en
[Mejoras Post-MVP](../../05-Roadmap/Mejoras_Post_MVP.md).

---

## 5. Solución de problemas

- **`ModuleNotFoundError: No module named 'gradio'` o `No module named 'app'`:**
  se ejecutó sin `uv run` o desde una carpeta distinta a `backend`. Repite
  `cd backend` y luego `uv run python ../frontend_gradio/app_gradio.py`.
- **Errores de API key o de Gemini/Jina:** revisa `backend/.env`
   (`GEMINI_API_KEY`, `JINA_API_KEY`). Sin claves, el sistema conmuta al modelo
   local de embeddings.
- **El puerto 7860 está ocupado:** Gradio probará `7861`, `7862`, etc. Observa la
   URL emitida en la terminal.

---

<div align="right">

[Volver al README](../../../README.md)

</div>

