import { Component, Input, Output, EventEmitter, signal, computed, HostListener, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AdaptationResponse } from '../../core/models/adaptation.model';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-json-drawer',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div 
      class="drawer-overlay" 
      *ngIf="isOpen" 
      (click)="onBackdropClick($event)"
      role="dialog" 
      aria-modal="true" 
      aria-labelledby="json-drawer-title"
    >
      <div class="drawer-panel glass-card" (click)="$event.stopPropagation()">
        <!-- DRAWER HEADER -->
        <div class="drawer-header">
          <div class="header-title-box">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6366F1" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            <h3 id="json-drawer-title">Datos JSON y Estructura</h3>
          </div>
          <button 
            type="button" 
            class="btn-close" 
            (click)="closeDrawer.emit()" 
            aria-label="Cerrar panel de datos JSON"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>

        <!-- DRAWER NAVIGATION TABS (OCI Tab only shown if environment.showDeveloperTools is true) -->
        <div class="drawer-tabs" *ngIf="showDeveloperTools">
          <button 
            type="button" 
            class="tab-btn" 
            [class.active]="activeTab() === 'json'"
            (click)="activeTab.set('json')"
          >
            Payload JSON
          </button>
          <button 
            type="button" 
            class="tab-btn" 
            [class.active]="activeTab() === 'oci'"
            (click)="activeTab.set('oci')"
          >
            Almacenamiento (OCI)
          </button>
        </div>

        <!-- TAB CONTENT 1: JSON PAYLOAD -->
        <div class="drawer-content" *ngIf="activeTab() === 'json' || !showDeveloperTools">
          <div class="actions-bar">
            <span class="info-tag">Estructura estricta API</span>
            <div class="btn-group">
              <button type="button" class="btn-action" (click)="copyJson()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                {{ copied() ? '¡Copiado!' : 'Copiar' }}
              </button>
              <button type="button" class="btn-action" (click)="downloadJson()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                Descargar .json
              </button>
            </div>
          </div>

          <div class="json-code-box">
            <pre><code>{{ formattedJson() }}</code></pre>
          </div>
        </div>

        <!-- TAB CONTENT 2: OCI STORAGE (Developer Mode Only) -->
        <div class="drawer-content" *ngIf="activeTab() === 'oci' && showDeveloperTools">
          <div class="oci-info-card" *ngIf="data?.almacenamiento_oci">
            <div class="oci-badge">OCI ALWAYS FREE</div>
            <h4>Persistencia en Oracle Cloud Object Storage</h4>
            
            <div class="oci-details-grid">
              <div class="detail-row">
                <span class="detail-label">Estado de Carga:</span>
                <span class="status-pill">{{ data?.almacenamiento_oci?.status_upload }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">Bucket:</span>
                <code>{{ data?.almacenamiento_oci?.bucket }}</code>
              </div>
              <div class="detail-row">
                <span class="detail-label">ID del Objeto:</span>
                <div class="code-copy-wrapper">
                  <code>{{ data?.almacenamiento_oci?.objeto_id }}</code>
                  <button type="button" class="btn-mini-copy" (click)="copyObjectId()">
                    {{ copiedId() ? '✓' : 'Copiar' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="no-oci-fallback" *ngIf="!data?.almacenamiento_oci">
            <p>No se encontraron datos de almacenamiento OCI para esta respuesta.</p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .drawer-overlay {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(4px);
      z-index: 1000;
      display: flex;
      justify-content: flex-end;
      animation: fadeIn 0.2s ease-out;
    }

    .drawer-panel {
      width: 100%;
      max-width: 560px;
      height: 100%;
      background: #0D1117;
      color: #C9D1D9;
      display: flex;
      flex-direction: column;
      box-shadow: -8px 0 24px rgba(0, 0, 0, 0.3);
      animation: slideLeft 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
    }

    .drawer-header {
      padding: 1.25rem 1.5rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .header-title-box {
      display: flex;
      align-items: center;
      gap: 0.6rem;
    }

    .header-title-box h3 {
      font-size: 1.1rem;
      font-weight: 700;
      color: #F0F6FC;
      margin: 0;
    }

    .btn-close {
      background: transparent;
      border: none;
      color: #8B949E;
      cursor: pointer;
      padding: 0.35rem;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: color 0.2s;
    }

    .btn-close:hover {
      color: #F0F6FC;
      background: rgba(255, 255, 255, 0.08);
    }

    .drawer-tabs {
      display: flex;
      padding: 0.5rem 1.5rem;
      gap: 0.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      background: #161B22;
    }

    .tab-btn {
      padding: 0.4rem 0.85rem;
      border-radius: 6px;
      background: transparent;
      border: 1px solid transparent;
      color: #8B949E;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
    }

    .tab-btn.active {
      background: rgba(255, 255, 255, 0.08);
      color: #F0F6FC;
      border-color: rgba(255, 255, 255, 0.15);
    }

    .drawer-content {
      flex: 1;
      overflow-y: auto;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .actions-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .info-tag {
      font-size: 0.78rem;
      color: #8B949E;
      font-weight: 600;
    }

    .btn-group {
      display: flex;
      gap: 0.5rem;
    }

    .btn-action {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.4rem 0.75rem;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #C9D1D9;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
    }

    .btn-action:hover {
      background: rgba(255, 255, 255, 0.15);
    }

    .json-code-box {
      flex: 1;
      background: #010409;
      padding: 1.25rem;
      border-radius: 10px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      overflow-x: auto;
    }

    .json-code-box pre {
      margin: 0;
      font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace;
      font-size: 0.85rem;
      line-height: 1.5;
      color: #7EE787;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .oci-info-card {
      background: #161B22;
      border-radius: 12px;
      padding: 1.25rem;
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .oci-badge {
      font-size: 0.72rem;
      font-weight: 800;
      color: #EA580C;
      background: rgba(234, 88, 12, 0.15);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      display: inline-block;
      margin-bottom: 0.5rem;
    }

    .oci-info-card h4 {
      margin: 0 0 1rem 0;
      color: #F0F6FC;
      font-size: 1rem;
    }

    .oci-details-grid {
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
    }

    .detail-row {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .detail-label {
      font-size: 0.75rem;
      color: #8B949E;
      font-weight: 600;
    }

    .status-pill {
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 700;
      color: #34D399;
      background: rgba(52, 211, 153, 0.15);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      width: fit-content;
    }

    .code-copy-wrapper {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    code {
      font-family: Consolas, Monaco, monospace;
      font-size: 0.82rem;
      color: #A5D6FF;
    }

    .btn-mini-copy {
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.1);
      border: none;
      color: #C9D1D9;
      font-size: 0.75rem;
      cursor: pointer;
    }

    .no-oci-fallback {
      padding: 2rem;
      text-align: center;
      color: #8B949E;
      font-size: 0.9rem;
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes slideLeft {
      from { transform: translateX(100%); }
      to { transform: translateX(0); }
    }
  `]
})
export class JsonDrawerComponent {
  @Input() isOpen = false;
  @Input() data: AdaptationResponse | null = null;
  @Output() closeDrawer = new EventEmitter<void>();

  activeTab = signal<'json' | 'oci'>('json');
  copied = signal<boolean>(false);
  copiedId = signal<boolean>(false);

  showDeveloperTools = environment.showDeveloperTools;

  formattedJson = computed(() => {
    return this.data ? JSON.stringify(this.data, null, 2) : '{}';
  });

  @HostListener('document:keydown.escape')
  onEscapePress(): void {
    if (this.isOpen) {
      this.closeDrawer.emit();
    }
  }

  onBackdropClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) {
      this.closeDrawer.emit();
    }
  }

  copyJson(): void {
    navigator.clipboard.writeText(this.formattedJson());
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 2000);
  }

  downloadJson(): void {
    const blob = new Blob([this.formattedJson()], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nuevamente-adaptacion-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  copyObjectId(): void {
    const objId = this.data?.almacenamiento_oci?.objeto_id;
    if (objId) {
      navigator.clipboard.writeText(objId);
      this.copiedId.set(true);
      setTimeout(() => this.copiedId.set(false), 2000);
    }
  }
}
