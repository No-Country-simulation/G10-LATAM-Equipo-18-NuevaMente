# Guía de Configuración y Despliegue en Oracle Cloud Infrastructure (OCI)

**Proyecto NuevaMente — Capa Always Free (Región: mx-monterrey-1)**

---

## 1. Arquitectura y Presupuesto Always Free ($0.00 COP / USD)

La infraestructura de **NuevaMente** está construida para operar dentro de la capa **Always Free de Oracle Cloud Infrastructure (OCI)** sin generar costos:

- **OCI Object Storage (Tier Standard, Privado):**
  - **Bucket Fuentes (`nuevamente-documentos-fuente`):** Almacena documentos originales subidos por el usuario (PDF, MD, TXT).
  - **Bucket Contenidos (`nuevamente-contenidos-educativos`):** Almacena los artefactos pedagógicos generados en formato JSON estructurado canónico.
  - **Jerarquía Canónica de Claves:**
    - Documentos: `usuarios/{user_id}/documentos/{sha256}/{nombre_saneado}`
    - Contenidos: `usuarios/{user_id}/contenidos/{content_id}/v{version}.json`
- **OCI Compute Instance (Ubuntu en mx-monterrey-1):**
  - Hospeda la API FastAPI (puerto 8000 / proxy Nginx 80) y la SPA Angular compilada.

---

## 2. Autenticación Segura sin Claves: Instance Principals

En producción en la VM de OCI, **NO se almacenan claves privadas, tokens ni archivos `~/.oci/config`**.
El backend utiliza **Instance Principals** de OCI mediante el SDK oficial:

```python
signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
```

### Configuración en la Consola OCI (IAM):

1. **Crear Dynamic Group:**
   - Nombre: `NuevamenteVMGroup`
   - Regla de coincidencia:
     ```text
     ANY {instance.id = 'ocid1.instance.oc1.mx-monterrey-1.<TU_OCID_DE_INSTANCIA>'}
     ```

2. **Crear IAM Policy:**
   - Nombre: `NuevamenteStoragePolicy`
   - Enunciados:
     ```text
     Allow dynamic-group NuevamenteVMGroup to manage objects in compartment <TU_COMPARTIMENTO> where any {target.bucket.name = 'nuevamente-documentos-fuente', target.bucket.name = 'nuevamente-contenidos-educativos'}
     Allow dynamic-group NuevamenteVMGroup to read buckets in compartment <TU_COMPARTIMENTO>
     ```

---

## 3. Variables de Entorno del Backend en la VM

Crear o editar el archivo de configuración del entorno (ej. `/etc/nuevamente.env` o `/home/ubuntu/app/backend/.env`):

```bash
# Entorno de ejecución
APP_ENV=production
ALLOW_LOCAL_STORAGE=false
STORAGE_METHOD=oci

# Configuración OCI Object Storage
OCI_ENABLED=true
OCI_AUTH_MODE=instance_principal
OCI_REGION=mx-monterrey-1
OCI_BUCKET_SOURCES=nuevamente-documentos-fuente
OCI_BUCKET_CONTENT=nuevamente-contenidos-educativos

# LLM Providers (sustituir con claves reales; nunca commitear)
GEMINI_API_KEY=tu_clave_gemini
GROQ_API_KEY=tu_clave_groq
COHERE_API_KEY=tu_clave_cohere
```

---

## 4. Configuración del Servicio Systemd (`nuevamente.service`)

Archivo de unidad en `/etc/systemd/system/nuevamente.service`:

```ini
[Unit]
Description=NuevaMente FastAPI Backend Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/app/backend
EnvironmentFile=/etc/nuevamente.env
ExecStart=/home/ubuntu/app/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## 5. Cola de Persistencia en Segundo Plano y Diagnóstico

- **Cola SQLite Concurrente:** Toda persistencia a OCI se encola de forma inmediata en la tabla `storage_jobs`.
- **Autochequeo en Startup:** Al iniciar el backend, se ejecuta `self_check()`, validando acceso a ambos buckets y tier Standard sin acceso público.
- **Sin Fallback Silencioso:** En `APP_ENV=production`, cualquier error de autenticación o cuota en OCI eleva alertas y registra el estado `error` en `/api/almacenamiento/estado/{content_id}` con opción de reintento manual o en background.
- **Herramienta de Diagnóstico:**
  ```bash
  python backend/scripts/check_services.py
  ```
  Verifica conectividad LLM, Embeddings y OCI Object Storage.

---

## 6. Migración Idempotente desde Almacenamiento Local

Si existían archivos acumulados en `storage_mock/`:

1. Simulación sin cambios:
   ```bash
   python backend/scripts/migrate_local_to_oci.py --dry-run
   ```
2. Ejecución real:
   ```bash
   python backend/scripts/migrate_local_to_oci.py
   ```
   El script calcula SHA-256 de cada archivo, verifica con `head_object` si ya existe en OCI y solo transfiere objetos no duplicados.
