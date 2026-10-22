# Configuración de Storages

> `docs/02-Instalacion/` · [Volver al README](../../README.md)

NuevaMente guarda dos cosas: el **documento original** y los **artefactos
generados** (contenido educativo). El backend elige el almacenamiento por
disponibilidad, con respaldo a disco local.

---

## 1. Cómo se decide el backend

`settings.resolve_storage_backend()` resuelve el backend efectivo en este orden:

1. Si `STORAGE_METHOD=supabase` y hay credenciales → **supabase**.
2. Si `OCI_ENABLED` (hay cliente OCI válido) → **oci**.
3. Si hay credenciales de Supabase → **supabase**.
4. En cualquier otro caso → **local** (`LOCAL_STORAGE_DIR`, por defecto
   `storage_mock`).

`STORAGE_METHOD` solo expresa una **preferencia**; nunca fuerza un backend roto.

```dotenv
# backend/.env
STORAGE_METHOD=oci            # 'oci' (default) o 'supabase'
ALLOW_LOCAL_STORAGE=false     # habilita explícitamente el respaldo en disco
STORAGE_LOCAL_DIR=storage_mock
STORAGE_MAX_UPLOAD_MB=25
STORAGE_USER_QUOTA_MB=200
STORAGE_SOFT_LIMIT_GIB=15
```

---

## 2. Supabase

```dotenv
SUPABASE_URL=https://tuproyecto.supabase.co
SUPABASE_KEY=<service_role>   # NO la anon/public; nunca se versiona
SUPABASE_BUCKET_DOCUMENTS=document-source
SUPABASE_BUCKET_ARTIFACTS=adapted-artifacts
```

Pasos en el dashboard (crear bucket privado, tabla `documents`, obtener
credenciales) y uso en código:
[Almacenamiento con Supabase](../04-Documentacion/backend/storage/Almacenamiento_Supabase.md).

---

## 3. OCI Object Storage

```dotenv
OCI_AUTH_MODE=instance_principal   # o 'auto'
OCI_REGION=mx-monterrey-1
OCI_NAMESPACE=
OCI_BUCKET_SOURCES=nuevamente-documentos-fuente
OCI_BUCKET_CONTENT=nuevamente-contenidos-educativos
# OCI_COMPARTMENT_OCID=ocid1.compartment.oc1..   # opcional
```

> `OCI_ENABLED` **no** es una variable de entorno: es una propiedad calculada de
> `settings` (`config.py`) que devuelve `True` cuando `get_oci_client()` logra
> construir un cliente válido. Configurarlo en `.env` no tiene efecto.
> `OCI_COMPARTMENT_OCID` se lee con `os.getenv` en
> `app/infrastructure/oci_client.py`.

El detalle de compartments, policies y verificación de credenciales:
[Almacenamiento con OCI](../04-Documentacion/backend/storage/Almacenamiento_OCI.md).

---

## 4. Verificación

```bash
cd backend
uv run --with email-validator --with genanki python -c "
from app.core.config import settings
print('backend efectivo:', settings.resolve_storage_backend())
print('supabase configurado:', settings.supabase_configured)
print('OCI habilitado:', settings.OCI_ENABLED)
"
```

---

<div align="right">

[Volver al README](../../README.md)

</div>

