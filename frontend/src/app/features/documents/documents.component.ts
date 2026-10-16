import { Component, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { DocumentService } from '../../core/services/document.service';
import { AppDocument, DocumentType } from '../../core/models/document.model';

@Component({
  selector: 'app-documents',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  template: `
    <div class="documents-container">
      <!-- Page Header & Stats -->
      <div class="page-header">
        <div>
          <span class="module-badge">📚 MÓDULO DE GESTIÓN DOCUMENTAL</span>
          <h1>Almacén de Documentos</h1>
          <p>Repositorio de archivos técnicos (.pdf, .md, .txt) para alimentación del pipeline RAG Híbrido.</p>
        </div>
        <div class="header-stats">
          <div class="stat-card">
            <span class="stat-value">{{ documentService.totalActiveCount() }}</span>
            <span class="stat-label">Documentos Activos</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ documentService.totalStorageSizeFormatted() }}</span>
            <span class="stat-label">Almacenamiento Usado</span>
          </div>
        </div>
      </div>

      <!-- Dropzone Upload Section -->
      <div 
        class="upload-dropzone glass-card"
        [class.is-dragging]="isDragging()"
        (dragover)="onDragOver($event)"
        (dragleave)="onDragLeave($event)"
        (drop)="onDrop($event)"
      >
        <input #fileInput type="file" (change)="onFileSelected($event)" accept=".pdf,.md,.txt" style="display:none;" />
        <div class="dropzone-body" (click)="fileInput.click()">
          <div class="drop-icon-wrapper">
            <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <div class="drop-text-group">
            <h3>Arrastra y suelta tus archivos aquí</h3>
            <p>O haz clic para explorar en tu equipo (.pdf, .md, .txt hasta 20MB)</p>
          </div>
          <button type="button" class="btn-browse">
            📂 Buscar Archivo
          </button>
        </div>
        <div class="upload-loader" *ngIf="isUploading()">
          <div class="spinner"></div>
          <span>Procesando e indexando documento...</span>
        </div>
      </div>

      <!-- Controls & Filter Bar -->
      <div class="controls-bar glass-card">
        <!-- Search Box -->
        <div class="search-box">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input 
            type="text" 
            placeholder="Buscar documento por nombre o etiquetas..."
            [value]="searchTerm()"
            (input)="onSearchInput($event)"
          />
        </div>

        <!-- Filter & View Mode Switches -->
        <div class="filter-group">
          <select [value]="selectedTypeFilter()" (change)="onTypeFilterChange($event)">
            <option value="all">Todos los tipos (.pdf, .md, .txt)</option>
            <option value="pdf">Documentos PDF (.pdf)</option>
            <option value="md">Archivos Markdown (.md)</option>
            <option value="txt">Archivos de Texto (.txt)</option>
          </select>

          <div class="view-toggle">
            <button 
              type="button" 
              class="toggle-btn" 
              [class.active]="viewMode() === 'grid'"
              (click)="viewMode.set('grid')"
              title="Vista en Cuadrícula"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            </button>
            <button 
              type="button" 
              class="toggle-btn" 
              [class.active]="viewMode() === 'table'"
              (click)="viewMode.set('table')"
              title="Vista en Lista"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
            </button>
          </div>
        </div>
      </div>

      <!-- GRID VIEW -->
      <div class="documents-grid" *ngIf="viewMode() === 'grid' && filteredDocuments().length > 0">
        <div class="doc-card glass-card" *ngFor="let doc of filteredDocuments()">
          <div class="doc-card-header">
            <span class="type-badge" [ngClass]="doc.type">
              {{ doc.type.toUpperCase() }}
            </span>
            <div class="card-menu-actions">
              <button type="button" class="btn-icon" (click)="openRenameModal(doc)" title="Renombrar">✏️</button>
              <button type="button" class="btn-icon danger" (click)="moveToTrash(doc)" title="Mover a Papelera">🗑️</button>
            </div>
          </div>

          <div class="doc-card-body">
            <div class="doc-file-icon">
              <span *ngIf="doc.type === 'pdf'">📕</span>
              <span *ngIf="doc.type === 'md'">📘</span>
              <span *ngIf="doc.type === 'txt'">📄</span>
            </div>
            <h3 class="doc-name" [title]="doc.name">{{ doc.name }}</h3>
            <p class="doc-meta">
              <span>{{ formatSize(doc.size) }}</span> · 
              <span>{{ formatDate(doc.uploadDate) }}</span>
            </p>
            <div class="tags-container" *ngIf="doc.tags && doc.tags.length > 0">
              <span class="tag-pill" *ngFor="let tag of doc.tags">{{ tag }}</span>
            </div>
          </div>

          <div class="doc-card-footer">
            <button type="button" class="btn-preview" (click)="openPreviewModal(doc)">
              👁️ Previsualizar
            </button>
            <button type="button" class="btn-use-workspace" (click)="useInWorkspace(doc)">
              🚀 Usar en Workspace
            </button>
          </div>
        </div>
      </div>

      <!-- TABLE VIEW -->
      <div class="table-card glass-card" *ngIf="viewMode() === 'table' && filteredDocuments().length > 0">
        <table class="docs-table">
          <thead>
            <tr>
              <th>Tipo</th>
              <th>Nombre del Documento</th>
              <th>Tamaño</th>
              <th>Fecha de Carga</th>
              <th>Etiquetas</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let doc of filteredDocuments()">
              <td>
                <span class="type-badge" [ngClass]="doc.type">{{ doc.type.toUpperCase() }}</span>
              </td>
              <td class="doc-title-cell">
                <strong>{{ doc.name }}</strong>
              </td>
              <td>{{ formatSize(doc.size) }}</td>
              <td>{{ formatDate(doc.uploadDate) }}</td>
              <td>
                <div class="tags-container">
                  <span class="tag-pill" *ngFor="let tag of doc.tags">{{ tag }}</span>
                </div>
              </td>
              <td class="table-actions">
                <button type="button" class="btn-table-action" (click)="openPreviewModal(doc)" title="Ver">👁️ Ver</button>
                <button type="button" class="btn-table-action primary" (click)="useInWorkspace(doc)" title="Usar en Workspace">🚀 Usar</button>
                <button type="button" class="btn-table-action" (click)="openRenameModal(doc)" title="Editar">✏️</button>
                <button type="button" class="btn-table-action danger" (click)="moveToTrash(doc)" title="Papelera">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- EMPTY STATE -->
      <div class="empty-state glass-card" *ngIf="filteredDocuments().length === 0">
        <div class="empty-icon-box">📁</div>
        <h3>No se encontraron documentos</h3>
        <p>Sube archivos PDF, Markdown o Texto plano para comenzar a utilizarlos en el Workspace.</p>
      </div>

      <!-- PREVIEW MODAL / DRAWER -->
      <div class="modal-overlay" *ngIf="previewDoc()" (click)="closePreviewModal()">
        <div class="modal-container preview-modal" (click)="$event.stopPropagation()">
          <div class="modal-header">
            <div class="header-info">
              <span class="type-badge" [ngClass]="previewDoc()!.type">{{ previewDoc()!.type.toUpperCase() }}</span>
              <h3>{{ previewDoc()!.name }}</h3>
            </div>
            <button type="button" class="btn-close" (click)="closePreviewModal()">✕</button>
          </div>

          <div class="modal-body">
            <!-- PDF Viewer iframe/embed -->
            <div class="pdf-viewer-container" *ngIf="previewDoc()!.type === 'pdf'">
              <iframe 
                *ngIf="sanitizedPreviewUrl()"
                [src]="sanitizedPreviewUrl()" 
                class="pdf-iframe"
                title="Previsualizador PDF"
              ></iframe>
              <div class="pdf-fallback-box" *ngIf="!sanitizedPreviewUrl()">
                <p>📄 Este archivo PDF se encuentra listo para el motor RAG.</p>
                <p class="preview-subtext">Haz clic a continuación para cargarlo en el Workspace de Adaptación.</p>
              </div>
            </div>

            <!-- Text / Markdown Reader Viewer -->
            <div class="text-viewer-container" *ngIf="previewDoc()!.type !== 'pdf'">
              <pre class="text-reader-content">{{ previewDoc()!.content || 'Sin contenido de texto disponible.' }}</pre>
            </div>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="downloadDoc(previewDoc()!)">
              📥 Descargar
            </button>
            <button type="button" class="btn-primary" (click)="useInWorkspace(previewDoc()!)">
              🚀 Cargar en Workspace de Adaptación
            </button>
          </div>
        </div>
      </div>

      <!-- RENAME MODAL -->
      <div class="modal-overlay" *ngIf="renameDocTarget()" (click)="closeRenameModal()">
        <div class="modal-container rename-modal" (click)="$event.stopPropagation()">
          <div class="modal-header">
            <h3>✏️ Renombrar Documento</h3>
            <button type="button" class="btn-close" (click)="closeRenameModal()">✕</button>
          </div>
          <div class="modal-body">
            <label for="rename-input" class="rename-label">Nombre del Archivo</label>
            <input 
              id="rename-input"
              type="text" 
              class="rename-input" 
              [value]="renameInputText()" 
              (input)="onRenameInput($event)" 
            />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="closeRenameModal()">Cancelar</button>
            <button type="button" class="btn-primary" (click)="saveRename()">Guardar Cambios</button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .documents-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 1rem 0;
    }

    .module-badge {
      font-size: 0.75rem;
      font-weight: 800;
      color: #6366F1;
      letter-spacing: 0.08em;
      margin-bottom: 0.25rem;
      display: block;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 2rem;
      gap: 1.5rem;
    }

    .page-header h1 {
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 0.4rem;
    }

    .page-header p {
      color: var(--text-secondary);
      font-size: 1rem;
    }

    .header-stats {
      display: flex;
      gap: 1rem;
    }

    .stat-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      padding: 0.85rem 1.25rem;
      border-radius: 14px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    .stat-value {
      font-size: 1.5rem;
      font-weight: 800;
      color: #4F46E5;
    }

    .stat-label {
      font-size: 0.78rem;
      color: var(--text-muted);
      font-weight: 600;
    }

    /* DROPZONE UPLOAD */
    .upload-dropzone {
      padding: 2rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 2px dashed #818CF8;
      margin-bottom: 2rem;
      transition: all 0.25s ease;
      cursor: pointer;
      position: relative;
    }

    .upload-dropzone:hover, .upload-dropzone.is-dragging {
      border-color: #4F46E5;
      background: rgba(99, 102, 241, 0.04);
      transform: translateY(-2px);
    }

    .dropzone-body {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }

    .drop-icon-wrapper {
      width: 60px; height: 60px;
      border-radius: 16px;
      background: rgba(99, 102, 241, 0.1);
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }

    .drop-text-group {
      flex: 1;
    }

    .drop-text-group h3 {
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 0.25rem;
    }

    .drop-text-group p {
      font-size: 0.88rem;
      color: var(--text-secondary);
    }

    .btn-browse {
      background: #4F46E5;
      color: #FFFFFF;
      border: none;
      padding: 0.65rem 1.25rem;
      border-radius: 12px;
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
      transition: background 0.2s;
    }

    .btn-browse:hover { background: #4338CA; }

    .upload-loader {
      position: absolute; inset: 0; background: rgba(255,255,255,0.9);
      border-radius: 20px; display: flex; align-items: center; justify-content: center;
      gap: 1rem; font-weight: 700; color: #4F46E5;
    }

    /* CONTROLS BAR */
    .controls-bar {
      padding: 1.25rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .search-box {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      background: var(--bg-app);
      padding: 0.6rem 1rem;
      border-radius: 10px;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
    }

    .search-box input {
      background: transparent; border: none; width: 100%; font-size: 0.95rem;
      color: var(--text-primary); outline: none;
    }

    .filter-group {
      display: flex; gap: 0.75rem; align-items: center;
    }

    .filter-group select {
      padding: 0.6rem 1rem; border-radius: 10px; background: var(--bg-app);
      border: 1px solid var(--border-subtle); color: var(--text-primary); font-size: 0.9rem; outline: none;
    }

    .view-toggle {
      display: flex; background: var(--bg-app); border-radius: 10px; border: 1px solid var(--border-subtle); padding: 0.2rem;
    }

    .toggle-btn {
      background: transparent; border: none; padding: 0.4rem 0.65rem; border-radius: 8px;
      color: var(--text-muted); cursor: pointer; display: flex; align-items: center;
    }

    .toggle-btn.active { background: var(--bg-surface); color: #4F46E5; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }

    /* GRID VIEW */
    .documents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1.5rem;
    }

    .doc-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 18px;
      padding: 1.25rem;
      display: flex; flex-direction: column;
      transition: all 0.2s ease;
      box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }

    .doc-card:hover {
      transform: translateY(-3px);
      box-shadow: 0 10px 25px rgba(0,0,0,0.08);
      border-color: rgba(99, 102, 241, 0.4);
    }

    .doc-card-header {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;
    }

    .type-badge {
      font-size: 0.72rem; font-weight: 800; padding: 0.2rem 0.6rem; border-radius: 6px; letter-spacing: 0.05em;
    }
    .type-badge.pdf { background: rgba(239, 68, 68, 0.12); color: #EF4444; }
    .type-badge.md { background: rgba(124, 58, 237, 0.12); color: #7C3AED; }
    .type-badge.txt { background: rgba(6, 182, 212, 0.12); color: #0891B2; }

    .card-menu-actions {
      display: flex; gap: 0.25rem;
    }

    .btn-icon {
      background: transparent; border: none; padding: 0.3rem 0.45rem; border-radius: 6px;
      cursor: pointer; font-size: 0.9rem; opacity: 0.7; transition: opacity 0.2s;
    }
    .btn-icon:hover { opacity: 1; background: var(--bg-app); }
    .btn-icon.danger:hover { background: rgba(239, 68, 68, 0.1); }

    .doc-card-body {
      flex: 1; margin-bottom: 1.25rem;
    }

    .doc-file-icon {
      font-size: 2rem; margin-bottom: 0.5rem;
    }

    .doc-name {
      font-size: 1.05rem; font-weight: 700; margin-bottom: 0.35rem; line-height: 1.35;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }

    .doc-meta {
      font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.75rem;
    }

    .tags-container {
      display: flex; flex-wrap: wrap; gap: 0.35rem;
    }

    .tag-pill {
      font-size: 0.72rem; background: var(--bg-app); border: 1px solid var(--border-subtle);
      padding: 0.15rem 0.5rem; border-radius: 6px; color: var(--text-secondary);
    }

    .doc-card-footer {
      display: flex; gap: 0.6rem; border-top: 1px solid var(--border-subtle); padding-top: 1rem;
    }

    .btn-preview {
      flex: 1; background: var(--bg-app); border: 1px solid var(--border-subtle); color: var(--text-primary);
      padding: 0.5rem; border-radius: 10px; font-size: 0.82rem; font-weight: 700; cursor: pointer;
    }

    .btn-use-workspace {
      flex: 1.3; background: #4F46E5; color: #FFF; border: none;
      padding: 0.5rem; border-radius: 10px; font-size: 0.82rem; font-weight: 700; cursor: pointer;
      transition: background 0.2s;
    }
    .btn-use-workspace:hover { background: #4338CA; }

    /* TABLE VIEW */
    .table-card { padding: 1rem; border-radius: 18px; background: var(--bg-surface); border: 1px solid var(--border-subtle); overflow-x: auto; }
    .docs-table { width: 100%; border-collapse: collapse; text-align: left; }
    .docs-table th { padding: 1rem; font-size: 0.78rem; font-weight: 800; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle); }
    .docs-table td { padding: 1rem; border-bottom: 1px solid var(--border-subtle); font-size: 0.9rem; }
    .doc-title-cell { max-width: 300px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .table-actions { display: flex; gap: 0.4rem; }
    .btn-table-action { background: var(--bg-app); border: 1px solid var(--border-subtle); padding: 0.35rem 0.65rem; border-radius: 8px; font-size: 0.8rem; font-weight: 600; cursor: pointer; }
    .btn-table-action.primary { background: #4F46E5; color: #FFF; border: none; font-weight: 700; }
    .btn-table-action.danger { color: #EF4444; border-color: rgba(239, 68, 68, 0.3); }

    /* MODALS */
    .modal-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.65); backdrop-filter: blur(5px);
      z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 1.5rem;
    }

    .modal-container {
      background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 20px;
      width: 100%; max-width: 850px; max-height: 85vh; display: flex; flex-direction: column;
      box-shadow: 0 25px 50px rgba(0,0,0,0.3); overflow: hidden;
    }

    .modal-header {
      padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border-subtle);
      display: flex; justify-content: space-between; align-items: center;
    }

    .header-info { display: flex; align-items: center; gap: 0.75rem; }
    .modal-header h3 { font-size: 1.15rem; font-weight: 800; margin: 0; }

    .btn-close { background: transparent; border: none; font-size: 1.25rem; cursor: pointer; color: var(--text-muted); }

    .modal-body { flex: 1; padding: 1.5rem; overflow-y: auto; }

    .pdf-viewer-container { height: 500px; width: 100%; background: #1E293B; border-radius: 12px; overflow: hidden; }
    .pdf-iframe { width: 100%; height: 100%; border: none; }
    .pdf-fallback-box { padding: 3rem; text-align: center; color: #F8FAFC; }

    .text-viewer-container { background: var(--bg-app); border-radius: 12px; padding: 1.25rem; max-height: 450px; overflow-y: auto; }
    .text-reader-content { white-space: pre-wrap; font-family: monospace; font-size: 0.88rem; line-height: 1.6; margin: 0; }

    .modal-footer { padding: 1.25rem 1.5rem; border-top: 1px solid var(--border-subtle); display: flex; justify-content: flex-end; gap: 0.75rem; }
    .btn-secondary { background: var(--bg-app); border: 1px solid var(--border-subtle); padding: 0.6rem 1.25rem; border-radius: 10px; font-weight: 700; cursor: pointer; }
    .btn-primary { background: #4F46E5; color: #FFF; border: none; padding: 0.6rem 1.25rem; border-radius: 10px; font-weight: 700; cursor: pointer; }

    .rename-modal { max-width: 450px; }
    .rename-label { font-size: 0.85rem; font-weight: 700; margin-bottom: 0.5rem; display: block; }
    .rename-input { width: 100%; padding: 0.75rem; border-radius: 10px; border: 1px solid var(--border-subtle); background: var(--bg-app); color: var(--text-primary); font-size: 0.95rem; }

    .empty-state { padding: 4rem 2rem; text-align: center; border-radius: 20px; }
    .empty-icon-box { font-size: 3rem; margin-bottom: 1rem; }
  `]
})
export class DocumentsComponent {
  readonly documentService = inject(DocumentService);
  private router = inject(Router);
  private sanitizer = inject(DomSanitizer);

  searchTerm = signal<string>('');
  selectedTypeFilter = signal<string>('all');
  viewMode = signal<'grid' | 'table'>('grid');

  isDragging = signal<boolean>(false);
  isUploading = signal<boolean>(false);

  previewDoc = signal<AppDocument | null>(null);
  sanitizedPreviewUrl = signal<SafeResourceUrl | null>(null);

  renameDocTarget = signal<AppDocument | null>(null);
  renameInputText = signal<string>('');

  filteredDocuments = computed(() => {
    const query = this.searchTerm().toLowerCase();
    const type = this.selectedTypeFilter();

    return this.documentService.activeDocuments().filter(doc => {
      const matchQuery = doc.name.toLowerCase().includes(query) ||
        (doc.tags && doc.tags.some(t => t.toLowerCase().includes(query)));
      const matchType = type === 'all' || doc.type === type;
      return matchQuery && matchType;
    });
  });

  onSearchInput(event: Event): void {
    this.searchTerm.set((event.target as HTMLInputElement).value);
  }

  onTypeFilterChange(event: Event): void {
    this.selectedTypeFilter.set((event.target as HTMLSelectElement).value);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      this.handleFileUpload(event.dataTransfer.files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFileUpload(input.files[0]);
    }
  }

  private async handleFileUpload(file: File): Promise<void> {
    this.isUploading.set(true);
    try {
      await this.documentService.uploadDocument(file);
    } catch (e) {
      console.error('Error uploading file:', e);
    } finally {
      this.isUploading.set(false);
    }
  }

  openPreviewModal(doc: AppDocument): void {
    this.previewDoc.set(doc);
    if (doc.type === 'pdf' && doc.contentUrl) {
      this.sanitizedPreviewUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(doc.contentUrl));
    } else {
      this.sanitizedPreviewUrl.set(null);
    }
  }

  closePreviewModal(): void {
    this.previewDoc.set(null);
    this.sanitizedPreviewUrl.set(null);
  }

  openRenameModal(doc: AppDocument): void {
    this.renameDocTarget.set(doc);
    this.renameInputText.set(doc.name);
  }

  closeRenameModal(): void {
    this.renameDocTarget.set(null);
  }

  onRenameInput(event: Event): void {
    this.renameInputText.set((event.target as HTMLInputElement).value);
  }

  saveRename(): void {
    const doc = this.renameDocTarget();
    const newName = this.renameInputText().trim();
    if (doc && newName) {
      this.documentService.renameDocument(doc.id, newName);
      this.closeRenameModal();
    }
  }

  moveToTrash(doc: AppDocument): void {
    this.documentService.moveToTrash(doc.id);
  }

  useInWorkspace(doc: AppDocument): void {
    this.documentService.selectForWorkspace(doc);
    if (this.previewDoc()) {
      this.closePreviewModal();
    }
    this.router.navigate(['/workspace']);
  }

  downloadDoc(doc: AppDocument): void {
    const blob = new Blob([doc.content || ''], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = doc.name;
    a.click();
    URL.revokeObjectURL(url);
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  formatDate(dateStr: string): string {
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }
}
