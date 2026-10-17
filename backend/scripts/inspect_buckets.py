import os
import sys
import oci

def main():
    config_path = os.path.expanduser("~/.oci/config")
    if os.path.exists(config_path):
        config = oci.config.from_file(config_path)
        client = oci.object_storage.ObjectStorageClient(config)
    else:
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        client = oci.object_storage.ObjectStorageClient(config={"region": "mx-monterrey-1"}, signer=signer)

    ns = client.get_namespace().data
    print(f"[*] Tenancy Namespace: {ns}")

    if len(sys.argv) > 2 and sys.argv[1] == "--delete":
        b = sys.argv[2]
        k = sys.argv[3]
        print(f"[*] Deleting {k} from {b}...")
        client.delete_object(ns, b, k)
        print("[✓] Deleted.")
        return

    buckets = ["nuevamente-contenidos-educativos", "nuevamente-documentos-fuente"]
    for b in buckets:
        print(f"\n=== BUCKET: {b} ===")
        response = client.list_objects(ns, b, limit=1000)
        objects = response.data.objects
        print(f"Total objects: {len(objects)}")
        for obj in objects:
            print(f"  - {obj.name} ({obj.size} bytes, modified: {obj.time_modified})")

if __name__ == "__main__":
    main()
