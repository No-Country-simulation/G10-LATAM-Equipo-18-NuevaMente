export type DocumentStatus = 'active' | 'trashed';
export type DocumentType = 'pdf' | 'md' | 'txt';

export interface AppDocument {
  id: string; // backend `document_id`
  name: string;
  size: number; // bytes when known; the backend reports 0 for indexed docs
  type: DocumentType;
  uploadDate: string; // ISO string or formatted date
  contentUrl?: string; // Blob or DataURL for previewing PDF/files
  content?: string; // Extracted text; only present for locally-read files
  status: DocumentStatus;
  backendStatus?: string; // raw backend status: ready | failed | processing
  indexed?: boolean; // true when the backend status is 'ready'
  parents?: number; // number of indexed parent sections
  children?: number; // number of indexed child fragments
  storageBackend?: string; // oci | supabase | local
  tags?: string[];
  lastModified?: string;
  description?: string;
}

export interface DocumentUploadPayload {
  file: File;
  name?: string;
  tags?: string[];
}
