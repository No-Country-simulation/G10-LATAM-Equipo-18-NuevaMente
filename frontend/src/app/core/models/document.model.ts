export type DocumentStatus = 'active' | 'trashed';
export type DocumentType = 'pdf' | 'md' | 'txt';

export interface AppDocument {
  id: string;
  name: string;
  size: number; // bytes
  type: DocumentType;
  uploadDate: string; // ISO string or formatted date
  contentUrl?: string; // Blob or DataURL for previewing PDF/files
  content?: string; // Extracted text content for RAG consumption
  status: DocumentStatus;
  tags?: string[];
  lastModified?: string;
  description?: string;
}

export interface DocumentUploadPayload {
  file: File;
  name?: string;
  tags?: string[];
}
