#!/usr/bin/env python3
"""
migrate_local_to_oci.py

Migra archivos locales acumulados en storage_mock/ hacia los buckets de
OCI Object Storage Always Free. Soporta --dry-run y es idempotente por hash SHA-256.

Uso:
    python backend/scripts/migrate_local_to_oci.py [--dry-run]
"""

import sys
import os
import argparse
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.services.storage import get_storage_backend, OciStorageBackend
from app.services.storage.base import StorageBackend


def migrate_storage_mock(dry_run: bool = False) -> int:
    print("=" * 70)
    print("  NUEVAMENTE - MIGRACIÓN LOCAL (STORAGE_MOCK) -> OCI OBJECT STORAGE")
    print(f"  Modo: {'[SIMULACIÓN DRY-RUN]' if dry_run else '[EJECUCIÓN REAL]'}")
    print("=" * 70)

    mock_dir = Path(os.getcwd()) / "storage_mock"
    if not mock_dir.exists():
        print(f"[*] Directorio {mock_dir} no existe. Nada que migrar.")
        return 0

    backend = get_storage_backend()
    is_oci = isinstance(backend, OciStorageBackend)
    if not is_oci and not dry_run:
        print("[ERROR] El backend configurado no es OciStorageBackend. Active OCI_ENABLED=true y verifique Instance Principals / credenciales.")
        return 1
    elif not is_oci:
        print("[AVISO] OCI no conectado localmente en modo desarrollo. Mostrando archivos que se migrarán al ejecutar en la VM con Instance Principals.")

    total_scanned = 0
    total_migrated = 0
    total_skipped = 0
    total_failed = 0

    bucket_sources = settings.OCI_BUCKET_SOURCES
    bucket_content = settings.OCI_BUCKET_CONTENT

    for bucket_dir in mock_dir.iterdir():
        if not bucket_dir.is_dir():
            continue

        target_bucket = bucket_sources if "fuente" in bucket_dir.name or "doc" in bucket_dir.name else bucket_content

        print(f"\n--> Procesando directorio local: {bucket_dir.name} -> Bucket OCI: {target_bucket}")

        for file_path in bucket_dir.rglob("*"):
            if not file_path.is_file() or file_path.name.endswith(".meta.json"):
                continue

            total_scanned += 1
            rel_name = str(file_path.relative_to(bucket_dir)).replace("\\", "/")
            data = file_path.read_bytes()
            sha256_hash = StorageBackend.compute_sha256(data)
            size_kb = len(data) / 1024

            # Construir clave OCI adecuada
            if rel_name.startswith("usuarios/"):
                target_key = rel_name
            else:
                if target_bucket == bucket_sources:
                    target_key = StorageBackend.build_document_key("migracion", sha256_hash, file_path.name)
                else:
                    target_key = StorageBackend.build_content_key("migracion", file_path.stem)

            # Verificar si ya existe en OCI con el mismo hash
            existing_head = backend.head_object(target_bucket, target_key) if is_oci else None
            if existing_head and existing_head.get("opc-meta-sha256") == sha256_hash:
                print(f"    [SKIP] {rel_name} ({size_kb:.1f} KB) ya existe en OCI con hash idéntico.")
                total_skipped += 1
                continue

            if dry_run:
                print(f"    [PLAN] Subiría {rel_name} -> {target_bucket}/{target_key} ({size_kb:.1f} KB)")
                total_migrated += 1
            else:
                try:
                    ext = file_path.suffix.lower()
                    c_type = "application/pdf" if ext == ".pdf" else ("application/json" if ext == ".json" else "text/plain")
                    backend.put_object(
                        bucket_name=target_bucket,
                        object_name=target_key,
                        data=data,
                        content_type=c_type,
                        metadata={"origen": "migracion_local", "archivo_original": file_path.name},
                    )
                    print(f"    [OK] Migrado {rel_name} -> {target_key}")
                    total_migrated += 1
                except Exception as exc:
                    print(f"    [FAIL] Error migrando {rel_name}: {exc}")
                    total_failed += 1

    print("\n" + "=" * 70)
    print("  RESUMEN DE MIGRACIÓN")
    print(f"  - Archivos encontrados: {total_scanned}")
    print(f"  - Migrados:            {total_migrated}")
    print(f"  - Omitidos (dedupe):   {total_skipped}")
    print(f"  - Fallidos:            {total_failed}")
    print("=" * 70)

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migra archivos de storage_mock/ hacia OCI Object Storage.")
    parser.add_argument("--dry-run", action="store_true", help="Simula la migración sin subir datos.")
    args = parser.parse_args()
    sys.exit(migrate_storage_mock(dry_run=args.dry_run))
