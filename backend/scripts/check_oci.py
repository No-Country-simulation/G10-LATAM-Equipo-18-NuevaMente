#!/usr/bin/env python3
"""
check_oci.py

Diagnóstico y verificación de conectividad con OCI Object Storage Always Free.
Verifica:
  - Modo de autenticación (Instance Principals o config_file).
  - Región y Namespace.
  - Existencia de ambos buckets (fuentes y contenidos educativos).
  - Acceso privado (NoPublicAccess) y almacenamiento tier Standard.
  - Ciclo de vida completo (PUT -> HEAD -> GET -> DELETE) en _healthcheck/ con latencias.
  - Traducción amigable de errores sin exponer secretos.
"""

import sys
import os
import time
from typing import Tuple, Dict, Any

# Inserción de ruta raíz del backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.services.storage import get_storage_backend, OciStorageBackend


def translate_oci_error(error: Exception) -> str:
    msg = str(error)
    if "NotAuthenticated" in msg:
        return "NotAuthenticated: Revisa la regla del Dynamic Group en OCI o la validez de la clave/token."
    elif "NotAuthorizedOrNotFound" in msg or "404" in msg:
        return "NotAuthorizedOrNotFound: Falta la IAM Policy (ej. 'Allow dynamic-group ... to manage objects in compartment'), o el nombre de bucket/namespace es incorrecto."
    elif "ConnectTimeout" in msg or "timeout" in msg.lower():
        return "Timeout de red: Revisa la salida a internet (NAT Gateway / Internet Gateway) y Security Lists de la VM."
    return f"Error OCI: {msg}"


def run_oci_check() -> int:
    print("=" * 70)
    print("  NUEVAMENTE - VERIFICACIÓN DE OCI OBJECT STORAGE (ALWAYS FREE)")
    print("=" * 70)

    auth_mode = settings.OCI_AUTH_MODE
    region = settings.OCI_REGION
    bucket_sources = settings.OCI_BUCKET_SOURCES
    bucket_content = settings.OCI_BUCKET_CONTENT

    print(f"[*] Modo de Autenticación configurado: {auth_mode}")
    print(f"[*] Región OCI: {region}")
    print(f"[*] Bucket de Documentos Fuente: {bucket_sources}")
    print(f"[*] Bucket de Contenidos Educativos: {bucket_content}")

    try:
        backend = get_storage_backend()
    except Exception as exc:
        print(f"\n[FAIL] Error inicializando Storage Backend: {translate_oci_error(exc)}")
        return 1

    if not isinstance(backend, OciStorageBackend):
        print("\n[WARN] El backend activo es LocalStorageBackend (modo local/mock).")
        print("       Para probar OCI real, configure OCI_ENABLED=true y credenciales válidas.")
        return 0

    if not backend.is_connected or not backend._client:
        print("\n[FAIL] No hay conexión activa con el cliente de OCI Object Storage.")
        return 1

    client = backend._client
    namespace = backend.namespace
    print(f"[*] Namespace OCI detectado: {namespace[:4]}...{namespace[-4:] if len(namespace) > 8 else ''}")

    # 1. Comprobar existencia y configuración de ambos buckets
    buckets_to_check = [
        ("Fuentes", bucket_sources),
        ("Contenidos", bucket_content),
    ]

    for label, b_name in buckets_to_check:
        print(f"\n--> Verificando Bucket de {label} ('{b_name}')...")
        try:
            t0 = time.time()
            b_info = client.get_bucket(namespace, b_name).data
            lat = (time.time() - t0) * 1000
            print(f"    ✓ Bucket encontrado ({lat:.1f}ms).")

            # Validar Tier Standard
            storage_tier = getattr(b_info, "storage_tier", "Standard")
            print(f"    ✓ Nivel de Almacenamiento: {storage_tier}")
            if storage_tier != "Standard":
                print(f"    [WARN] El bucket no está en tier Standard (detectado: {storage_tier}).")

            # Validar Acceso Privado
            public_access = getattr(b_info, "public_access_type", "NoPublicAccess")
            print(f"    ✓ Tipo de Acceso Público: {public_access}")
            if public_access != "NoPublicAccess":
                print(f"    [WARN] El bucket no es completamente privado (debe ser NoPublicAccess).")

        except Exception as exc:
            print(f"    [FAIL] No se pudo acceder al bucket '{b_name}': {translate_oci_error(exc)}")
            return 1

    # 2. Prueba de Ciclo Completo (Ida y Vuelta) con objeto temporal
    healthcheck_key = f"_healthcheck/ping_{int(time.time())}.txt"
    test_payload = b"NuevaMente OCI Object Storage Healthcheck - Always Free Standard Tier"

    print(f"\n--> Ejecutando prueba de ciclo de vida (PUT -> HEAD -> GET -> DELETE) en '{healthcheck_key}'...")
    try:
        # PUT
        t0 = time.time()
        backend.put_object(
            bucket_name=bucket_content,
            object_name=healthcheck_key,
            data=test_payload,
            content_type="text/plain",
            metadata={"check": "healthcheck_ping"},
        )
        lat_put = (time.time() - t0) * 1000
        print(f"    ✓ PUT exitoso ({lat_put:.1f}ms)")

        # HEAD
        t0 = time.time()
        head_data = backend.head_object(bucket_name=bucket_content, object_name=healthcheck_key)
        lat_head = (time.time() - t0) * 1000
        if not head_data:
            print("    [FAIL] HEAD devolvió None para el objeto recién subido.")
            return 1
        print(f"    ✓ HEAD exitoso ({lat_head:.1f}ms)")

        # GET
        t0 = time.time()
        downloaded = backend.get_object(bucket_name=bucket_content, object_name=healthcheck_key)
        lat_get = (time.time() - t0) * 1000
        if downloaded != test_payload:
            print("    [FAIL] Los bytes descargados no coinciden con el contenido original.")
            return 1
        print(f"    ✓ GET exitoso ({lat_get:.1f}ms, {len(downloaded)} bytes intactos)")

        # DELETE (Idempotente)
        t0 = time.time()
        del_ok = backend.delete_object(bucket_name=bucket_content, object_name=healthcheck_key)
        lat_del = (time.time() - t0) * 1000
        if not del_ok:
            print("    [FAIL] DELETE no retornó confirmación.")
            return 1
        print(f"    ✓ DELETE exitoso e idempotente ({lat_del:.1f}ms)")

    except Exception as exc:
        print(f"    [FAIL] Falló el ciclo de vida en OCI: {translate_oci_error(exc)}")
        return 1

    print("\n" + "=" * 70)
    print("  ✓ RESUMEN: OCI OBJECT STORAGE TOTALMENTE OPERATIVO Y VERIFICADO")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(run_oci_check())
