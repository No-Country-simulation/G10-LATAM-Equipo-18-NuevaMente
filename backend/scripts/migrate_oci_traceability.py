"""
migrate_oci_traceability.py

Script profesional de migración y trazabilidad en Oracle Cloud Infrastructure (OCI) Object Storage:
1. Elimina 'usuarios/usr_demo_001/' en 'nuevamente-contenidos-educativos' dejando únicamente 'usuarios/anonimo/'.
2. Aplica la nueva convención de trazabilidad en 'nuevamente-documentos-fuente':
   usuarios/{user_id}/documentos/{slug}_{YYYYMMDD}_{hash8}/{nombre_original}
3. Aplica la nueva convención de trazabilidad en 'nuevamente-contenidos-educativos':
   usuarios/{user_id}/contenidos/{carpeta_trazable}/{nombre_archivo_trazable}_v1.json
   (Eliminando los nombres genéricos 'v1.json').
4. Añade metadatos 'opc-meta-*' a cada objeto migrado para trazabilidad en consola OCI.
5. Actualiza las tablas 'documentos' y 'contenidos' en users.db.
"""

import os
import re
import sqlite3
from datetime import datetime, timezone
import oci

BUCKET_DOCS = "nuevamente-documentos-fuente"
BUCKET_CONTENT = "nuevamente-contenidos-educativos"

def get_oci_client():
    config_path = os.path.expanduser("~/.oci/config")
    if os.path.exists(config_path):
        config = oci.config.from_file(config_path)
        return oci.object_storage.ObjectStorageClient(config)
    signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
    return oci.object_storage.ObjectStorageClient(config={"region": "mx-monterrey-1"}, signer=signer)

def copy_and_delete(client, ns, bucket, src_key, dst_key, metadata=None, content_type="application/octet-stream"):
    print(f"  [COPY] {src_key} -> {dst_key}")
    # Descargar objeto fuente
    obj_data = client.get_object(ns, bucket, src_key).data.content
    # Subir con nueva clave y metadata
    client.put_object(
        namespace_name=ns,
        bucket_name=bucket,
        object_name=dst_key,
        put_object_body=obj_data,
        content_type=content_type,
        opc_meta=metadata or {}
    )
    # Eliminar objeto fuente antiguo
    print(f"  [DELETE SRC] {src_key}")
    client.delete_object(ns, bucket, src_key)

def run_migration():
    client = get_oci_client()
    ns = client.get_namespace().data
    print(f"[*] Namespace OCI: {ns}")

    key_mappings_docs = {}
    key_mappings_contents = {}

    # ─────────────────────────────────────────────────────────────────────────────
    # 1. Bucket: nuevamente-contenidos-educativos
    # ─────────────────────────────────────────────────────────────────────────────
    print(f"\n[*] Procesando bucket: {BUCKET_CONTENT}...")
    resp = client.list_objects(ns, BUCKET_CONTENT, limit=1000)
    objects = resp.data.objects

    for obj in objects:
        name = obj.name
        # 1a. Eliminar completamente usr_demo_001
        if "usuarios/usr_demo_001/" in name:
            print(f"  [PURGE DEMO] Eliminando objeto de prueba: {name}")
            client.delete_object(ns, BUCKET_CONTENT, name)
            continue

        # 1b. Migrar v1.json genéricos bajo anonimo a nombres descriptivos con trazabilidad
        if name.startswith("usuarios/anonimo/contenidos/") and name.endswith("/v1.json"):
            # Formato: usuarios/anonimo/contenidos/{folder}/v1.json
            parts = name.split("/")
            folder_name = parts[3]
            clean_folder = re.sub(r"[^a-zA-Z0-9_-]", "_", folder_name)
            new_filename = f"{clean_folder}_v1.json"
            new_key = f"usuarios/anonimo/contenidos/{clean_folder}/{new_filename}"

            if new_key != name:
                meta = {
                    "trazabilidad-tipo": "contenido_educativo",
                    "content-id": clean_folder,
                    "version": "1",
                    "user-id": "anonimo",
                    "migrado-trazabilidad": "true",
                }
                copy_and_delete(client, ns, BUCKET_CONTENT, name, new_key, meta, content_type="application/json")
                key_mappings_contents[name] = new_key

    # ─────────────────────────────────────────────────────────────────────────────
    # 2. Bucket: nuevamente-documentos-fuente
    # ─────────────────────────────────────────────────────────────────────────────
    print(f"\n[*] Procesando bucket: {BUCKET_DOCS}...")
    resp = client.list_objects(ns, BUCKET_DOCS, limit=1000)
    doc_objects = resp.data.objects

    # Regex para detectar carpetas con hashes largos (64 hex caracteres)
    hash_folder_pattern = re.compile(r"^usuarios/([^/]+)/documentos/([a-fA-F0-9]{32,64})/([^/]+)$")

    for obj in doc_objects:
        name = obj.name
        match = hash_folder_pattern.match(name)
        if match:
            user_id = match.group(1)
            sha_hash = match.group(2)
            filename = match.group(3)

            # Generar carpeta trazable: {slug}_{fecha}_{hash8}
            stem = filename.rsplit(".", 1)[0] if "." in filename else filename
            slug = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)[:35].strip("_") or "doc"
            date_str = "20261017"
            short_hash = sha_hash[:8]
            traceable_folder = f"{slug}_{date_str}_{short_hash}"

            new_key = f"usuarios/{user_id}/documentos/{traceable_folder}/{filename}"
            meta = {
                "trazabilidad-tipo": "documento_fuente",
                "nombre-original": filename,
                "sha256": sha_hash,
                "user-id": user_id,
                "migrado-trazabilidad": "true",
            }
            copy_and_delete(client, ns, BUCKET_DOCS, name, new_key, meta, content_type="application/pdf")
            key_mappings_docs[name] = new_key

    # ─────────────────────────────────────────────────────────────────────────────
    # 3. Actualizar BD users.db
    # ─────────────────────────────────────────────────────────────────────────────
    db_paths = ["/app/users.db", "users.db", "/home/ubuntu/app/backend/users.db"]
    for db_p in db_paths:
        if os.path.exists(db_p):
            print(f"\n[*] Actualizando referencias de trazabilidad en base de datos: {db_p}...")
            conn = sqlite3.connect(db_p)
            c = conn.cursor()

            # Actualizar documentos
            for old_k, new_k in key_mappings_docs.items():
                c.execute("UPDATE documentos SET object_key = ? WHERE object_key = ?", (new_k, old_k))
                print(f"  [DB DOCS UPDATE] {old_k} -> {new_k}")

            # Actualizar o limpiar contenidos
            c.execute("DELETE FROM contenidos WHERE user_id = 'usr_demo_001'")
            c.execute("DELETE FROM storage_jobs WHERE user_id = 'usr_demo_001'")
            for old_k, new_k in key_mappings_contents.items():
                c.execute("UPDATE contenidos SET object_key_json = ? WHERE object_key_json = ?", (new_k, old_k))
                c.execute("UPDATE storage_jobs SET object_key = ? WHERE object_key = ?", (new_k, old_k))
                print(f"  [DB CONTENT UPDATE] {old_k} -> {new_k}")

            conn.commit()
            conn.close()

    print("\n[✓] MIGRACIÓN Y TRAZABILIDAD OCI COMPLETADA EXITOSAMENTE.")

if __name__ == "__main__":
    run_migration()
