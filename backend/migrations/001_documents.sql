-- 001_documents.sql
-- Purpose: creates the `documents` table — one row per uploaded document,
-- tracking where its original file lives (object_key) and its processing
-- status. Run once in the Supabase SQL editor for this project.

create table if not exists documents (
    document_id uuid primary key,
    user_id uuid null,                          -- populated once login exists
    title text not null,
    source_filename text not null,
    object_key text not null,                   -- path inside the document-source bucket
    status text not null default 'processing',  -- processing | ready | failed
    total_parents integer,
    total_children integer,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Speeds up list_documents(user_id=...) once documents are scoped per user.
create index if not exists documents_user_id_idx on documents (user_id);

-- Speeds up "newest first" listings regardless of user.
create index if not exists documents_created_at_idx on documents (created_at desc);