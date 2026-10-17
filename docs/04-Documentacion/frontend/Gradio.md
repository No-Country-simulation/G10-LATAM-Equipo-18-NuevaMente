# Frontend Gradio (interfaz de pruebas)

> `docs/04-Documentacion/frontend/` · [Volver al README](../../../README.md)

Interfaz mínima de pruebas (`frontend_gradio/app_gradio.py`) construida con
Gradio. Sirve para validar el pipeline completo (ingesta → chunking → embeddings
→ índice FAISS) y la generación, sin esperar a la SPA de Angular ni depender de
clientes externos como Postman o `cURL`. Consume la misma API REST del backend.

---

## 1. Explicación simple: ¿para qué sirve?

```text
[ Archivo: PDF / MD / TXT ]
            │
            ▼
┌──────────────────────────────────────────────────────────────┐
│ UI Gradio (frontend_gradio/app_gradio.py)                     │
│ 1. Subida y ejecución del pipeline (vía API REST)             │
│ 2. Resumen del documento (ID, estado, conteos)                │
│ 3. Exploración de documentos ya indexados                     │
└──────────────────────────────────────────────────────────────┘
```

Capacidades principales:

- Subir un documento y lanzar la ingesta, mostrando el avance.
- Ver el resumen del documento (`document_id`, `status`, totales de chunks).
- Explorar documentos previamente indexados.

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

5. La interfaz corre en proceso con los servicios del backend usando su mismo entorno Python y configuración `.env`, por lo que no es estrictamente obligatorio tener `uvicorn` activo en paralelo para probar el pipeline y la adaptación en Gradio.

---

## 3. Uso

1. **Subir documento:** arrastra o selecciona un archivo `.pdf`, `.md` o `.txt`
   (o pega texto), agrega un título opcional y envía.
2. **Seguir el progreso:** la UI refleja las etapas del pipeline y, al terminar,
   el resumen del documento.
3. **Explorar:** consulta los documentos ya indexados y su estado.

---

## 4. Solución de problemas

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

