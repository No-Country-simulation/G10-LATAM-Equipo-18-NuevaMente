"""
supabase_client.py

Purpose:
    Creates and caches a single Supabase client for the backend process.
    Uses the service_role key (bypasses Row Level Security) — this client
    must never be exposed to the frontend, and any code using it must add
    its own ownership checks (e.g. filtering by user_id) since RLS won't.

Input:
    settings.SUPABASE_URL, settings.SUPABASE_KEY (from .env, never committed).

Output:
    get_supabase_client() -> a ready-to-use supabase.Client instance.
"""

from typing import Optional

from supabase import create_client, Client

from app.core.config import settings

_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """Returns the cached Supabase client, creating it on first use."""
    global _client
    if _client is None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in .env to use Supabase "
                "(SUPABASE_KEY must be the service_role key, not anon/public)."
            )
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client