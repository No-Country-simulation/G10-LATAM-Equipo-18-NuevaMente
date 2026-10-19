/**
 * SharedDropzoneComponent
 *
 * Purpose:
 *     Single reusable dropzone for the document ingestion flow, shared by the
 *     Documents page ("Mis Documentos") and the Workspace "upload new" area so
 *     both screens expose the exact same upload UX (drag & drop + browse).
 *
 *     It is presentational: it only picks a file and reports it. The parent
 *     owns the actual ingestion call. When the picked file is a PDF it shows an
 *     "AI Vision (OCR)" toggle so the user can opt in to vision-based text
 *     extraction for scanned documents.
 *
 * Input:
 *     [disabled]: block interaction while a pipeline run is in progress
 *     [compact]: tighter paddings for constrained panels
 *     [accept]: accepted file extensions
 *
 * Output:
 *     fileSelected: emits the picked File
 *     useAiVisionChange: emits the current OCR toggle value (true only makes
 *         sense for PDFs; the parent should ignore it for other types)
 */
import { Component, EventEmitter, Input, Output, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-shared-dropzone',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div
      class="dropzone"
      [class.compact]="compact"
      [class.dragover]="isDragging()"
      [class.disabled]="disabled"
      (dragover)="onDragOver($event)"
      (dragleave)="onDragLeave($event)"
      (drop)="onDrop($event)"
      (click)="onClick(fileInput)"
    >
      <input
        #fileInput
        type="file"
        [accept]="accept"
        style="display:none;"
        (change)="onFileSelected($event)"
      />

      <div class="dropzone-main" *ngIf="!selectedFile()">
        <span class="drop-icon">☁️</span>
        <p class="drop-title">
          <strong>Arrastra tu archivo aquí</strong> o haz clic para explorar
        </p>
        <span class="drop-hint">Soporta PDF, Markdown (.md) y Texto (.txt) hasta 20MB</span>
      </div>

      <div class="file-preview" *ngIf="selectedFile()">
        <span class="file-icon">📄</span>
        <div class="file-info">
          <strong>{{ selectedFile()?.name }}</strong>
          <span>{{ (selectedFile()?.size || 0) / 1024 | number: '1.0-0' }} KB</span>
        </div>
        <button
          type="button"
          class="btn-remove"
          title="Quitar archivo"
          (click)="$event.stopPropagation(); clear()"
        >
          ✕
        </button>
      </div>

      <ng-content select="[dropzone-footer]"></ng-content>
    </div>

    <!-- OCR (AI Vision) opt-in, only offered for PDFs -->
    <label
      class="vision-toggle"
      *ngIf="isPdfSelected()"
      (click)="$event.stopPropagation()"
    >
      <input
        type="checkbox"
        [checked]="useAiVision()"
        (change)="toggleVision($event)"
      />
      <span class="vision-text">
        <strong>Usar OCR</strong>
        <small>Extraer texto de PDFs escaneados</small>
      </span>
    </label>

    <ng-content select="[after-dropzone]"></ng-content>
  `,
  styles: [`
    .dropzone {
      border: 2px dashed var(--border-subtle);
      border-radius: 12px;
      padding: 1.75rem 1.25rem;
      text-align: center;
      background: var(--bg-app);
      transition: all 0.2s ease;
      cursor: pointer;
      position: relative;
    }
    .dropzone.compact { padding: 1rem; }
    .dropzone.dragover { border-color: #6366F1; background: rgba(99, 102, 241, 0.08); }
    .dropzone.disabled { opacity: 0.6; pointer-events: none; cursor: not-allowed; }

    .dropzone-main { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; }
    .drop-icon { font-size: 1.8rem; }
    .drop-title { margin: 0; font-size: 0.95rem; }
    .drop-hint { margin: 0; font-size: 0.8rem; color: var(--text-secondary); }

    .file-preview {
      display: flex; align-items: center; gap: 0.75rem;
      padding: 0.75rem 1rem; border-radius: 10px;
      background: var(--bg-surface); border: 1px solid var(--border-subtle); text-align: left;
    }
    .file-icon { font-size: 1.4rem; }
    .file-info { flex: 1; display: flex; flex-direction: column; gap: 0.15rem; }
    .file-info strong { font-size: 0.9rem; }
    .file-info span { font-size: 0.8rem; color: var(--text-secondary); }
    .btn-remove {
      border: 1px solid var(--border-subtle); background: transparent;
      color: var(--text-secondary); border-radius: 999px; width: 28px; height: 28px; cursor: pointer;
    }

    .vision-toggle {
      display: flex; align-items: flex-start; gap: 0.6rem; margin-top: 0.75rem;
      padding: 0.65rem 0.85rem; border-radius: 10px; cursor: pointer;
      background: rgba(99, 102, 241, 0.06); border: 1px solid var(--border-subtle);
    }
    .vision-toggle input { margin-top: 0.2rem; accent-color: #6366F1; }
    .vision-text { display: flex; flex-direction: column; gap: 0.1rem; }
    .vision-text strong { font-size: 0.85rem; }
    .vision-text small { font-size: 0.75rem; color: var(--text-secondary); }
  `]
})
export class SharedDropzoneComponent {
  @Input() disabled = false;
  @Input() compact = false;
  @Input() accept = '.pdf,.md,.txt';

  @Output() fileSelected = new EventEmitter<File>();
  @Output() useAiVisionChange = new EventEmitter<boolean>();

  isDragging = signal(false);
  selectedFile = signal<File | null>(null);
  useAiVision = signal(false);

  constructor() {
    // Keep the OCR flag in sync for the parent: it only applies to PDFs.
    effect(() => {
      const pdf = this.isPdfSelected();
      const vision = this.useAiVision();
      this.useAiVisionChange.emit(pdf && vision);
    });
  }

  isPdfSelected(): boolean {
    const file = this.selectedFile();
    return !!file && file.name.toLowerCase().endsWith('.pdf');
  }

  onDragOver(e: DragEvent) {
    e.preventDefault();
    if (!this.disabled) this.isDragging.set(true);
  }
  onDragLeave(e: DragEvent) {
    e.preventDefault();
    this.isDragging.set(false);
  }
  onDrop(e: DragEvent) {
    e.preventDefault();
    this.isDragging.set(false);
    if (this.disabled) return;
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      this.pick(e.dataTransfer.files[0]);
    }
  }
  onClick(input: HTMLInputElement) {
    if (this.disabled) return;
    input.click();
  }
  onFileSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.pick(input.files[0]);
      input.value = '';
    }
  }
  toggleVision(e: Event) {
    e.stopPropagation();
    this.useAiVision.set((e.target as HTMLInputElement).checked);
  }
  pick(file: File) {
    this.selectedFile.set(file);
    // A fresh file resets the OCR opt-in.
    this.useAiVision.set(false);
    this.fileSelected.emit(file);
    this.useAiVisionChange.emit(false);
  }
  clear() {
    this.selectedFile.set(null);
    this.useAiVision.set(false);
  }
}
