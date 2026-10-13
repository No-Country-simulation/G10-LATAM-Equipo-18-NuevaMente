"""
oci_backend.py

Purpose:
    Production Oracle Cloud Infrastructure (OCI) Object Storage backend.
    Supports both Instance Principals (VM production) and config_file (local dev).
    Enforces Always Free boundaries, deduplication, idempotent deletion,
    and strict error logging without silent fallbacks.
"""

import os
import io
import logging
from typing import Dict, Any, Optional, List

from app.core.config import settings
from app.services.storage.base import StorageBackend

logger = logging.getLogger("OciStorageBackend")


class OciStorageBackend(StorageBackend):
    """Implementación de StorageBackend para Oracle Cloud Infrastructure Object Storage."""

    _instance: Optional["OciStorageBackend"] = None
    _client = None
    _namespace: Optional[str] = None

    def __init__(self):
        self.auth_mode = settings.OCI_AUTH_MODE
        self.config_path = os.path.expanduser(settings.OCI_CONFIG_FILE)
        self.region = settings.OCI_REGION
        self.active_auth_mode = "none"
        self.is_connected = False
        self._last_error: Optional[str] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """
        Inicializa el cliente de OCI.
        Soporta modos:
          - 'auto': intenta Instance Principals; si falla y existe ~/.oci/config, usa config_file.
          - 'instance_principal': usa únicamente Instance Principals.
          - 'config_file': usa únicamente el archivo de configuración local.
        """
        try:
            import oci

            # Configurar estrategia de reintento estándar de OCI y timeouts estrictos
            retry_strategy = oci.retry.DEFAULT_RETRY_STRATEGY

            mode = (self.auth_mode or "auto").lower()
            initialized = False

            # 1. Intento con Instance Principals (en modo 'auto' o 'instance_principal')
            if mode in ("auto", "instance_principal"):
                # En Windows NT no se contacta el endpoint IMDS 169.254.169.254 para evitar bloqueos
                if os.name != "nt":
                    try:
                        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
                        client = oci.object_storage.ObjectStorageClient(
                            config={"region": self.region},
                            signer=signer,
                            retry_strategy=retry_strategy,
                            timeout=(10.0, 60.0),
                        )
                        # Validar conectividad efectiva
                        self._namespace = settings.OCI_NAMESPACE or client.get_namespace().data
                        self._client = client
                        self.active_auth_mode = "instance_principal"
                        self.is_connected = True
                        initialized = True
                        logger.info("OCI Object Storage conectado vía Instance Principals (Región: %s).", self.region)
                    except Exception as ip_err:
                        self._last_error = f"InstancePrincipals fallo: {str(ip_err)[:120]}"
                        logger.warning("Instance Principals no disponible: %s", ip_err)
                        if mode == "instance_principal":
                            raise ip_err
                elif mode == "instance_principal":
                    raise RuntimeError("Instance Principals solo es soportado en instancias de cómputo OCI (Linux).")

            # 2. Intento con Config File (en modo 'auto' como fallback, o explícito 'config_file')
            if not initialized and mode in ("auto", "config_file"):
                if os.path.exists(self.config_path):
                    try:
                        config = oci.config.from_file(self.config_path)
                        client = oci.object_storage.ObjectStorageClient(
                            config=config,
                            retry_strategy=retry_strategy,
                            timeout=(10.0, 60.0),
                        )
                        self._namespace = settings.OCI_NAMESPACE or client.get_namespace().data
                        self._client = client
                        self.active_auth_mode = "config_file"
                        self.is_connected = True
                        initialized = True
                        logger.info("OCI Object Storage conectado vía archivo config local (%s).", self.config_path)
                    except Exception as cfg_err:
                        self._last_error = f"config_file fallo: {str(cfg_err)[:120]}"
                        logger.warning("Fallo al conectar con config_file: %s", cfg_err)
                        if mode == "config_file":
                            raise cfg_err
                elif mode == "config_file":
                    raise FileNotFoundError(f"Archivo de configuración OCI no encontrado en: {self.config_path}")

            if not initialized:
                raise RuntimeError(
                    f"No se pudo inicializar OCI Object Storage en modo '{mode}'. "
                    f"Último error: {self._last_error or 'Sin credenciales válidas'}"
                )

        except Exception as exc:
            self.is_connected = False
            self._client = None
            self.active_auth_mode = "none"
            self._last_error = str(exc)
            if settings.APP_ENV == "production" and not settings.ALLOW_LOCAL_STORAGE:
                logger.critical("CRITICAL: Error conectando a OCI Object Storage en producción: %s", exc)
                raise RuntimeError(f"Fallo de conexión a OCI Object Storage en producción: {exc}")
            else:
                logger.warning("OCI Object Storage no disponible en desarrollo: %s.", exc)

    def self_check(self) -> Dict[str, Any]:
        """
        Autochequeo de OCI Object Storage:
          - Modo de autenticación activo
          - Conectividad a ambos buckets (fuentes y contenidos)
          - Verificación de acceso privado (NoPublicAccess) y tier Standard
        """
        report: Dict[str, Any] = {
            "status": "caido",
            "auth_mode": self.active_auth_mode,
            "region": self.region,
            "namespace": bool(self._namespace and self._namespace != "mock-namespace"),
            "buckets": {},
            "error": None,
        }

        if not self.is_connected or not self._client:
            report["error"] = self._last_error or "Cliente OCI no conectado."
            return report

        buckets_to_verify = [
            ("fuentes", settings.OCI_BUCKET_SOURCES),
            ("contenidos", settings.OCI_BUCKET_CONTENT),
        ]

        all_ok = True
        for key_label, bucket_name in buckets_to_verify:
            b_status: Dict[str, Any] = {"alcanzable": False, "tier": "Desconocido", "privado": False}
            try:
                b_info = self._client.get_bucket(self.namespace, bucket_name).data
                b_status["alcanzable"] = True
                tier = getattr(b_info, "storage_tier", "Standard")
                b_status["tier"] = tier
                public_access = getattr(b_info, "public_access_type", "NoPublicAccess")
                b_status["privado"] = (public_access == "NoPublicAccess")

                if tier != "Standard" or public_access != "NoPublicAccess":
                    all_ok = False
            except Exception as b_exc:
                all_ok = False
                b_status["error"] = str(b_exc)
            report["buckets"][bucket_name] = b_status

        report["status"] = "operativo" if all_ok else "degradado"
        return report

    @property
    def namespace(self) -> str:
        if not self._namespace:
            if self._client:
                self._namespace = self._client.get_namespace().data
            else:
                return "mock-namespace"
        return self._namespace

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Sube un archivo a OCI con validación de tamaño, metadatos limpios y deduplicación."""
        size_bytes = len(data)
        max_bytes = settings.STORAGE_MAX_UPLOAD_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise ValueError(
                f"El archivo supera el límite permitido de {settings.STORAGE_MAX_UPLOAD_MB}MB ({size_bytes / (1024 * 1024):.2f}MB)."
            )

        sha256_hash = self.compute_sha256(data)

        # Sanitizar metadatos para OCI (claves en opc-meta- y valores ASCII sin PII)
        opc_meta: Dict[str, str] = {"sha256": sha256_hash, "size-bytes": str(size_bytes)}
        if metadata:
            for k, v in metadata.items():
                safe_k = "".join(c for c in str(k).lower() if c.isalnum() or c == "-")[:32]
                safe_v = "".join(c for c in str(v) if ord(c) < 128)[:128]
                if safe_k and safe_v:
                    opc_meta[safe_k] = safe_v

        if not self.is_connected or not self._client:
            if settings.APP_ENV == "production" and not settings.ALLOW_LOCAL_STORAGE:
                logger.critical("CRITICAL: Intento de subida a OCI en producción sin cliente activo.")
                raise RuntimeError("OCI Object Storage no disponible en producción.")
            # Modo fallback local de desarrollo
            from app.services.storage.local_backend import LocalStorageBackend
            logger.warning("WARNING: Operando en fallback local de desarrollo para put_object.")
            return LocalStorageBackend().put_object(bucket_name, object_name, data, content_type, metadata)

        try:
            # Deduplicación: comprobar si ya existe con mismo tamaño y hash
            existing = self.head_object(bucket_name, object_name)
            if existing and existing.get("opc-meta-sha256") == sha256_hash:
                logger.info("Deduplicación OCI: objeto ya existente con idéntico SHA-256 (%s).", object_name)
                return {
                    "bucket": bucket_name,
                    "objeto_id": object_name,
                    "status_upload": "completado",
                    "deduplicado": True,
                    "sha256": sha256_hash,
                }

            # Subida directa a OCI
            import oci
            body_stream = io.BytesIO(data)
            resp = self._client.put_object(
                namespace_name=self.namespace,
                bucket_name=bucket_name,
                object_name=object_name,
                put_object_body=body_stream,
                content_type=content_type,
                opc_meta=opc_meta,
            )

            etag = resp.headers.get("etag", "")
            logger.info("Objeto subido exitosamente a OCI [%s/%s] (%d bytes).", bucket_name, object_name, size_bytes)
            return {
                "bucket": bucket_name,
                "objeto_id": object_name,
                "status_upload": "completado",
                "etag": etag,
                "sha256": sha256_hash,
                "size_bytes": size_bytes,
            }

        except Exception as exc:
            logger.error("Error al subir objeto [%s/%s] a OCI: %s", bucket_name, object_name, exc)
            if settings.APP_ENV == "production" and not settings.ALLOW_LOCAL_STORAGE:
                raise RuntimeError(f"Fallo en OCI Object Storage al persistir {object_name}: {exc}")
            raise

    def head_object(self, bucket_name: str, object_name: str) -> Optional[Dict[str, Any]]:
        """Consulta los metadatos de un objeto en OCI."""
        if not self.is_connected or not self._client:
            return None
        try:
            resp = self._client.head_object(self.namespace, bucket_name, object_name)
            return dict(resp.headers)
        except Exception:
            return None

    def get_object(self, bucket_name: str, object_name: str) -> Optional[bytes]:
        """Descarga los bytes de un objeto desde OCI."""
        if not self.is_connected or not self._client:
            if settings.ALLOW_LOCAL_STORAGE:
                from app.services.storage.local_backend import LocalStorageBackend
                return LocalStorageBackend().get_object(bucket_name, object_name)
            return None

        try:
            resp = self._client.get_object(self.namespace, bucket_name, object_name)
            return resp.data.content
        except Exception as exc:
            logger.error("Error al descargar objeto [%s/%s] desde OCI: %s", bucket_name, object_name, exc)
            return None

    def delete_object(self, bucket_name: str, object_name: str) -> bool:
        """Elimina un objeto de OCI de manera idempotente (404 = True)."""
        if not self.is_connected or not self._client:
            if settings.ALLOW_LOCAL_STORAGE:
                from app.services.storage.local_backend import LocalStorageBackend
                return LocalStorageBackend().delete_object(bucket_name, object_name)
            return False

        try:
            self._client.delete_object(self.namespace, bucket_name, object_name)
            logger.info("Objeto eliminado de OCI: [%s/%s].", bucket_name, object_name)
            return True
        except Exception as exc:
            status_code = getattr(exc, "status", None)
            if status_code == 404 or "404" in str(exc) or "NotAuthorizedOrNotFound" in str(exc):
                logger.info("Objeto [%s/%s] no encontrado al borrar (idempotente OK).", bucket_name, object_name)
                return True
            logger.error("Fallo al borrar objeto [%s/%s] en OCI: %s", bucket_name, object_name, exc)
            return False

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Comprueba si un objeto existe mediante head_object."""
        return self.head_object(bucket_name, object_name) is not None

    def list_objects(self, bucket_name: str, prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista los objetos de un bucket con prefijo opcional."""
        if not self.is_connected or not self._client:
            if settings.ALLOW_LOCAL_STORAGE:
                from app.services.storage.local_backend import LocalStorageBackend
                return LocalStorageBackend().list_objects(bucket_name, prefix)
            return []

        try:
            kwargs: Dict[str, Any] = {}
            if prefix:
                kwargs["prefix"] = prefix
            resp = self._client.list_objects(self.namespace, bucket_name, **kwargs)
            return [
                {
                    "name": obj.name,
                    "size": obj.size,
                    "time_created": str(obj.time_created),
                    "etag": obj.etag,
                }
                for obj in (resp.data.objects or [])
            ]
        except Exception as exc:
            logger.error("Error listando objetos en bucket [%s]: %s", bucket_name, exc)
            return []
