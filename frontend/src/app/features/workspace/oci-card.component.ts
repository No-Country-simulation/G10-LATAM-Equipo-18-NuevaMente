import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AlmacenamientoOCI } from '../../core/models/adaptation.model';

@Component({
  selector: 'app-oci-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="oci-card glass-card" *ngIf="oci">
      <div class="card-header">
        <div class="cloud-icon-title">
          <span class="oracle-badge">OCI ALWAYS FREE</span>
          <h4>Persistencia en Oracle Cloud Object Storage</h4>
        </div>
        <span class="status-badge" [class.completado]="oci.status_upload === 'completado'">
          {{ oci.status_upload | uppercase }}
        </span>
      </div>

      <div class="card-grid">
        <div class="field-item">
          <span class="field-label">BUCKET OCI:</span>
          <span class="field-value"><code>{{ oci.bucket }}</code></span>
        </div>

        <div class="field-item">
          <span class="field-label">OBJETO ID (JSON):</span>
          <div class="copy-row">
            <span class="field-value"><code>{{ oci.objeto_id }}</code></span>
            <button class="btn-copy-id" (click)="copyObjectId()">
              {{ copied() ? '✓ Copiado' : 'Copiar ID' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .oci-card {
      padding: 1.5rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.25rem;
    }

    .oracle-badge {
      font-size: 0.72rem;
      font-weight: 800;
      color: #EA580C;
      background: rgba(234, 88, 12, 0.1);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
      letter-spacing: 0.05em;
      display: inline-block;
      margin-bottom: 0.25rem;
    }

    .cloud-icon-title h4 {
      font-size: 1.1rem;
    }

    .status-badge {
      font-size: 0.78rem;
      font-weight: 800;
      padding: 0.3rem 0.75rem;
      border-radius: 20px;
      background: var(--slate-200);
      color: var(--text-secondary);
    }

    .status-badge.completado {
      background: rgba(16, 185, 129, 0.15);
      color: #059669;
    }

    .card-grid {
      display: grid;
      grid-template-columns: 1fr 1.5fr;
      gap: 1.25rem;
      background: var(--bg-app);
      padding: 1rem;
      border-radius: 12px;
    }

    .field-item {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }

    .field-label {
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--text-muted);
    }

    .field-value code {
      font-family: var(--font-code);
      font-size: 0.85rem;
      color: var(--text-primary);
    }

    .copy-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .btn-copy-id {
      padding: 0.2rem 0.6rem;
      border-radius: 6px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      color: var(--text-primary);
    }
  `]
})
export class OciCardComponent {
  @Input() oci?: AlmacenamientoOCI;
  copied = signal<boolean>(false);

  copyObjectId(): void {
    if (this.oci?.objeto_id) {
      navigator.clipboard.writeText(this.oci.objeto_id);
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    }
  }
}
