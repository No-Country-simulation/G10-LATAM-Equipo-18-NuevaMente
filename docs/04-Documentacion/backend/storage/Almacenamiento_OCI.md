# Almacenamiento en OCI Object Storage

> `docs/04-Documentacion/backend/storage/` · [Volver al README](../../../../README.md)

Dos caminos válidos. El código del backend soporta ambos; lo único que cambia es dónde viven los buckets y qué policy se usa.

---

## Antes de empezar: cómo funciona (en breve)

* **Compartment:** Carpeta lógica donde vive cada recurso. Un bucket pertenece a un solo compartment (el que eliges al crear; por defecto queda en `root`).
* **Usuario/Grupo:** Identidad. El backend firma con la API key de un usuario.
* **Policy:** Quién puede hacer qué en qué compartment. Créala **siempre** en el compartment `root` (el selector superior debe decir `root`): una policy creada dentro de un compartment solo aplica a ese compartment y sus hijos.
* **`~/.oci/config`:** Solo identifica al usuario, tenancy y región. No contiene compartments.

---

## Camino A — Buckets en el compartment root (el más simple)

Los buckets quedan en `root` y la policy de acceso cubre toda la tenancy. No se configura nada extra en el backend.

### Pasos (una sola vez, consola)

1. **Identity & Security → Compartments:** Crear nuevamente (opcional — en este camino ni siquiera hace falta).
2. **Storage → Object Storage → Buckets → Create bucket** (sin seleccionar compartment → queda en `root`):
   * `nuevamente-documentos-fuente` (Standard, Private)
   * `nuevamente-contenidos-educativos` (Standard, Private)
3. **Identity & Security → Domains/Groups → Create group:** `nuevamente-backend`.
4. **Identity & Security → Policies → Create policy** (asegúrate de estar en el compartment `root`):
   ```text
   Allow group nuevamente-backend to manage object-family in tenancy
   ```
5. **Identity → Users → Create user:** `nuevamente-backend` → añádelo al grupo.
6. **API keys → Add API key → Generate API key pair:** Descarga la clave privada y copia el preview de configuración.

### Credenciales locales

Crea o edita el archivo `C:\Users\<tu-usuario>\.oci\config` (con el preview que te dio la consola):

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaa...
fingerprint=aa:bb:...
tenancy=ocid1.tenancy.oc1..aaaa...
region=mx-monterrey-1
key_file=C:\Users\<tu-usuario>\.oci\oci_api_key.pem
```

> `region` debe coincidir con `OCI_REGION` del `.env` del backend (por defecto,
> `mx-monterrey-1`).

Guarda el archivo .pem (que creará OCI) en la carpeta ~\.oci\

### Backend

Sin `OCI_COMPARTMENT_OCID` (queda vacío = `root`). Crea los buckets en `root` y la política en tenancy los cubre.

---

## Camino B — Buckets en el compartment nuevamente (ordenado)

Todo el almacenamiento vive en su propio compartment. Requiere una variable extra en el backend.

### Pasos (una sola vez, consola)

1. **Identity & Security → Compartments → Create compartment:** `nuevamente`.
2. **Storage → Object Storage → Buckets → Create bucket** con el selector *"Create in compartment: nuevamente"*:
   * `nuevamente-documentos-fuente` (Standard, Private)
   * `nuevamente-contenidos-educativos` (Standard, Private)
   *(O crearlos más tarde desde la consola, ver abajo).*
3. **Identity & Security → Domains/Groups → Create group:** `nuevamente-backend`.
4. **Identity & Security → Policies → Create policy** (en el compartment `root`, con target al compartment):
   ```text
   Allow group nuevamente-backend to manage object-family in compartment nuevamente
   ```
5. **Identity → Users → Create user:** `nuevamente-backend` → añádelo al grupo.
6. **API keys → Add API key** (del usuario `nuevamente-backend`) → descarga la clave privada y copia el preview.

### Credenciales locales

Igual que el Camino A (el `~/.oci/config` no cambia):

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaa...
fingerprint=aa:bb:...
tenancy=ocid1.tenancy.oc1..aaaa...
region=mx-monterrey-1
key_file=C:\Users\<tu-usuario>\.oci\oci_api_key.pem
```

Guarda el archivo .pem (que creará OCI) en la carpeta ~\.oci\

### El dato clave: `OCI_COMPARTMENT_OCID`

`ensure_bucket` es una operación que realizas desde la consola o la CLI de OCI (el
backend no la ejecuta al arrancar). Cuando crea un bucket, OCI exige el OCID del
compartment. El backend resuelve el compartment así
(`app/infrastructure/oci_client.py`):

```python
_compartment_id = os.getenv("OCI_COMPARTMENT_OCID") or config.get("tenancy")
```

* Si `OCI_COMPARTMENT_OCID` está **vacío** → usa el OCID de la tenancy = `root` (Camino A).
* Si quieres los buckets en `nuevamente` → tienes que pasarle el OCID de ese compartment, porque no viene en `~/.oci/config` ni se deduce automáticamente.

### Dónde conseguirlo
* **Ruta:** *Identity & Security → Compartments → fila "nuevamente" → Copy OCID* (empieza con `ocid1.compartment.oc1..`).

### Dónde ponerlo (configuración del entorno)
```env
# backend/.env (local) — o secret con el MISMO nombre en la plataforma de despliegue
OCI_COMPARTMENT_OCID=ocid1.compartment.oc1..aaaa...
```

**Advertencia:** Si lo dejas vacío, los buckets deben existir en `root` y una policy en el compartment `nuevamente` no los cubrirá → generará un error 404 de permisos. Los buckets en `root` además no se pueden "mover" directamente a un compartment: hay que borrarlos y recrearlos.

---

## Comparación rápida

| Característica | Camino A (root) | Camino B (nuevamente) |
| :--- | :--- | :--- |
| **Dónde viven los buckets** | `root` | Compartment `nuevamente` |
| **Policy (crear en root)** | `... manage object-family in tenancy` | `... manage object-family in compartment nuevamente` |
| **`OCI_COMPARTMENT_OCID`** | Vacío (default) | OCID del compartment `nuevamente` |
| **Esfuerzo** | Mínimo | +1 variable, +1 compartment |
| **Ideal para** | MVP / desarrollo rápido | Aislar el proyecto en su propio compartment |

---

## Verificación (ambos caminos)

Ejecuta el siguiente comando para comprobar que la conexión y los permisos son correctos:

```bash
cd backend
uv run --with email-validator --with genanki python -c "
from app.infrastructure.oci_client import get_oci_client, get_oci_namespace, get_oci_compartment_id
from app.services.storage.oci_backend import OciStorageBackend

c = get_oci_client()
ns = get_oci_namespace()
print('namespace  :', ns)
print('compartment:', get_oci_compartment_id())

backend = OciStorageBackend()
print('self-check :', backend.self_check())
"
```

Debe imprimir un `self-check` con los buckets visibles o un estado correcto de la
conexión (namespace, compartment y buckets accesibles). Si aparece un error
`404`/`403`, revisa:
1. Que el usuario `nuevamente-backend` pertenezca al grupo correcto.
2. Que la policy esté creada en el compartment `root`.
3. Dale unos segundos de propagación a OCI tras crear recursos de IAM.

---

<div align="right">

[Volver al README](../../../../README.md)

</div>

