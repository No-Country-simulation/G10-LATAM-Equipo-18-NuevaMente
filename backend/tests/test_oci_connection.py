import oci

try:
    # Read config file
    config = oci.config.from_file()
    
    # Initialize Object Storage client
    object_storage_client = oci.object_storage.ObjectStorageClient(config)
    
    # Get namespace to validate credentials
    namespace = object_storage_client.get_namespace().data
    print("--------------------------------------------------")
    print(f"¡Conexión exitosa a OCI! 🎉")
    print(f"Tu Namespace es: {namespace}")
    print("--------------------------------------------------")

except Exception as e:
    print("--------------------------------------------------")
    print("❌ Error de conexión. Revisa lo siguiente:")
    print(f"Detalle del error: {e}")
    print("--------------------------------------------------")