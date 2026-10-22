# Configuración de Storages

> `docs/02-Instalacion/` · [Volver al README](../../README.md)

NuevaMente guarda **dos tipos de información** y hoy no existe un selector
único para ambos:

1. **Documentos originales** (PDF/MD/TXT) y su metadata.
2. **Artefactos generados** (JSON y PDF de las adaptaciones) y la metadata de
   biblioteca/papelera.

> **Importante:** en el MVP, OCI es el único backend completo. Supabase está
> implementado como **modo parcial para documentos originales y su metadata**;
> no guarda todavía los artefactos generados ni la biblioteca. El reemplazo
> total de proveedor está documentado como mejora post-MVP en
> [Mejoras Post-MVP](../05-Roadmap/Mejoras_Post_MVP.md).

---

## 1. Estado real de los backends

| Dato | OCI | Supabase | Local |
| :--- | :--- | :--- | :--- |
| Documento original | Sí | Sí | Sí, solo desarrollo |
| Metadata del documento | SQLite | Postgres/Supabase | SQLite |
| Artefactos generados | Sí | **No** (ruta sin conectar) | Sí, solo desarrollo |
| Biblioteca y papelera | SQLite | SQLite | SQLite |
| Vectores FAISS | Disco local | Disco local | Disco local |
| Frontend Angular | Sí | **No adaptado** | Sí |
| Gradio | Sí | Sí, recomendado | Sí |

`settings.resolve_storage_backend()` resuelve el backend efectivo en este orden:

1. Si `STORAGE_METHOD=supabase` y hay credenciales → **supabase**.
2. Si hay cliente OCI válido (`OCI_ENABLED`) → **oci**.
3. Si hay credenciales de Supabase → **supabase**.
4. En cualquier otro caso → **local**.

`STORAGE_METHOD` solo expresa una preferencia para **documentos originales**;
no cambia el destino de los artefactos generados ni de los vectores.

> **Supabase no usa SQLite.** En modo Supabase, la tabla `documents` vive en
> Postgres y el archivo original en Supabase Storage. Lo que sigue en SQLite es
> el resto del estado del MVP: usuarios/autenticación, contenidos, papelera y
> cola de trabajos.

---

## 2. Modo recomendado para el MVP: OCI

Es el único modo con el flujo completo: documentos, artefactos, cola de
persistencia y papelera.

```dotenv
# backend/.env
APP_ENV=development
STORAGE_METHOD=oci
ALLOW_LOCAL_STORAGE=false
OCI_AUTH_MODE=auto
OCI_REGION=mx-monterrey-1
OCI_NAMESPACE=
OCI_BUCKET_SOURCES=nuevamente-documentos-fuente
OCI_BUCKET_CONTENT=nuevamente-contenidos-educativos
```

La configuración detallada de buckets, compartments y policies está en
[Almacenamiento en OCI](../04-Documentacion/backend/storage/Almacenamiento_OCI.md).

---

## 3. Modo Supabase parcial (solo documentos)

Sirve para evitar OCI en la subida y el registro de documentos originales. Es
útil para probar con Gradio o para un piloto sin tarjeta de OCI, pero **no es un
reemplazo completo**.

### 3.1 Requisitos

- Proyecto Supabase con la key `service_role` (nunca la `anon/public`).
- Bucket privado `document-source`.
- Migraciones aplicadas en el SQL Editor:
  - `migrations/001_documents.sql`
  - `migrations/003_documents_storage_backend.sql`
- **No aplicar** `migrations/002_trash_system.sql` en Supabase: usa la tabla
  `contenidos`, que solo existe en SQLite.
- `migrations/002_adapted_contents.sql` existe, pero hoy no la usa el código.

### 3.2 Variables

```dotenv
# backend/.env
APP_ENV=development
STORAGE_METHOD=supabase
SUPABASE_URL=https://tuproyecto.supabase.co
SUPABASE_KEY=<service_role>
SUPABASE_BUCKET_DOCUMENTS=document-source
SUPABASE_BUCKET_ARTIFACTS=adapted-artifacts
ALLOW_LOCAL_STORAGE=true     # permite que los artefactos caigan en storage_mock/
```

> `SUPABASE_BUCKET_ARTIFACTS` se deja preparado para la mejora post-MVP; en el
> flujo actual los artefactos **no** se suben a ese bucket.

### 3.3 Qué funciona

- Subir un documento desde Gradio o desde el backend con `user_id=None`.
- Guardar el archivo original en el bucket `document-source`.
- Crear, listar y actualizar la fila en la tabla `documents`.
- Marcar el documento como `ready` o `failed`.
- Ingesta, chunking, embeddings y FAISS (siempre locales).
- Generación RAG y visualización del resultado en Gradio.

### 3.4 Qué no funciona

- Los JSON/PDF generados siguen yendo a OCI o a `storage_mock/`.
- La biblioteca, la papelera, la auditoría y la cola siguen en SQLite.
- El frontend Angular no puede listar ni subir documentos con un usuario
  autenticado: los IDs son `usr_ana_001` y Supabase espera `uuid`.
- `/health` sigue reportando el estado de OCI, no el de Supabase.
- No hay panel de configuración ni migración automática de datos.

### 3.5 Interfaz recomendada

Para este modo, usa **Gradio**:

```powershell
cd backend
uv run python ../frontend_gradio/app_gradio.py
```

Gradio no requiere login y llama al pipeline con `user_id=None`, por lo que evita
la incompatibilidad de IDs con Angular. Ver
[Frontend Gradio](../04-Documentacion/frontend/Gradio.md).

---

## 4. Modo local (solo desarrollo)

Si no hay OCI ni Supabase, el backend usa `storage_mock/` y SQLite. Es útil para
pruebas, no para producción.

```dotenv
APP_ENV=development
STORAGE_METHOD=oci
ALLOW_LOCAL_STORAGE=true
STORAGE_LOCAL_DIR=storage_mock
```

En producción (`APP_ENV=production` y `ALLOW_LOCAL_STORAGE=false`) el backend
falla de forma explícita si OCI no está disponible; no hace un fallback silencioso.

---

## 5. Verificación

```bash
cd backend
uv run --with email-validator --with genanki python -c "
from app.core.config import settings
print('backend efectivo:', settings.resolve_storage_backend())
print('supabase configurado:', settings.supabase_configured)
print('OCI habilitado:', settings.OCI_ENABLED)
"
```

Para el modo Supabase parcial:

1. Sube un documento desde Gradio.
2. Revisa el bucket `document-source` y la tabla `documents` en Supabase.
3. Verifica que el artefacto generado **no** aparece en Supabase; estará en
   OCI o en `storage_mock/`.
4. No uses Angular para validar este modo hasta completar la mejora post-MVP.

---

<div align="right">

[Volver al README](../../README.md) · [Mejoras Post-MVP](../05-Roadmap/Mejoras_Post_MVP.md)

</div>
