-- 002_adapted_contents.sql
-- Purpose: creates the `adapted_contents` table — records generated educational
-- packages (flashcards, quizzes, tutorials, summaries) linked to their parent
-- document in the `documents` table. Stores the artifact storage location and
-- the full payload JSON. Run once in the Supabase SQL editor for this project.

create table if not exists adapted_contents (
    artifact_id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(document_id) on delete cascade,
    user_id uuid null,                          -- populated once login exists
    output_format text not null,                -- 'flashcards' | 'quiz' | 'tutorial' | 'resumen ejecutivo' | 'guion de clase'
    recipient_profile text not null,            -- 'desarrollador junior' | 'arquitecto' | 'ejecutivo' | etc.
    niche text not null,                        -- 'general' | 'fintech' | 'salud' | etc.
    object_key text not null,                   -- path inside the adapted-artifacts bucket
    content_json jsonb not null,                -- structured payload containing generated items, citations, and evaluation
    created_at timestamptz not null default now()
);

-- Speeds up finding all adaptations generated for a specific document.
create index if not exists adapted_contents_document_id_idx on adapted_contents (document_id);

-- Speeds up user history queries.
create index if not exists adapted_contents_user_id_idx on adapted_contents (user_id);

-- Speeds up newest-first sorting.
create index if not exists adapted_contents_created_at_idx on adapted_contents (created_at desc);
