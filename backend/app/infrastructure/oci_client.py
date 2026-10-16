"""
oci_client.py

Purpose:
    Creates and caches a single OCI Object Storage client for the backend
    process, mirroring supabase_client.py. Credentials come from
    settings.OCI_CONFIG_FILE (~/.oci/config) or OCI_* env secrets — never
    hardcoded. Returns None (not an exception) when OCI isn't configured,
    so callers can degrade gracefully.

Input:
    settings.OCI_CONFIG_FILE, or OCI_TENANCY_OCID / OCI_USER_OCID /
    OCI_FINGERPRINT / OCI_PRIVATE_KEY_PATH / OCI_REGION.

Output:
    get_oci_client() -> ObjectStorageClient | None
    get_oci_namespace() -> str | None
"""

import os
from typing import Optional

from app.core.config import settings

_client = None
_namespace = None
_compartment_id = None


def get_oci_client():
    """Returns the cached ObjectStorageClient, or None when OCI isn't configured."""
    global _client, _compartment_id
    if _client is None:
        try:
            import oci
            if os.path.exists(settings.OCI_CONFIG_FILE):
                config = oci.config.from_file(settings.OCI_CONFIG_FILE)
            elif os.getenv("OCI_TENANCY_OCID"):
                config = {
                    "user": os.environ["OCI_USER_OCID"],
                    "fingerprint": os.environ["OCI_FINGERPRINT"],
                    "tenancy": os.environ["OCI_TENANCY_OCID"],
                    "region": os.environ["OCI_REGION"],
                    "key_file": os.path.expanduser(os.environ["OCI_PRIVATE_KEY_PATH"]),
                }
            else:
                return None
            # Root compartment = tenancy OCID, unless an explicit one is set.
            _compartment_id = os.getenv("OCI_COMPARTMENT_OCID") or config.get("tenancy")
            _client = oci.object_storage.ObjectStorageClient(config)
        except Exception:
            _client = None
    return _client


def get_oci_namespace() -> Optional[str]:
    """Returns the tenancy namespace, resolving it once from the API."""
    global _namespace
    if _namespace is None and get_oci_client() is not None:
        _namespace = settings.OCI_NAMESPACE or get_oci_client().get_namespace().data
    return _namespace


def get_oci_compartment_id() -> Optional[str]:
    """Compartment used to create buckets: explicit override, else root (tenancy)."""
    return _compartment_id