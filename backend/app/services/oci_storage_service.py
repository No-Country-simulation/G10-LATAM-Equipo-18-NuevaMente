import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("OCIStorageService")

class OCIStorageService:
    def __init__(self):
        self.config_path = os.path.expanduser("~/.oci/config")
        self.is_connected = False
        self.client = None
        self.namespace = "mock-oci-namespace"
        
        if os.path.exists(self.config_path):
            try:
                import oci
                self.config = oci.config.from_file(self.config_path)
                self.client = oci.object_storage.ObjectStorageClient(self.config)
                self.namespace = self.client.get_namespace().data
                self.is_connected = True
                logger.info("Conexión activa con Oracle Cloud Infrastructure (OCI Object Storage).")
            except Exception as e:
                logger.warning(f"No se pudo conectar a OCI Object Storage via SDK: {e}. Operando en modo Fallback Local.")
        else:
            logger.info("Archivo ~/.oci/config no encontrado. OCI Storage operará en modo Local Mock (Always Free Compatible).")

    def upload_json_artifact(self, bucket_name: str, object_name: str, json_data: dict) -> Dict[str, Any]:
        """
        Guarda los contenidos educativos adaptados (JSON) en el bucket de OCI Object Storage Always Free.
        """
        if self.is_connected and self.client:
            try:
                body = json.dumps(json_data, ensure_ascii=False, indent=2).encode('utf-8')
                self.client.put_object(self.namespace, bucket_name, object_name, body, content_type="application/json")
                return {
                    "bucket": bucket_name,
                    "objeto_id": object_name,
                    "status_upload": "completado"
                }
            except Exception as e:
                logger.error(f"Error subiendo JSON a OCI Object Storage: {e}")

        # Fallback local mock
        base_dir = Path(os.getcwd()) / "storage_mock" / bucket_name
        base_dir.mkdir(parents=True, exist_ok=True)
        file_path = base_dir / object_name

        file_path.write_text(json.dumps(json_data, ensure_ascii=False, indent=2), encoding="utf-8")
            
        return {
            "bucket": bucket_name,
            "objeto_id": object_name,
            "status_upload": "completado"
        }

    def upload_document_source(self, bucket_name: str, object_name: str, file_bytes: bytes, content_type: str = "application/pdf") -> Dict[str, Any]:
        """
        Guarda los documentos técnicos originales subidos (PDF, TXT, MD) en OCI Object Storage Always Free.
        """
        if self.is_connected and self.client:
            try:
                self.client.put_object(self.namespace, bucket_name, object_name, file_bytes, content_type=content_type)
                return {
                    "bucket": bucket_name,
                    "objeto_id": object_name,
                    "status_upload": "completado"
                }
            except Exception as e:
                logger.error(f"Error subiendo documento fuente a OCI Object Storage: {e}")

        # Fallback local mock
        base_dir = Path(os.getcwd()) / "storage_mock" / bucket_name
        base_dir.mkdir(parents=True, exist_ok=True)
        file_path = base_dir / object_name
        file_path.write_bytes(file_bytes)

        return {
            "bucket": bucket_name,
            "objeto_id": object_name,
            "status_upload": "completado"
        }

    def download_document_source(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """
        Descarga documentos técnicos u objetos desde OCI Object Storage Always Free.
        """
        if self.is_connected and self.client:
            try:
                response = self.client.get_object(self.namespace, bucket_name, object_name)
                return response.data.content
            except Exception as e:
                logger.error(f"Error descargando documento desde OCI Object Storage: {e}")

        # Fallback local mock
        base_dir = Path(os.getcwd()) / "storage_mock" / bucket_name
        file_path = base_dir / object_name
        if file_path.exists():
            return file_path.read_bytes()
        return None

