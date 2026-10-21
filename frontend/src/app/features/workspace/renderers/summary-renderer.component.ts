import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResumenEjecutivoItem, RagFuente } from '../../../core/models/adaptation.model';

/** Blocks merged into one paragraph, matching the backend summary composer. */
const ITEMS_PER_PARAGRAPH = 2;

@Component({
  selector: 'app-summary-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="summary-container" *ngIf="paragraphs.length > 0">
      <!-- Document header -->
      <div class="tldr-banner glass-card">
        <div class="tldr-badge">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          <span>SÍNTESIS RÁPIDA</span>
        </div>
        <h2>Resumen Ejecutivo</h2>
      </div>

      <!-- Single continuous output: one text made of paragraphs -->
      <div class="summary-flow glass-card">
        <p *ngFor="let paragraph of paragraphs">{{ paragraph }}</p>
      </div>

      <!-- Verified source locations, kept as a single footer line -->
      <div class="sources-footer" *ngIf="sourceLabels.length > 0">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        <span>Fuentes verificadas: {{ sourceLabels.join(' · ') }}</span>
      </div>
    </div>
  `,
  styles: [`
    .summary-container {
      width: 100%;
    }

    .tldr-banner {
      padding: 1.5rem 1.75rem;
      border-radius: 18px;
      background: linear-gradient(135deg, var(--bg-surface) 0%, rgba(16, 185, 129, 0.08) 100%);
      border: 1px solid rgba(16, 185, 129, 0.25);
      margin-bottom: 1.25rem;
    }

    .tldr-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.75rem;
      font-weight: 800;
      color: #10B981;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }

    .tldr-banner h2 {
      font-size: 1.4rem;
      font-weight: 800;
      margin: 0;
      color: var(--text-primary);
    }

    .summary-flow {
      padding: 2rem 2.25rem;
      border-radius: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
    }

    .summary-flow p {
      font-size: 1rem;
      line-height: 1.85;
      color: var(--text-primary);
      margin: 0 0 1.15rem 0;
      text-align: left;
    }

    .summary-flow p:last-child {
      margin-bottom: 0;
    }

    .sources-footer {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      margin-top: 0.85rem;
      font-size: 0.8rem;
      color: #0284C7;
      font-weight: 600;
    }
  `]
})
export class SummaryRendererComponent implements OnChanges {
  @Input({ required: true }) items: ResumenEjecutivoItem[] = [];
  /** Stored `resumen_ejecutivo` text; used when there are no structured items. */
  @Input() text?: string;

  paragraphs: string[] = [];
  sourceLabels: string[] = [];

  ngOnChanges(_changes: SimpleChanges): void {
    this.paragraphs = this.composeParagraphs();
    this.sourceLabels = this.collectSourceLabels();
  }

  /** One flowing text: blocks grouped into paragraphs, no cards or numbering. */
  private composeParagraphs(): string[] {
    const sentences = (this.items || [])
      .filter((item) => !!item && !!(item.punto_clave || item.impacto_negocio))
      .map((item) => this.buildSentence(item.punto_clave, item.impacto_negocio))
      .filter((sentence) => sentence.length > 0);

    if (sentences.length > 0) {
      const paragraphs: string[] = [];
      for (let i = 0; i < sentences.length; i += ITEMS_PER_PARAGRAPH) {
        paragraphs.push(sentences.slice(i, i + ITEMS_PER_PARAGRAPH).join(' '));
      }
      return paragraphs;
    }

    // Fallback for older generations stored as "1. takeaway: impact" lines.
    return this.legacyParagraphs(this.text || '');
  }

  private buildSentence(point?: string, impact?: string): string {
    const cleanPoint = (point || '').trim().replace(/\.$/, '');
    const cleanImpact = (impact || '').trim();
    const parts: string[] = [];
    if (cleanPoint) {
      parts.push(cleanPoint.charAt(0).toUpperCase() + cleanPoint.slice(1) + '.');
    }
    if (cleanImpact) {
      parts.push(/\.$/.test(cleanImpact) ? cleanImpact : cleanImpact + '.');
    }
    return parts.join(' ');
  }

  private legacyParagraphs(text: string): string[] {
    const lines = text
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
      .filter((line) => !/^(resumen ejecutivo|executive summary)/i.test(line))
      .map((line) => line.replace(/^\d+\.\s*/, ''));

    const paragraphs: string[] = [];
    for (let i = 0; i < lines.length; i += ITEMS_PER_PARAGRAPH) {
      paragraphs.push(lines.slice(i, i + ITEMS_PER_PARAGRAPH).join(' '));
    }
    return paragraphs;
  }

  private collectSourceLabels(): string[] {
    const labels: string[] = [];
    for (const item of this.items || []) {
      const source: RagFuente | undefined = item.fuentes && item.fuentes.length > 0 ? item.fuentes[0] : undefined;
      if (!source) {
        continue;
      }
      const label = source.breadcrumb || source.seccion || (source.pagina ? `Pág. ${source.pagina}` : '');
      if (label && !labels.includes(label)) {
        labels.push(label);
      }
    }
    return labels;
  }
}
