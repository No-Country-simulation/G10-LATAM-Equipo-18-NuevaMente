# Interfaz Temporal de Pruebas (frontend_temp) — NuevaMente

Este documento describe la arquitectura, propósito e instrucciones para ejecutar y utilizar la interfaz gráfica temporal de pruebas (`frontend_temp/upload_test_ui.py`) desarrollada con Gradio en NuevaMente.

---

## 1. Explicación Simple: ¿Qué es y Para Qué Sirve?

`upload_test_ui.py` es una interfaz interactiva de prueba rápida (throwaway UI) diseñada para validar todo el flujo de ingesta, particionado en chunks, generación de embeddings (con fallback automático) e indexación vectorial en FAISS de manera visual, sin necesidad de esperar por el frontend definitivo ni depender de clientes externos como Postman o cURL.

```
[ Archivo de Entrada: PDF / MD / TXT ]
                  │
                  ▼
┌────────────────────────────────────────────────────────┐
│ Interfaz Temporal Gradio (upload_test_ui.py)           │
│                                                        │
│ 1. Ejecución del Pipeline:                             │
│    - Almacenamiento y registro (Supabase/Metadata)     │
│    - Chunking jerárquico Padre-Hijo                    │
│    - Generación de Embeddings (Gemini -> Jina -> Local)│
│    - Indexación en almacén vectorial FAISS             │
│                                                        │
│ 2. Visualización e Inspección Inmediata:               │
│    - Resumen del documento (ID, estado, conteos)       │
│    - Identificación del modelo y proveedor activo       │
│    - Muestra de 4 chunks clave (0, 1, N-2, N-1)        │
│    - Muestra numérica de vectores y norma L2           │
│    - Explorador de documentos previamente indexados    │
└────────────────────────────────────────────────────────┘
```

### Capacidades Principales
- **Prueba End-to-End:** Ejecuta la función `process_and_index_document()` del backend directamente en tiempo real.
- **Identificación de Modelos:** Muestra si el documento fue procesado con Google Gemini (`models/gemini-embedding-001@768`), Jina AI (`jina-embeddings-v3@768`) o el modelo Local (`sentence-transformers/...@768`).
- **Inspección de Muestra de Chunks:** Muestra de forma legible el fragmento inicial (0), el segundo (1), el penúltimo (N-2) y el último (N-1), junto a sus IDs, breadcrumbs y longitudes.
- **Verificación Numérica de Embeddings:** Extrae los vectores directamente desde el índice FAISS, mostrando los primeros y últimos valores de punto flotante y confirmando la norma L2 unitaria ($\approx 1.0000$).
- **Historial e Inspección de Existentes:** Permite consultar la lista de documentos en el repositorio y cargar la estructura vectorial de cualquier `document_id` previo.

---

## 2. Instrucciones de Ejecución Paso a Paso

> [!IMPORTANT]
> **Ubicación Obligatoria en la Carpeta `backend`**
> La aplicación debe ejecutarse **exclusivamente posicionándose primero dentro de la carpeta `backend`** antes de invocar `uv run`. 
> 
> **¿Por qué?**
> 1. En `backend/` reside el entorno virtual administrado por `uv` con todas las dependencias instaladas (`gradio`, `faiss-cpu`, `google-genai`, `requests`, `numpy`, etc.).
> 2. En `backend/.env` se encuentran las variables de entorno y claves de API necesarias.
> 3. Evita conflictos de importación (`sys.path`) del paquete `app.*`.

### Pasos para iniciar la interfaz:

1. **Abrir la terminal** en la raíz del proyecto.
2. **Navegar a la carpeta `backend`:**
   ```powershell
   cd backend
   ```
3. **Ejecutar el script de la interfaz con `uv run`:**
   ```powershell
   uv run python ../frontend_temp/upload_test_ui.py
   ```
4. **Abrir en el navegador:**
   Una vez iniciado, Gradio mostrará una URL local en la consola (por defecto):
   ```
   Running on local URL:  http://127.0.0.1:7860
   ```
   Abre ese enlace en tu navegador para interactuar con la interfaz.

---

## 3. Guía de Uso de la Interfaz

La aplicación cuenta con dos pestañas principales:

### Pestaña 1: "Subir documento"
1. **Seleccionar archivo:** Arrastra o selecciona un archivo con extensión permitida (`.pdf`, `.md`, `.markdown`, `.txt`).
2. **Título opcional:** Puedes ingresar un título legible o dejarlo en blanco para que use el nombre del archivo.
3. **Procesar documento:** Haz clic en el botón principal **"Procesar documento"**.
   - Verás un mensaje en tiempo real: `⏳ Procesando documento... esto puede tardar varios segundos...`
   - Al finalizar, se despliega:
     - **Resumen:** `document_id`, `status` (`ready`), `object_key`, total de chunks padres e hijos.
     - **Modelo y Almacén Vectorial:** Proveedor detectado (Gemini / Jina / Local), dimensión (768), vectores indexados en FAISS.
     - **Muestras de Chunks y Vectores:** 4 bloques detallados con los fragmentos iniciales y finales y sus respectivos vectores normalizados.

### Pestaña 2: "Documentos existentes"
1. **Listado general:** Muestra una tabla con todos los documentos previamente procesados y guardados en el repositorio local.
2. **Actualizar listado:** Botón para refrescar los registros si se subieron documentos en paralelo.
3. **Inspección sin re-subida:**
   - Copia cualquier `document_id` de la tabla.
   - Pégalo en el campo **"ID del Documento (document_id)"**.
   - Haz clic en **"Inspeccionar Chunks y Vectores"**.
   - La interfaz cargará el almacén FAISS correspondiente (`vector_store/{document_id}/`) y mostrará sus chunks y vectores de muestra de inmediato.

---

## 4. Solución de Problemas Comunes (Troubleshooting)

- **`ModuleNotFoundError: No module named 'gradio'` o `No module named 'app'`:**
  - **Causa:** El comando se ejecutó sin `uv run` o desde una carpeta distinta a `backend`.
  - **Solución:** Asegúrate de ejecutar `cd backend` y luego `uv run python ../frontend_temp/upload_test_ui.py`.
- **`ValueError: JINA_API_KEY is missing or invalid` o fallos en Gemini:**
  - **Causa:** No se definieron las claves en `backend/.env`.
  - **Solución:** Revisa tu archivo `backend/.env` para incluir `GEMINI_API_KEY` o `JINA_API_KEY`. Si ninguna clave está disponible, el sistema conmutará automáticamente al modelo local (`sentence-transformers`).
- **El puerto 7860 está ocupado:**
  - Gradio intentará automáticamente el puerto `7861`, `7862`, etc. Observa la URL emitida en la terminal.
