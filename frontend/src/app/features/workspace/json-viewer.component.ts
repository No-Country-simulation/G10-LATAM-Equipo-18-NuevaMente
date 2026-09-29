import { Component, Input, signal } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-json-viewer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="json-card glass-card">
      <div class="card-header">
        <h4>Visor de Payload JSON (Contrato Estricto API)</h4>
        <div class="actions">
          <button class="btn-action" (click)="copyJson()">
            {{ copied() ? '✓ Copiado' : '📋 Copiar JSON' }}
          </button>
          <button class="btn-action" (click)="downloadJson()">
            💾 Descargar .json
          </button>
        </div>
      </div>

      <div class="json-content-wrapper">
        <pre class="json-code"><code>{{ formattedJson }}</code></pre>
      </div>
    </div>
  `,
  styles: [`
    .json-card {
      padding: 1.5rem;
      border-radius: 16px;
      background: #0D1117;
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #C9D1D9;
    }

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .card-header h4 {
      font-size: 1rem;
      color: #F0F6FC;
    }

    .actions {
      display: flex;
      gap: 0.5rem;
    }

    .btn-action {
      padding: 0.4rem 0.75rem;
      border-radius: 6px;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #C9D1D9;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
    }

    .btn-action:hover {
      background: rgba(255, 255, 255, 0.15);
    }

    .json-content-wrapper {
      max-height: 400px;
      overflow-y: auto;
      background: #010409;
      padding: 1.25rem;
      border-radius: 10px;
    }

    .json-code {
      font-family: var(--font-code);
      font-size: 0.85rem;
      line-height: 1.5;
      color: #7EE787;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
    }
  `]
})
export class JsonViewerComponent {
  @Input() data: any;

  copied = signal<boolean>(false);

  get formattedJson(): string {
    return JSON.stringify(this.data, null, 2);
  }

  copyJson(): void {
    navigator.clipboard.writeText(this.formattedJson);
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 2000);
  }

  downloadJson(): void {
    const blob = new Blob([this.formattedJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `nuevamente-adaptacion-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }
}
