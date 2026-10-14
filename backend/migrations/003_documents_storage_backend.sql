-- 003_documents_storage_backend.sql
-- Purpose: records which storage backend holds each document's original file
-- (oci | supabase | local), so a listing row knows where its bytes live even
-- if the active backend changes. Run once in the Supabase SQL editor.

alter table documents
    add column if not exists storage_backend text;
