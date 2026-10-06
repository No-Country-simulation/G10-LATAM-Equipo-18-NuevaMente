# Guía de Configuración y Despliegue en Oracle Cloud Infrastructure (OCI)

**Proyecto NuevaMente — Capa Always Free**

---

## 1. Cumplimiento del Presupuesto Always Free (\$0.00 COP / USD)

La infraestructura del sistema **NuevaMente** está diseñada para operar íntegramente dentro de los límites de la capa **Always Free de Oracle Cloud Infrastructure (OCI)**, garantizando que el proyecto no genere ningún tipo de cargo económico:

- **OCI Object Storage (Requisito Obligatorio MVP):**
  - **Límite Always Free:** 10 GB de almacenamiento total y hasta 50,000 solicitudes de API al mes.
  - **Bucket 1 (`nuevamente-documentos-fuente`):** Almacena los archivos originales subidos por el usuario (PDF, MD, TXT).
  - **Bucket 2 (`nuevamente-contenidos-educativos`):** Almacena los artefactos pedagógicos generados en formato JSON estructurado.

- **OCI Compute Instance (Diferencial Opcional):**
  - **Límite Always Free:** Hasta 4 OCPUs de procesador Ampere A1 (ARM) y 24 GB de memoria RAM o 2 instancias Micro AMD.

---

## 2. Configuración de OCI Object Storage

### 2.1 Estructura del Archivo de Credenciales (`~/.oci/config`)
Para conectar el backend FastAPI con OCI Object Storage mediante la librería oficial `oci` de Python, se requiere la presencia del archivo de configuración local:

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaaxxx...
fingerprint=aa:bb:cc:dd:ee:ff:11:22:33:44:55:66:77:88:99:00
tenancy=ocid1.tenancy.oc1..aaaaaaaayyy...
region=us-ashburn-1
key_file=~/.oci/oci_api_key.pem
```

### 2.2 Modo de Fallback Simulado (Local Mock Mode)
Para facilitar las pruebas de desarrollo sin exigir credenciales OCI activas en local, el servicio `OCIStorageService` del backend detecta automáticamente la ausencia de `~/.oci/config` y conmuta de forma transparente al almacenamiento en disco local (`backend/storage_mock/`), garantizando que la aplicación continúe funcionando sin errores.

---

## 3. Arquitectura del Servicio OCI en FastAPI (`oci_storage_service.py`)

El backend expone una interfaz desacoplada para interactuar con OCI:

```python
import oci
from app.core.config import settings

class OCIStorageService:
    def __init__(self):
        try:
            self.config = oci.config.from_file(settings.OCI_CONFIG_FILE)
            self.client = oci.object_storage.ObjectStorageClient(self.config)
            self.namespace = self.client.get_namespace().data
            self.is_connected = True
        except Exception as e:
            self.is_connected = False
            print(f"[OCI SDK] Configuración OCI no detectada. Operando en modo Local Mock.")

    def upload_json_artifact(self, bucket_name: str, object_name: str, json_data: dict) -> dict:
        if self.is_connected:
            body = json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8')
            self.client.put_object(self.namespace, bucket_name, object_name, body)
            return {"status": "completado", "bucket": bucket_name, "objeto_id": object_name}
        else:
            # Local persistence fallback
            save_path = f"storage_mock/{bucket_name}/{object_name}"
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            return {"status": "completado_mock_local", "bucket": bucket_name, "objeto_id": object_name}
```

---

## 4. Estructura del Objeto JSON Almacenado en OCI

Cada ejecución exitosa genera y persiste un objeto en el bucket `nuevamente-contenidos-educativos` con la siguiente estructura:

```json
{
  "status": "exito",
  "metadatos": {
    "perfil_aplicado": "Principiante",
    "formato_generado": "Flashcards",
    "tiempo_estimado_estudio_minutos": 5,
    "conceptos_clave": ["VCN", "Subredes", "Internet Gateway", "Security Lists"]
  },
  "contenido_adaptado": {
    "titulo": "Dominando Redes en la Nube (VCN) desde Cero",
    "introduccion_contextualizada": "Imagina la VCN como tu propio barrio privado dentro de Oracle Cloud...",
    "items": [
      {
        "frente": "¿Qué es una VCN en Oracle Cloud?",
        "dorso": "Es tu red virtual privada y personalizada dentro de la nube de Oracle.",
        "pista_didactica": "Piensa en ella como el terreno cercado donde residen tus servidores."
      }
    ]
  },
  "evaluacion_calidad": {
    "anclaje_fuente_score": 0.98,
    "claridad_pedagogica": "Alta",
    "observaciones": "Lenguaje ajustado con analogías para público principiante."
  },
  "almacenamiento_oci": {
    "bucket": "nuevamente-contenidos-educativos",
    "objeto_id": "contenido-vcn-principiante-flashcards-001.json",
    "status_upload": "completado"
  }
}
```
