import { Component, signal, computed, inject, OnInit, HostListener, ElementRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { StateService, RecentProject } from '../../core/services/state.service';
import { ExportService } from '../../core/services/export.service';
import { environment } from '../../../environments/environment';
import { getDaysRemainingStatus, DaysRemainingStatus } from '../../core/utils/trash-utils';

export type SortOption = 'vencimiento' | 'recientes' | 'titulo';

@Component({
  selector: 'app-trash',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="trash-container">
      <!-- TOAST NOTIFICATION -->
      <div class="toast-notification" *ngIf="toastMsg()" role="status" aria-live="polite">
        <span>{{ toastMsg() }}</span>
      </div>

      <!-- PAGE HEADER & BANNER -->
      <div class="page-header">
        <div class="header-titles">
          <h1>Papelera de Contenidos</h1>
          <p>Gestiona los proyectos eliminados antes de su purga definitiva.</p>
        </div>

        <button 
          type="button" 
          class="btn-empty-trash" 
          *ngIf="projectsList().length > 0"
          (click)="openEmptyTrashModal()"
          aria-label="Vaciar papelera completa"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          Vaciar papelera
        </button>
      </div>

      <!-- DYNAMIC RETENTION INFO BANNER -->
      <div class="info-banner glass-card" role="region" aria-label="Información de retención">
        <div class="banner-icon-box">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        </div>
        <div class="banner-text">
          <strong>Retención Automática Activa</strong>
          <p>Los elementos se eliminan automáticamente tras {{ retentionDays }} días. Pasado ese plazo no se pueden recuperar.</p>
        </div>
      </div>

      <!-- CONTROLS & SEARCH BAR -->
      <div class="controls-bar glass-card">
        <div class="search-input-box">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <input 
            type="text" 
            placeholder="Buscar por título en la papelera..."
            [value]="searchTerm()"
            (input)="updateSearch($event)"
            aria-label="Buscar por título en la papelera"
          />
        </div>

        <div class="filters-row">
          <select [value]="selectedPerfil()" (change)="updatePerfil($event)" aria-label="Filtrar por perfil">
            <option value="">Todos los perfiles</option>
            <option value="Principiante">Principiante</option>
            <option value="Desarrollador">Desarrollador</option>
            <option value="Lider Tecnico">Líder Técnico</option>
            <option value="Ejecutivo">Ejecutivo</option>
          </select>

          <select [value]="selectedFormato()" (change)="updateFormato($event)" aria-label="Filtrar por formato">
            <option value="">Todos los formatos</option>
            <option value="Flashcards">Flashcards</option>
            <option value="Quiz">Quiz</option>
            <option value="Tutorial">Tutorial</option>
            <option value="Resumen Ejecutivo">Resumen Ejecutivo</option>
            <option value="Guion de Clase">Guion de Clase</option>
          </select>

          <select [value]="sortBy()" (change)="updateSort($event)" aria-label="Ordenar resultados">
            <option value="vencimiento">⏱️ Próximos a vencer</option>
            <option value="recientes">📅 Más recientes</option>
            <option value="titulo">🔤 Título A-Z</option>
          </select>
        </div>
      </div>

      <!-- BATCH ACTIONS FLOATING BAR -->
      <div class="batch-actions-bar glass-card" *ngIf="selectedIds().size > 0">
        <div class="batch-count-info">
          <span class="batch-badge">{{ selectedIds().size }}</span>
          <span>elemento(s) seleccionado(s)</span>
        </div>
        <div class="batch-buttons">
          <button 
            type="button" 
            class="btn-batch-restore" 
            (click)="restoreBatch()"
            aria-label="Restaurar seleccionados"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            Restaurar seleccionados
          </button>
          <button 
            type="button" 
            class="btn-batch-delete" 
            (click)="openBatchDeleteModal()"
            aria-label="Eliminar seleccionados definitivamente"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            Eliminar seleccionados
          </button>
          <button type="button" class="btn-batch-clear" (click)="clearSelection()">✕ Cancelar</button>
        </div>
      </div>

      <!-- LOADING SKELETON STATE -->
      <div class="skeleton-wrapper glass-card" *ngIf="isLoading()">
        <div class="skeleton-row" *ngFor="let i of [1,2,3]"></div>
      </div>

      <!-- ERROR RETRY STATE -->
      <div class="error-state glass-card" *ngIf="hasError() && !isLoading()">
        <span class="error-icon">⚠️</span>
        <h3>No se pudo cargar la papelera</h3>
        <p>Ocurrió un inconveniente al listar los elementos.</p>
        <button type="button" class="btn-retry" (click)="refreshProjects()">🔄 Reintentar</button>
      </div>

      <!-- TABLE & MOBILE CARDS CONTENT -->
      <div class="table-card glass-card" *ngIf="!isLoading() && !hasError() && filteredProjects().length > 0">
        <table class="trash-table">
          <thead>
            <tr>
              <th class="th-checkbox">
                <input 
                  type="checkbox" 
                  [checked]="isAllSelected()" 
                  (change)="toggleSelectAll($event)"
                  aria-label="Seleccionar todos los documentos de la papelera"
                />
              </th>
              <th>Documento</th>
              <th>Perfil</th>
              <th>Formato</th>
              <th>Fecha Eliminación</th>
              <th>Tiempo Restante</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              *ngFor="let proj of filteredProjects()" 
              [class.row-selected]="selectedIds().has(proj.id)"
              (click)="openPreview(proj)"
            >
              <td class="td-checkbox" (click)="$event.stopPropagation()">
                <input 
                  type="checkbox" 
                  [checked]="selectedIds().has(proj.id)" 
                  (change)="toggleSelectProject(proj.id)"
                  [attr.aria-label]="'Seleccionar ' + proj.nombre"
                />
              </td>
              <td class="td-title">
                <strong>{{ proj.nombre }}</strong>
                <span class="doc-sub">{{ proj.descripcion }}</span>
              </td>
              <td><span class="badge-profile">{{ proj.perfil }}</span></td>
              <td><span class="badge-format">{{ proj.formato }}</span></td>
              <td>
                <span class="deleted-date">{{ formatDate(proj.deletedAt) }}</span>
              </td>
              <td (click)="$event.stopPropagation()">
                <div class="countdown-box">
                  <span 
                    class="countdown-badge" 
                    [class.badge-green]="getCountdown(proj.purgeAt).colorClass === 'green'"
                    [class.badge-amber]="getCountdown(proj.purgeAt).colorClass === 'amber'"
                    [class.badge-red]="getCountdown(proj.purgeAt).colorClass === 'red'"
                  >
                    {{ getCountdown(proj.purgeAt).label }}
                  </span>
                  <!-- SVG Mini Retention Ratio Bar -->
                  <div class="progress-bar-track" aria-hidden="true">
                    <div 
                      class="progress-bar-fill" 
                      [class.fill-green]="getCountdown(proj.purgeAt).colorClass === 'green'"
                      [class.fill-amber]="getCountdown(proj.purgeAt).colorClass === 'amber'"
                      [class.fill-red]="getCountdown(proj.purgeAt).colorClass === 'red'"
                      [style.width.%]="getCountdown(proj.purgeAt).ratio * 100"
                    ></div>
                  </div>
                </div>
              </td>
              <td class="td-actions" (click)="$event.stopPropagation()">
                <button 
                  type="button" 
                  class="btn-restore" 
                  (click)="restoreSingle(proj)" 
                  title="Restaurar a Biblioteca"
                  [attr.aria-label]="'Restaurar ' + proj.nombre + ' a la biblioteca'"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                  Restaurar
                </button>

                <button 
                  type="button" 
                  class="btn-delete-perm" 
                  (click)="openDeleteConfirmModal(proj)" 
                  title="Eliminar definitivamente"
                  [attr.aria-label]="'Eliminar definitivamente ' + proj.nombre"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                  Eliminar
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- EMPTY STATE VIEW -->
      <div class="empty-state glass-card" *ngIf="!isLoading() && !hasError() && filteredProjects().length === 0">
        <div class="empty-icon-wrapper">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="1.5"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
        </div>
        <h3>Tu papelera está vacía</h3>
        <p>Los elementos que muevas a la papelera desde la Biblioteca aparecerán aquí antes de su eliminación definitiva.</p>
      </div>

      <!-- ACCESSIBLE CONFIRMATION DIALOG (role="alertdialog") -->
      <div 
        class="modal-backdrop" 
        *ngIf="confirmModal().isOpen"
        (click)="closeConfirmModal()"
      >
        <div 
          class="modal-card glass-card" 
          role="alertdialog" 
          aria-modal="true"
          aria-labelledby="confirm-modal-title"
          aria-describedby="confirm-modal-desc"
          (click)="$event.stopPropagation()"
        >
          <div class="modal-header">
            <span class="warning-badge-icon">⚠️</span>
            <h3 id="confirm-modal-title">{{ confirmModal().title }}</h3>
          </div>

          <p id="confirm-modal-desc" class="modal-desc">{{ confirmModal().description }}</p>

          <div class="modal-actions">
            <button 
              #cancelBtn
              type="button" 
              class="btn-cancel-modal" 
              (click)="closeConfirmModal()"
            >
              Cancelar
            </button>

            <button 
              type="button" 
              class="btn-confirm-delete" 
              (click)="executeModalAction()"
            >
              Eliminar definitivamente
            </button>
          </div>
        </div>
      </div>

      <!-- READ-ONLY PREVIEW DRAWER / MODAL -->
      <div class="modal-backdrop" *ngIf="previewProject()" (click)="previewProject.set(null)">
        <div class="preview-drawer-card glass-card" (click)="$event.stopPropagation()" role="dialog" aria-label="Vista previa de documento">
          <div class="preview-header">
            <div>
              <span class="readonly-tag">🔒 VISTA PREVIA DE SOLO LECTURA (PAPELERA)</span>
              <h2>{{ previewProject()?.nombre }}</h2>
            </div>
            <button type="button" class="btn-close-drawer" (click)="previewProject.set(null)">✕</button>
          </div>

          <div class="preview-body" *ngIf="previewProject()?.response">
            <div class="preview-meta-row">
              <span class="meta-item"><strong>Perfil:</strong> {{ previewProject()?.perfil }}</span>
              <span class="meta-item"><strong>Formato:</strong> {{ previewProject()?.formato }}</span>
              <span class="meta-item"><strong>Anclaje:</strong> {{ ((previewProject()?.response?.evaluacion_calidad?.anclaje_fuente_score || 0.98) * 100) | number:'1.0-0' }}%</span>
            </div>

            <div class="preview-intro-box">
              <p>{{ previewProject()?.response?.contenido_adaptado?.introduccion_contextualizada }}</p>
            </div>

            <div class="preview-concepts">
              <strong>Conceptos Clave:</strong>
              <div class="concept-chips">
                <span class="c-chip" *ngFor="let c of previewProject()?.response?.metadatos?.conceptos_clave">{{ c }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .trash-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 1rem 0;
      position: relative;
    }

    .toast-notification {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      z-index: 1000;
      background: var(--bg-surface);
      border: 1px solid #10B981;
      color: var(--text-primary);
      padding: 0.85rem 1.25rem;
      border-radius: 14px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
      font-size: 0.9rem;
      font-weight: 600;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .header-titles h1 {
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 0.4rem;
    }

    .header-titles p {
      color: var(--text-secondary);
      font-size: 1.05rem;
    }

    .btn-empty-trash {
      background: rgba(239, 68, 68, 0.12);
      color: #EF4444;
      border: 1px solid rgba(239, 68, 68, 0.3);
      padding: 0.6rem 1.1rem;
      border-radius: 10px;
      font-size: 0.88rem;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      transition: all 0.2s;
    }
    .btn-empty-trash:hover {
      background: #EF4444;
      color: #FFFFFF;
    }

    .info-banner {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 1rem 1.25rem;
      border-radius: 16px;
      background: rgba(99, 102, 241, 0.08);
      border: 1px solid rgba(99, 102, 241, 0.25);
      margin-bottom: 1.5rem;
    }

    .banner-text strong {
      display: block;
      font-size: 0.92rem;
      color: #6366F1;
      margin-bottom: 0.15rem;
    }

    .banner-text p {
      font-size: 0.88rem;
      color: var(--text-secondary);
      margin: 0;
    }

    .controls-bar {
      padding: 1.25rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      gap: 1.25rem;
      margin-bottom: 1.5rem;
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
      color: var(--text-muted);
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

    .batch-actions-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.85rem 1.25rem;
      background: rgba(99, 102, 241, 0.08);
      border: 1px solid rgba(99, 102, 241, 0.3);
      border-radius: 14px;
      margin-bottom: 1.5rem;
    }

    .batch-count-info {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 0.9rem;
      font-weight: 600;
    }

    .batch-badge {
      background: #4F46E5;
      color: #FFF;
      padding: 0.15rem 0.6rem;
      border-radius: 12px;
      font-size: 0.82rem;
      font-weight: 800;
    }

    .batch-buttons {
      display: flex;
      gap: 0.75rem;
    }

    .btn-batch-restore {
      background: #10B981;
      color: #FFF;
      border: none;
      padding: 0.45rem 0.9rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .btn-batch-delete {
      background: #EF4444;
      color: #FFF;
      border: none;
      padding: 0.45rem 0.9rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }

    .btn-batch-clear {
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      padding: 0.45rem 0.85rem;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
    }

    .table-card {
      padding: 1rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      overflow-x: auto;
    }

    .trash-table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
    }

    .trash-table th {
      padding: 1rem;
      font-size: 0.78rem;
      font-weight: 800;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-subtle);
      letter-spacing: 0.05em;
    }

    .th-checkbox, .td-checkbox {
      width: 40px;
      text-align: center;
    }

    .trash-table td {
      padding: 1.15rem 1rem;
      border-bottom: 1px solid var(--border-subtle);
      font-size: 0.92rem;
      cursor: pointer;
    }

    .trash-table tr:hover {
      background: var(--bg-app);
    }

    .td-title {
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }

    .doc-sub {
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
      white-space: nowrap;
    }

    .deleted-date {
      font-size: 0.82rem;
      color: var(--text-secondary);
      white-space: nowrap;
    }

    .countdown-box {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
      width: 140px;
    }

    .countdown-badge {
      font-size: 0.78rem;
      font-weight: 800;
      padding: 0.2rem 0.5rem;
      border-radius: 6px;
      display: inline-block;
      white-space: nowrap;
    }

    .badge-green { background: rgba(16, 185, 129, 0.15); color: #059669; }
    .badge-amber { background: rgba(245, 158, 11, 0.15); color: #D97706; }
    .badge-red { background: rgba(239, 68, 68, 0.15); color: #DC2626; }

    .progress-bar-track {
      width: 100%;
      height: 4px;
      background: var(--border-subtle);
      border-radius: 2px;
      overflow: hidden;
    }

    .progress-bar-fill {
      height: 100%;
      transition: width 0.3s;
    }

    .fill-green { background: #10B981; }
    .fill-amber { background: #F59E0B; }
    .fill-red { background: #EF4444; }

    .td-actions {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .btn-restore {
      background: #10B981;
      color: #FFFFFF;
      border: none;
      padding: 0.45rem 0.8rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }
    .btn-restore:hover { background: #059669; }

    .btn-delete-perm {
      background: rgba(239, 68, 68, 0.12);
      color: #EF4444;
      border: 1px solid rgba(239, 68, 68, 0.3);
      padding: 0.45rem 0.8rem;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
    }
    .btn-delete-perm:hover {
      background: #EF4444;
      color: #FFFFFF;
    }

    .empty-state {
      padding: 4rem 2rem;
      text-align: center;
      border-radius: 20px;
    }

    .empty-icon-wrapper {
      width: 80px;
      height: 80px;
      border-radius: 50%;
      background: rgba(99, 102, 241, 0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 1.5rem auto;
    }

    .skeleton-wrapper {
      padding: 2rem;
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .skeleton-row {
      height: 50px;
      background: linear-gradient(90deg, var(--bg-app) 25%, var(--border-subtle) 50%, var(--bg-app) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
      border-radius: 10px;
    }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    /* CONFIRMATION ACCESSIBLE MODAL */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(5px);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
    }

    .modal-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 20px;
      padding: 2rem;
      max-width: 480px;
      width: 100%;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    }

    .modal-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1rem;
    }

    .warning-badge-icon {
      font-size: 1.5rem;
    }

    .modal-header h3 {
      font-size: 1.25rem;
      font-weight: 800;
    }

    .modal-desc {
      color: var(--text-secondary);
      font-size: 0.95rem;
      line-height: 1.5;
      margin-bottom: 1.75rem;
    }

    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.75rem;
    }

    .btn-cancel-modal {
      padding: 0.65rem 1.25rem;
      border-radius: 10px;
      background: var(--bg-app);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-weight: 700;
      cursor: pointer;
    }

    .btn-confirm-delete {
      padding: 0.65rem 1.25rem;
      border-radius: 10px;
      background: #EF4444;
      color: #FFFFFF;
      border: none;
      font-weight: 700;
      cursor: pointer;
    }

    /* PREVIEW DRAWER */
    .preview-drawer-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 20px;
      padding: 2rem;
      max-width: 700px;
      width: 100%;
      max-height: 80vh;
      overflow-y: auto;
    }

    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 1.5rem;
    }

    .readonly-tag {
      font-size: 0.75rem;
      font-weight: 800;
      color: #F59E0B;
      display: block;
      margin-bottom: 0.3rem;
    }

    .btn-close-drawer {
      background: transparent;
      border: none;
      font-size: 1.2rem;
      color: var(--text-muted);
      cursor: pointer;
    }

    .preview-meta-row {
      display: flex;
      gap: 1rem;
      margin-bottom: 1rem;
      font-size: 0.88rem;
    }

    .preview-intro-box {
      background: var(--bg-app);
      padding: 1rem;
      border-radius: 12px;
      margin-bottom: 1rem;
      line-height: 1.6;
    }

    .concept-chips {
      display: flex;
      gap: 0.5rem;
      margin-top: 0.5rem;
    }

    .c-chip {
      background: rgba(99, 102, 241, 0.1);
      color: #6366F1;
      font-size: 0.78rem;
      font-weight: 600;
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
    }
  `]
})
export class TrashComponent implements OnInit {
  private stateService = inject(StateService);
  readonly retentionDays = environment.trashRetentionDays ?? 15;

  @ViewChild('cancelBtn') cancelBtnRef?: ElementRef<HTMLButtonElement>;

  searchTerm = signal<string>('');
  selectedPerfil = signal<string>('');
  selectedFormato = signal<string>('');
  sortBy = signal<SortOption>('vencimiento');
  isLoading = signal<boolean>(false);
  hasError = signal<boolean>(false);

  projectsList = signal<RecentProject[]>([]);
  selectedIds = signal<Set<string>>(new Set());
  previewProject = signal<RecentProject | null>(null);
  toastMsg = signal<string | null>(null);

  confirmModal = signal<{
    isOpen: boolean;
    type: 'single' | 'batch' | 'empty';
    targetProject?: RecentProject;
    title: string;
    description: string;
  }>({
    isOpen: false,
    type: 'single',
    title: '',
    description: ''
  });

  ngOnInit(): void {
    this.refreshProjects();
  }

  refreshProjects(): void {
    this.isLoading.set(true);
    this.hasError.set(false);

    try {
      const list = this.stateService.getTrashProjects();
      this.projectsList.set([...list]);
      this.isLoading.set(false);
    } catch (e) {
      this.isLoading.set(false);
      this.hasError.set(true);
    }
  }

  filteredProjects = computed(() => {
    const query = this.searchTerm().toLowerCase();
    const perf = this.selectedPerfil();
    const fmt = this.selectedFormato();
    const sort = this.sortBy();

    let list = this.projectsList().filter(proj => {
      const matchQuery = proj.nombre.toLowerCase().includes(query);
      const matchPerf = !perf || proj.perfil.includes(perf);
      const matchFmt = !fmt || proj.formato.includes(fmt);
      return matchQuery && matchPerf && matchFmt;
    });

    if (sort === 'vencimiento') {
      list.sort((a, b) => {
        const daysA = getDaysRemainingStatus(a.purgeAt).days;
        const daysB = getDaysRemainingStatus(b.purgeAt).days;
        return daysA - daysB;
      });
    } else if (sort === 'recientes') {
      list.sort((a, b) => {
        const dateA = a.deletedAt ? new Date(a.deletedAt).getTime() : 0;
        const dateB = b.deletedAt ? new Date(b.deletedAt).getTime() : 0;
        return dateB - dateA;
      });
    } else if (sort === 'titulo') {
      list.sort((a, b) => a.nombre.localeCompare(b.nombre));
    }

    return list;
  });

  getCountdown(purgeAt?: string | null): DaysRemainingStatus {
    return getDaysRemainingStatus(purgeAt);
  }

  formatDate(isoDate?: string | null): string {
    if (!isoDate) return '-';
    const d = new Date(isoDate);
    if (isNaN(d.getTime())) return '-';
    return `${d.getDate()} ${d.toLocaleString('es-ES', { month: 'short' })}. ${d.getFullYear()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
  }

  isAllSelected(): boolean {
    const list = this.filteredProjects();
    if (list.length === 0) return false;
    return list.every(p => this.selectedIds().has(p.id));
  }

  toggleSelectAll(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const current = new Set(this.selectedIds());
    if (checked) {
      this.filteredProjects().forEach(p => current.add(p.id));
    } else {
      this.filteredProjects().forEach(p => current.delete(p.id));
    }
    this.selectedIds.set(current);
  }

  toggleSelectProject(id: string): void {
    const current = new Set(this.selectedIds());
    if (current.has(id)) {
      current.delete(id);
    } else {
      current.add(id);
    }
    this.selectedIds.set(current);
  }

  clearSelection(): void {
    this.selectedIds.set(new Set());
  }

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

  updateSort(event: Event): void {
    const val = (event.target as HTMLSelectElement).value as SortOption;
    this.sortBy.set(val);
  }

  openPreview(proj: RecentProject): void {
    this.previewProject.set(proj);
  }

  restoreSingle(proj: RecentProject): void {
    this.stateService.restoreFromTrash(proj.id);
    this.showToast(`" ${proj.nombre} " restaurado a la biblioteca.`);
    this.refreshProjects();
  }

  restoreBatch(): void {
    const ids = Array.from(this.selectedIds());
    ids.forEach(id => this.stateService.restoreFromTrash(id));
    this.selectedIds.set(new Set());
    this.showToast(`${ids.length} elementos restaurados a la biblioteca.`);
    this.refreshProjects();
  }

  openDeleteConfirmModal(proj: RecentProject): void {
    this.confirmModal.set({
      isOpen: true,
      type: 'single',
      targetProject: proj,
      title: '¿Eliminar definitivamente este documento?',
      description: `Esta acción eliminará de forma permanente "${proj.nombre}". Pasado este punto, no se podrá recuperar de la biblioteca ni de la papelera.`
    });
    setTimeout(() => this.cancelBtnRef?.nativeElement?.focus(), 50);
  }

  openBatchDeleteModal(): void {
    const count = this.selectedIds().size;
    this.confirmModal.set({
      isOpen: true,
      type: 'batch',
      title: `¿Eliminar definitivamente ${count} elementos?`,
      description: `Esta acción borrará de forma permanente los ${count} elementos seleccionados. Esta acción no se puede deshacer.`
    });
    setTimeout(() => this.cancelBtnRef?.nativeElement?.focus(), 50);
  }

  openEmptyTrashModal(): void {
    const count = this.projectsList().length;
    this.confirmModal.set({
      isOpen: true,
      type: 'empty',
      title: '¿Vaciar la papelera completa?',
      description: `Esta acción eliminará definitivamente todos los ${count} elementos almacenados en la papelera. No se podrán recuperar jamás.`
    });
    setTimeout(() => this.cancelBtnRef?.nativeElement?.focus(), 50);
  }

  closeConfirmModal(): void {
    this.confirmModal.set({ isOpen: false, type: 'single', title: '', description: '' });
  }

  executeModalAction(): void {
    const modal = this.confirmModal();
    if (modal.type === 'single' && modal.targetProject) {
      this.stateService.deletePermanently(modal.targetProject.id);
      this.showToast(`"${modal.targetProject.nombre}" eliminado definitivamente.`);
    } else if (modal.type === 'batch') {
      const ids = Array.from(this.selectedIds());
      ids.forEach(id => this.stateService.deletePermanently(id));
      this.selectedIds.set(new Set());
      this.showToast(`${ids.length} elementos eliminados definitivamente.`);
    } else if (modal.type === 'empty') {
      this.stateService.emptyTrash();
      this.showToast('La papelera ha sido vaciada completamente.');
    }
    this.closeConfirmModal();
    this.refreshProjects();
  }

  private showToast(msg: string): void {
    this.toastMsg.set(msg);
    setTimeout(() => this.toastMsg.set(null), 4000);
  }

  @HostListener('window:keydown.escape')
  handleEscape(): void {
    if (this.confirmModal().isOpen) {
      this.closeConfirmModal();
    } else if (this.previewProject()) {
      this.previewProject.set(null);
    }
  }
}
