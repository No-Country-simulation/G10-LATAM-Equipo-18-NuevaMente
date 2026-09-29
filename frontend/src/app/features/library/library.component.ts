import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';

export interface LibraryDocument {
  id: string;
  titulo: string;
  perfil: string;
  formato: string;
  nicho: string;
  fecha: string;
  score_rag: number;
  oci_status: 'completado' | 'pendiente';
}

@Component({
  selector: 'app-library',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="library-container">
      <div class="page-header">
        <h1>Biblioteca de Paquetes Educativos</h1>
        <p>Historial completo de documentación adaptada y almacenada en Oracle Cloud Infrastructure.</p>
      </div>

      <!-- Filters & Search Bar -->
      <div class="controls-bar glass-card">
        <div class="search-input-box">
          <span class="search-icon">🔍</span>
          <input 
            type="text" 
            placeholder="Buscar por título de documento..."
            [value]="searchTerm()"
            (input)="updateSearch($event)"
          />
        </div>

        <div class="filters-row">
          <select [value]="selectedPerfil()" (change)="updatePerfil($event)">
            <option value="">Todos los perfiles</option>
            <option value="Principiante">Principiante</option>
            <option value="Desarrollador">Desarrollador</option>
            <option value="Lider Tecnico">Líder Técnico</option>
            <option value="Ejecutivo">Ejecutivo</option>
          </select>

          <select [value]="selectedFormato()" (change)="updateFormato($event)">
            <option value="">Todos los formatos</option>
            <option value="Flashcards">Flashcards</option>
            <option value="Quiz">Quiz</option>
            <option value="Tutorial">Tutorial</option>
            <option value="Resumen Ejecutivo">Resumen Ejecutivo</option>
            <option value="Guion de Clase">Guion de Clase</option>
          </select>
        </div>
      </div>

      <!-- Table of Documents -->
      <div class="table-card glass-card" *ngIf="filteredDocuments().length > 0">
        <table class="library-table">
          <thead>
            <tr>
              <th>Documento</th>
              <th>Perfil</th>
              <th>Formato</th>
              <th>Sector</th>
              <th>Anclaje RAG</th>
              <th>Estado OCI</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let doc of filteredDocuments()">
              <td class="td-title">
                <strong>{{ doc.titulo }}</strong>
                <span class="doc-date">{{ doc.fecha }}</span>
              </td>
              <td><span class="badge-profile">{{ doc.perfil }}</span></td>
              <td><span class="badge-format">{{ doc.formato }}</span></td>
              <td>{{ doc.nicho }}</td>
              <td><span class="rag-score">🛡️ {{ (doc.score_rag * 100) | number:'1.0-0' }}%</span></td>
              <td>
                <span class="badge-oci" [class.done]="doc.oci_status === 'completado'">
                  {{ doc.oci_status }}
                </span>
              </td>
              <td class="td-actions">
                <button class="btn-action-icon" (click)="deleteDoc(doc.id)" title="Eliminar">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      <div class="empty-state glass-card" *ngIf="filteredDocuments().length === 0">
        <span class="empty-icon">📂</span>
        <h3>No se encontraron documentos</h3>
        <p>Prueba ajustando los filtros de búsqueda o crea una nueva adaptación en el Workspace.</p>
      </div>
    </div>
  `,
  styles: [`
    .library-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 1rem 0;
    }

    .page-header {
      margin-bottom: 2rem;
    }

    .page-header h1 {
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 0.5rem;
    }

    .page-header p {
      color: var(--text-secondary);
      font-size: 1.05rem;
    }

    .controls-bar {
      padding: 1.25rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      gap: 1.5rem;
      margin-bottom: 2rem;
    }

    .search-input-box {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      background: var(--bg-app);
      padding: 0.6rem 1rem;
      border-radius: 10px;
      border: 1px solid var(--border-subtle);
    }

    .search-input-box input {
      background: transparent;
      border: none;
      width: 100%;
      font-size: 0.95rem;
      color: var(--text-primary);
      outline: none;
    }

    .filters-row {
      display: flex;
      gap: 0.75rem;
    }

    .filters-row select {
      padding: 0.6rem 1rem;
      border-radius: 10px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-size: 0.9rem;
      outline: none;
    }

    .table-card {
      padding: 1rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      overflow-x: auto;
    }

    .library-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }

    .library-table th {
      padding: 1rem;
      font-size: 0.78rem;
      font-weight: 800;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-subtle);
      letter-spacing: 0.05em;
    }

    .library-table td {
      padding: 1.15rem 1rem;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 0.92rem;
    }

    .td-title {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }

    .doc-date {
      font-size: 0.78rem;
      color: var(--text-muted);
    }

    .badge-profile, .badge-format {
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-size: 0.8rem;
      font-weight: 600;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
    }

    .rag-score {
      color: #10B981;
      font-weight: 700;
    }

    .badge-oci {
      font-size: 0.75rem;
      font-weight: 800;
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      background: var(--slate-200);
    }

    .badge-oci.done {
      background: rgba(16, 185, 129, 0.15);
      color: #059669;
    }

    .btn-action-icon {
      background: transparent;
      border: none;
      cursor: pointer;
      font-size: 1rem;
    }

    .empty-state {
      padding: 4rem 2rem;
      text-align: center;
      border-radius: 20px;
    }

    .empty-icon {
      font-size: 3rem;
      display: block;
      margin-bottom: 1rem;
    }
  `]
})
export class LibraryComponent {
  searchTerm = signal<string>('');
  selectedPerfil = signal<string>('');
  selectedFormato = signal<string>('');

  documents = signal<LibraryDocument[]>([
    {
      id: 'doc-1',
      titulo: 'Introducción a la Arquitectura de Redes VCN en OCI',
      perfil: 'Desarrollador',
      formato: 'Tutorial',
      nicho: 'Fintech',
      fecha: '2026-09-29 05:10',
      score_rag: 0.98,
      oci_status: 'completado'
    },
    {
      id: 'doc-2',
      titulo: 'Guía de Microservicios & Kubernetes OKE',
      perfil: 'Lider Tecnico',
      formato: 'Flashcards',
      nicho: 'General',
      fecha: '2026-09-28 18:30',
      score_rag: 0.96,
      oci_status: 'completado'
    },
    {
      id: 'doc-3',
      titulo: 'Manual de Seguridad & IAM Policies en OCI',
      perfil: 'Ejecutivo',
      formato: 'Resumen Ejecutivo',
      nicho: 'Salud',
      fecha: '2026-09-27 14:15',
      score_rag: 0.99,
      oci_status: 'completado'
    }
  ]);

  filteredDocuments = computed(() => {
    const query = this.searchTerm().toLowerCase();
    const perf = this.selectedPerfil();
    const fmt = this.selectedFormato();

    return this.documents().filter(doc => {
      const matchQuery = doc.titulo.toLowerCase().includes(query);
      const matchPerf = !perf || doc.perfil === perf;
      const matchFmt = !fmt || doc.formato === fmt;
      return matchQuery && matchPerf && matchFmt;
    });
  });

  updateSearch(event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.searchTerm.set(val);
  }

  updatePerfil(event: Event): void {
    const val = (event.target as HTMLSelectElement).value;
    this.selectedPerfil.set(val);
  }

  updateFormato(event: Event): void {
    const val = (event.target as HTMLSelectElement).value;
    this.selectedFormato.set(val);
  }

  deleteDoc(id: string): void {
    this.documents.update(docs => docs.filter(d => d.id !== id));
  }
}
