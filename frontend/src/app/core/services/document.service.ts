import { Injectable, signal, computed } from '@angular/core';
import { AppDocument, DocumentType } from '../models/document.model';

const STORAGE_KEY = 'nuevamente_app_documents';

@Injectable({
  providedIn: 'root'
})
export class DocumentService {
  private documentsSignal = signal<AppDocument[]>([]);
  readonly selectedWorkspaceDocument = signal<AppDocument | null>(null);

  // Computed signals
  readonly activeDocuments = computed(() =>
    this.documentsSignal().filter(doc => doc.status === 'active')
  );

  readonly trashedDocuments = computed(() =>
    this.documentsSignal().filter(doc => doc.status === 'trashed')
  );

  readonly totalActiveCount = computed(() => this.activeDocuments().length);

  readonly totalStorageSizeFormatted = computed(() => {
    const bytes = this.activeDocuments().reduce((acc, doc) => acc + doc.size, 0);
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  });

  constructor() {
    this.initDocuments();
  }

  private initDocuments(): void {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed: AppDocument[] = JSON.parse(saved);
        const cleanedDocs = parsed.map(doc => ({
          ...doc,
          content: this.cleanPdfTextFrontend(doc.content || '', doc.name)
        }));
        this.saveToStorage(cleanedDocs);
        return;
      } catch (e) {
        console.error('Error parsing stored documents:', e);
      }
    }

    // Default Demo Initial Documents if storage is empty
    const initialDocs: AppDocument[] = [
      {
        id: 'doc-demo-001',
        name: 'Especificación de Redes VCN en Oracle Cloud Infrastructure (OCI).pdf',
        size: 1420500, // ~1.4 MB
        type: 'pdf',
        uploadDate: new Date(Date.now() - 86400000 * 2).toISOString(),
        status: 'active',
        tags: ['OCI', 'Redes', 'Cloud', 'Infraestructura'],
        content: `Manual de Arquitectura de Redes Virtuales (VCN) en Oracle Cloud Infrastructure (OCI).
Contenido didáctico:
1. Creación de VCNs y Subredes públicas/privadas.
2. Configuración de Security Lists e Ingress Rules para puertos HTTP 80, 443 y 8000.
3. Tabla de Ruteo e Internet Gateways (IGW).
4. Integración con Compute Instances Ubuntu y servicios de almacenamiento OCI Object Storage Always Free.`
      },
      {
        id: 'doc-demo-002',
        name: 'Guía de Microservicios con Spring Boot y MsJava.md',
        size: 24800, // 24.8 KB
        type: 'md',
        uploadDate: new Date(Date.now() - 86400000 * 5).toISOString(),
        status: 'active',
        tags: ['Java', 'Spring Boot', 'Fintech', 'Microservicios'],
        content: `# Guía Didáctica: MsJava Microservicios
## Arquitectura de Aplicaciones Escalarles en Fintech

### Contenido Principal:
- **Fase 1:** Configuración de dependencias Spring Boot 3.x y JDK 21.
- **Fase 2:** Implementación del patrón API Gateway y Service Discovery.
- **Fase 3:** Resiliencia y Fallback mediante Resilience4j y Circuit Breakers.
- **Fase 4:** Despliegue contenerizado en OCI Kubernetes Engine (OKE).`
      },
      {
        id: 'doc-demo-003',
        name: 'Resumen de Patrones RAG Híbrido y Graph RAG.txt',
        size: 12400, // 12.4 KB
        type: 'txt',
        uploadDate: new Date(Date.now() - 86400000 * 10).toISOString(),
        status: 'active',
        tags: ['RAG', 'IA', 'GraphRAG', 'Gemini'],
        content: `Arquitectura de RAG Híbrido + Graph RAG para Recuperación Didáctica.
Este documento detalla la combinación de Embeddings Densos (Gemini 001) y Búsqueda Esparsa (BM25) sincronizada con Grafos de Conocimiento (NetworkX) para garantizar el 100% de anclaje a las fuentes originales.`
      }
    ];

    this.saveToStorage(initialDocs);
  }

  private saveToStorage(docs: AppDocument[]): void {
    this.documentsSignal.set([...docs]);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(docs));
    } catch (e) {
      console.warn('Could not save documents to localStorage:', e);
    }
  }

  /**
   * Uploads and registers a new file
   */
  async uploadDocument(file: File, customName?: string, tags: string[] = []): Promise<AppDocument> {
    const fileExt = file.name.split('.').pop()?.toLowerCase();
    let type: DocumentType = 'txt';
    if (fileExt === 'pdf') type = 'pdf';
    else if (fileExt === 'md' || fileExt === 'markdown') type = 'md';

    const content = await this.readFileAsText(file);
    let contentUrl: string | undefined;

    if (type === 'pdf') {
      contentUrl = URL.createObjectURL(file);
    }

    const newDoc: AppDocument = {
      id: 'doc-' + Date.now() + '-' + Math.random().toString(36).substr(2, 5),
      name: customName || file.name,
      size: file.size,
      type,
      uploadDate: new Date().toISOString(),
      contentUrl,
      content,
      status: 'active',
      tags: tags.length > 0 ? tags : [type.toUpperCase(), 'Importado']
    };

    const current = this.documentsSignal();
    this.saveToStorage([newDoc, ...current]);
    return newDoc;
  }

  private cleanPdfTextFrontend(raw: string, filename: string): string {
    if (!raw) return `Documento PDF ${filename} cargado para procesamiento RAG.`;
    let text = raw.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\uFFFD]/g, '');
    text = text.replace(/stream[\s\S]*?endstream/gi, '');
    text = text.replace(/<<[\s\S]*?>>/g, '');
    text = text.replace(/\d+\s+\d+\s+obj[\s\S]*?endobj/gi, '');
    text = text.replace(/^.*(?:%PDF-|\b\d+\s+\d+\s+R\b|\/FlateDecode|\/Filter|\/FontDescriptor|\/MediaBox|\/Parent|\/Catalog|\/Length).*$/gm, '');
    text = text.trim();
    if (text.length < 20) {
      return `Documento PDF ${filename} cargado. El contenido será extraído mediante el motor RAG del backend.`;
    }
    return text;
  }

  /**
   * Reads file as plain text for RAG processing
   */
  private readFileAsText(file: File): Promise<string> {
    const fileExt = file.name.split('.').pop()?.toLowerCase();
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const result = e.target?.result as string || '';
        if (fileExt === 'pdf') {
          resolve(this.cleanPdfTextFrontend(result, file.name));
        } else {
          resolve(result || `Contenido de archivo: ${file.name}`);
        }
      };
      reader.onerror = () => resolve(`Documento ${file.name} cargado.`);
      reader.readAsText(file);
    });
  }

  /**
   * Renames a document
   */
  renameDocument(id: string, newName: string): void {
    const updated = this.documentsSignal().map(doc => {
      if (doc.id === id) {
        return { ...doc, name: newName, lastModified: new Date().toISOString() };
      }
      return doc;
    });
    this.saveToStorage(updated);
  }

  /**
   * Moves a document to trash (soft-delete)
   */
  moveToTrash(id: string): void {
    const updated = this.documentsSignal().map(doc => {
      if (doc.id === id) {
        return { ...doc, status: 'trashed' as const, lastModified: new Date().toISOString() };
      }
      return doc;
    });
    this.saveToStorage(updated);
    if (this.selectedWorkspaceDocument()?.id === id) {
      this.selectedWorkspaceDocument.set(null);
    }
  }

  /**
   * Restores a document from trash
   */
  restoreFromTrash(id: string): void {
    const updated = this.documentsSignal().map(doc => {
      if (doc.id === id) {
        return { ...doc, status: 'active' as const, lastModified: new Date().toISOString() };
      }
      return doc;
    });
    this.saveToStorage(updated);
  }

  /**
   * Permanently deletes a document
   */
  deletePermanently(id: string): void {
    const filtered = this.documentsSignal().filter(doc => doc.id !== id);
    this.saveToStorage(filtered);
    if (this.selectedWorkspaceDocument()?.id === id) {
      this.selectedWorkspaceDocument.set(null);
    }
  }

  /**
   * Gets document by ID
   */
  getDocumentById(id: string): AppDocument | undefined {
    return this.documentsSignal().find(doc => doc.id === id);
  }

  /**
   * Sets document for Workspace consumption
   */
  selectForWorkspace(document: AppDocument): void {
    this.selectedWorkspaceDocument.set(document);
  }

  /**
   * Clears selection for Workspace
   */
  clearWorkspaceSelection(): void {
    this.selectedWorkspaceDocument.set(null);
  }
}
