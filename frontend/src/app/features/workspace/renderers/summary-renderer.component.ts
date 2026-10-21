import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResumenEjecutivoItem, RagFuente } from '../../../core/models/adaptation.model';

/** Blocks merged into one paragraph, matching the backend summary composer. */
const ITEMS_PER_PARAGRAPH = 1;

/** Header line that introduces the reference list of the executive summary. */
const SOURCES_HEADER_PATTERN = /^(fuentes|sources|fontes)$/i;

/**
 * Renders the executive summary as one continuous text.
 *
 * The stored summary text is the canonical output: every paragraph already
 * carries the reference numbers of the sections it comes from, and the text
 * ends with a reference list. When only structured items are available (older
 * generations), the paragraphs are composed from them instead.
 */
@Component({
  selector: 'app-summary-renderer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="summary-container" *ngIf="paragraphs.length > 0 || noticeText">
      <!-- Document header -->
      <div class="tldr-banner glass-card" *ngIf="!noticeText">
        <div class="tldr-badge">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
          <span>SÍNTESIS RÁPIDA</span>
        </div>
        <h2>Resumen Ejecutivo</h2>
      </div>

      <!-- Notice shown when there is no summary to display -->
      <div class="summary-notice glass-card" *ngIf="noticeText">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#D97706" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <p>{{ noticeText }}</p>
      </div>

      <!-- Single continuous output: one text made of paragraphs -->
      <div class="summary-flow glass-card" *ngIf="paragraphs.length > 0">
        <p *ngFor="let paragraph of paragraphs">{{ paragraph }}</p>
      </div>

      <!-- Reference list: document title once, then one line per reference -->
      <div class="sources-block glass-card" *ngIf="sourceLines.length > 0">
        <div class="sources-header">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
          <span>{{ sourcesHeader }}</span>
        </div>
        <div class="sources-general" *ngIf="generalSource">{{ generalSource }}</div>
        <div class="source-line" *ngFor="let line of sourceLines">{{ line }}</div>
      </div>

      <!-- Verified source locations or count, kept as a single footer line -->
      <div class="sources-footer" *ngIf="verifiedPointsCount > 0 && !noticeText">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
        <span>{{ verifiedPointsCount }} {{ verifiedPointsCount === 1 ? 'punto verificado' : 'puntos verificados' }} contra el documento fuente</span>
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

    .summary-notice {
      display: flex;
      align-items: flex-start;
      gap: 0.75rem;
      padding: 1.25rem 1.5rem;
      border-radius: 16px;
      background: rgba(245, 158, 11, 0.1);
      border: 1px solid rgba(245, 158, 11, 0.3);
      color: var(--text-primary);
    }

    .summary-notice p {
      margin: 0;
      font-size: 0.95rem;
      line-height: 1.6;
    }

    .sources-block {
      margin-top: 1rem;
      padding: 1.1rem 1.4rem;
      border-radius: 14px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
    }

    .sources-header {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-size: 0.8rem;
      font-weight: 800;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: 0.65rem;
    }

    .sources-general {
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text-primary);
      margin-bottom: 0.4rem;
    }

    .source-line {
      font-size: 0.83rem;
      color: var(--text-secondary);
      line-height: 1.6;
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
  /** Stored `resumen_ejecutivo` text; canonical output when present. */
  @Input() text?: string;

  paragraphs: string[] = [];
  sourceLabels: string[] = [];
  /** Header of the reference list ("Fuentes", "Sources", ...). */
  sourcesHeader = 'Fuentes';
  /** Document title, printed once as the general source. */
  generalSource = '';
  /** One line per reference number. */
  sourceLines: string[] = [];
  /** Message shown instead of the summary when nothing could be generated. */
  noticeText = '';

  get verifiedPointsCount(): number {
    if (this.items && this.items.length > 0) {
      return this.items.filter(
        (it) => it.fuentes && it.fuentes.some((s) => s.verificado)
      ).length || this.items.length;
    }
    return this.paragraphs.length;
  }

  ngOnChanges(_changes: SimpleChanges): void {
    this.paragraphs = [];
    this.sourceLabels = [];
    this.sourcesHeader = 'Fuentes';
    this.generalSource = '';
    this.sourceLines = [];
    this.noticeText = '';

    const stored = (this.text || '').trim();

    if (stored) {
      const parsed = this.parseStoredText(stored);
      this.paragraphs = parsed.paragraphs;
      this.sourcesHeader = parsed.sourcesHeader;
      this.generalSource = parsed.generalSource;
      this.sourceLines = parsed.sourceLines;
    }

    if (this.paragraphs.length === 0) {
      // Older generations: compose the paragraphs from the structured items.
      this.paragraphs = this.composeParagraphs();
    }

    if (this.paragraphs.length === 0 && stored) {
      // Nothing was generated: the stored text is the explanation shown here.
      this.noticeText = stored;
    }

    this.sourceLabels = this.collectSourceLabels();
  }

  /**
   * Splits the stored summary into its paragraphs and its reference list.
   * The reference list starts with a header line and contains the document
   * title followed by one line per reference number.
   */
  private parseStoredText(text: string): {
    paragraphs: string[];
    sourcesHeader: string;
    generalSource: string;
    sourceLines: string[];
  } {
    const lines = text.split(/\r?\n/);
    const headerIndex = lines.findIndex((line) => SOURCES_HEADER_PATTERN.test(line.trim()));

    const bodyLines = headerIndex >= 0 ? lines.slice(0, headerIndex) : lines;
    const paragraphs = bodyLines
      .map((line) => line.trim())
      .filter((line) => line.length > 0);

    const sourcesHeader = headerIndex >= 0 ? lines[headerIndex].trim() : 'Fuentes';
    const referenceLines = headerIndex >= 0
      ? lines.slice(headerIndex + 1).map((line) => line.trim()).filter((line) => line.length > 0)
      : [];

    const generalSource = referenceLines.length > 0 && !referenceLines[0].startsWith('[')
      ? referenceLines[0]
      : '';
    const sourceLines = referenceLines.filter((line) => line.startsWith('['));

    return { paragraphs, sourcesHeader, generalSource, sourceLines };
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
