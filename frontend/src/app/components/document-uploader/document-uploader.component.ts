import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-document-uploader',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="uploader-card">
      <h3 class="title">📥 Carga de Documentación Técnica</h3>
      
      <!-- Drag & Drop / File Selector Area -->
      <div 
        class="file-dropzone"
        (click)="fileInput.click()"
      >
        <span class="drop-icon">📄</span>
        <div class="drop-title">Haz clic o arrastra aquí un archivo (PDF, Markdown o TXT)</div>
        <div class="drop-sub">Formatos soportados: <strong>.pdf</strong>, <strong>.md</strong>, <strong>.markdown</strong>, <strong>.txt</strong></div>
        <input 
          #fileInput
          type="file" 
          class="file-input-hidden" 
          accept=".pdf,.md,.markdown,.txt" 
          (change)="onFileSelected($event)"
        />
        <div *ngIf="selectedFileName" class="file-badge">
          📄 {{ selectedFileName }}
        </div>
      </div>

      <div class="input-group">
        <label>Título del Documento:</label>
        <input 
          type="text" 
          [(ngModel)]="documentoTitulo" 
          placeholder="Ej: Introducción a la Arquitectura de Redes VCN en OCI" 
          class="text-input"
        />
      </div>

      <div class="input-group">
        <label>Contenido Técnico Extraído (Editable):</label>
        <textarea 
          [(ngModel)]="documentoContenido" 
          rows="6" 
          placeholder="Pega aquí la documentación técnica o selecciona un archivo arriba..."
          class="textarea-input"
        ></textarea>
      </div>
    </div>
  `,
  styles: [`
    .uploader-card { background: #ffffff; padding: 1.5rem; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 1.5rem; }
    .title { font-size: 1.15rem; font-weight: 700; color: #1e293b; margin-bottom: 1rem; }
    .file-dropzone { border: 2px dashed #94a3b8; border-radius: 10px; padding: 1.5rem; text-align: center; background: #f8fafc; cursor: pointer; transition: all 0.2s ease; margin-bottom: 1rem; }
    .file-dropzone:hover { border-color: #2563eb; background: #eff6ff; }
    .drop-icon { font-size: 2.2rem; display: block; margin-bottom: 0.5rem; }
    .drop-title { font-weight: 700; font-size: 1rem; color: #1e293b; margin-bottom: 0.25rem; }
    .drop-sub { font-size: 0.82rem; color: #64748b; }
    .file-input-hidden { display: none; }
    .file-badge { display: inline-block; background: #dbeafe; color: #1e40af; padding: 0.4rem 0.85rem; border-radius: 20px; font-size: 0.85rem; font-weight: 600; margin-top: 0.75rem; }
    .input-group { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
    label { font-size: 0.85rem; font-weight: 600; color: #475569; }
    .text-input, .textarea-input { padding: 0.75rem; border-radius: 6px; border: 1px solid #cbd5e1; font-size: 0.95rem; font-family: inherit; }
    .textarea-input { resize: vertical; }
  `]
})
export class DocumentUploaderComponent {
  documentoTitulo: string = 'Introduccion a la Arquitectura de Redes VCN en OCI';
  documentoContenido: string = 'La Virtual Cloud Network (VCN) es una red privada y personalizable configurada en Oracle Cloud Infrastructure. Similar a una red de centro de datos tradicional, la VCN ofrece control total sobre su entorno de red, incluyendo subredes publicas y privadas, tablas de enrutamiento, Internet Gateways, NAT Gateways y Security Lists para control de trafico mediante reglas de entrada (ingress) y salida (egress).';
  selectedFileName: string = '';

  @Output() documentLoaded = new EventEmitter<any>();

  constructor(private http: HttpClient) {}

  onFileSelected(event: any): void {
    const files = event.target.files;
    if (files && files.length > 0) {
      const file = files[0];
      this.selectedFileName = file.name;

      const cleanTitle = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
      this.documentoTitulo = cleanTitle.charAt(0).toUpperCase() + cleanTitle.slice(1);

      const ext = file.name.split('.').pop().toLowerCase();

      if (ext === 'txt' || ext === 'md' || ext === 'markdown') {
        const reader = new FileReader();
        reader.onload = (e: any) => {
          this.documentoContenido = e.target.result;
        };
        reader.readAsText(file);
      } else if (ext === 'pdf') {
        const formData = new FormData();
        formData.append('file', file);

        this.http.post<any>('http://localhost:8000/api/v1/parse-pdf', formData).subscribe({
          next: (data) => {
            if (data.texto_extraido) {
              this.documentoContenido = data.texto_extraido;
            }
          },
          error: (err) => console.error('Error parseando PDF:', err)
        });
      }
    }
  }

  getDocumentData() {
    return {
      documento_titulo: this.documentoTitulo,
      documento_contenido: this.documentoContenido
    };
  }
}
