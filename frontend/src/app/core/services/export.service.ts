import { Injectable, inject } from '@angular/core';
import { AdaptationResponse } from '../models/adaptation.model';
import { NUEVAMENTE_API } from '../api/nuevamente-api';

@Injectable({
  providedIn: 'root'
})
export class ExportService {
  private api = inject(NUEVAMENTE_API, { optional: true });

  exportMarkdown(response: AdaptationResponse): void {
    const title = response.contenido_adaptado.titulo || 'Adaptación Educativa NuevaMente';
    let md = `# ${title}\n\n`;
    md += `**Perfil Destinatario:** ${response.metadatos.perfil_aplicado}\n`;
    md += `**Formato Pedagógico:** ${response.metadatos.formato_generado}\n`;
    md += `**Tiempo Estimado de Estudio:** ${response.metadatos.tiempo_estimado_estudio_minutos} minutos\n`;
    md += `**Anclaje RAG Score:** ${(response.evaluacion_calidad.anclaje_fuente_score * 100).toFixed(0)}%\n\n`;
    md += `---\n\n`;
    md += `## Introducción\n${response.contenido_adaptado.introduccion_contextualizada}\n\n`;

    const items = response.contenido_adaptado.items || [];
    const storedSummary = response.contenido_adaptado.resumen_ejecutivo;
    const renderAsParagraphs = this.isSummaryItems(items, storedSummary);

    if (renderAsParagraphs) {
      // Executive summary downloads as one continuous text of paragraphs.
      md += `## Resumen Ejecutivo\n\n`;
      md += this.composeSummaryParagraphs(items, storedSummary).join('\n\n') + '\n\n';
    } else {
      md += `## Contenido Didáctico\n\n`;
    }

    items.forEach((item: any, idx: number) => {
      if (renderAsParagraphs) {
        return; // Already rendered above as one continuous text.
      }
      if ('frente' in item) {
        md += `### Flashcard ${idx + 1}\n- **Q:** ${item.frente}\n- **A:** ${item.dorso}\n`;
        if (item.pista_didactica) md += `- *Pista:* ${item.pista_didactica}\n`;
      } else if ('pregunta' in item) {
        md += `### Pregunta ${idx + 1}: ${item.pregunta}\n`;
        (item.opciones || []).forEach((opt: string) => md += `  - [ ] ${opt}\n`);
        md += `**Respuesta Correcta:** ${item.respuesta_correcta}\n`;
        md += `*Justificación:* ${item.justificacion || item.justificacion_didactica}\n`;
      } else if ('paso' in item) {
        md += `### Paso ${item.paso}: ${item.titulo}\n${item.instruccion}\n`;
        if (item.ejemplo) md += `\`\`\`\n${item.ejemplo}\n\`\`\`\n`;
        if (item.advertencia) md += `> ⚠️ **Advertencia:** ${item.advertencia}\n`;
      } else if ('punto_clave' in item) {
        md += `### Punto Clave ${idx + 1}: ${item.punto_clave}\n`;
        md += `**Impacto de Negocio:** ${item.impacto_negocio}\n`;
      } else if ('escena' in item) {
        md += `### Escena ${item.escena} (${item.duracion_seg}s)\n`;
        md += `- **Narración:** ${item.narracion}\n`;
        md += `- **Apoyo Visual:** ${item.apoyo_visual}\n`;
      }
      md += `\n`;
    });

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    this.triggerDownload(blob, `${title.toLowerCase().replace(/[^a-z0-9]/g, '-')}.md`);
  }

  exportAnkiCsv(response: AdaptationResponse): void {
    const items = response.contenido_adaptado.items || [];
    const flashcards = items.filter((i: any) => 'frente' in i);

    if (flashcards.length === 0) {
      alert('Solo se pueden exportar a Anki los contenidos en formato Flashcards.');
      return;
    }

    let csv = '#separator:Comma\n#html:false\n';
    flashcards.forEach((f: any) => {
      const q = `"${f.frente.replace(/"/g, '""')}"`;
      const a = `"${f.dorso.replace(/"/g, '""')}"`;
      csv += `${q},${a}\n`;
    });

    // Include UTF-8 BOM (\uFEFF) so Excel and text editors properly render accents and special characters
    const bom = '\uFEFF';
    const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' });
    this.triggerDownload(blob, `flashcards-${Date.now()}.csv`);
  }

  viewPdfPreview(response: AdaptationResponse): void {
    this.openPrintWindowFallback(response);
  }

  exportPdfDirect(response: AdaptationResponse): void {
    const title = response?.contenido_adaptado?.titulo || 'Adaptación Educativa NuevaMente';
    const filename = `${title.toLowerCase().replace(/[^a-z0-9]/g, '-') || 'material-educativo'}.pdf`;

    if (this.api) {
      this.api.exportPdf(response).subscribe({
        next: (blob: Blob) => {
          this.triggerDownload(blob, filename);
        },
        error: (err: any) => {
          console.warn('[ExportService] Falló la descarga de PDF del servidor, recurriendo a vista de impresión:', err);
          this.openPrintWindowFallback(response);
        }
      });
      return;
    }

    this.openPrintWindowFallback(response);
  }

  exportPdfDidactico(response: AdaptationResponse): void {
    // Keep backward-compatible signature defaulting to direct PDF or fallback
    this.exportPdfDirect(response);
  }

  openPrintWindowFallback(response: AdaptationResponse): void {
    const printWindow = window.open('', '_blank', 'width=950,height=900,scrollbars=yes');
    if (!printWindow) {
      alert('Por favor permite ventanas emergentes (popups) en tu navegador para ver la vista previa del PDF.');
      return;
    }

    const title = response.contenido_adaptado.titulo || 'Adaptación Educativa NuevaMente';
    const items = response.contenido_adaptado.items || [];
    const scoreVal = response.evaluacion_calidad.anclaje_fuente_score;
    const scorePct = scoreVal !== undefined && scoreVal !== null ? `${Math.round(scoreVal * 100)}%` : 'Sin verificar';
    const dateStr = new Date().toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });

    let itemsHtml = '';

    const storedSummary = response.contenido_adaptado.resumen_ejecutivo;
    const renderAsParagraphs = this.isSummaryItems(items, storedSummary);
    if (renderAsParagraphs) {
      // Single flowing document instead of one card per block.
      const summaryHtml = this.composeSummaryParagraphs(items, storedSummary)
        .map((paragraph) => `<p>${paragraph}</p>`)
        .join('');
      itemsHtml = `<div class="summary-flow">${summaryHtml}</div>`;
    }

    items.forEach((item: any, idx: number) => {
      if (renderAsParagraphs) {
        return; // Summary already rendered as continuous paragraphs.
      }
      if ('paso' in item || 'instruccion' in item) {
        itemsHtml += `
          <div class="pdf-card">
            <div class="card-step-badge">PASO ${item.paso || idx + 1}</div>
            <h3 class="card-step-title">${item.titulo || ''}</h3>
            <p class="card-instruccion">${item.instruccion || ''}</p>
            ${item.ejemplo ? `
              <div class="pdf-code-block">
                <div class="code-title">CÓDIGO / COMANDO CLI:</div>
                <pre><code>${this.cleanCodeSnippet(item.ejemplo)}</code></pre>
              </div>
            ` : ''}
            ${item.advertencia ? `
              <div class="pdf-warning-box">
                <strong>⚠️ Advertencia importante:</strong>
                <p>${item.advertencia}</p>
              </div>
            ` : ''}
          </div>
        `;
      } else if ('frente' in item) {
        itemsHtml += `
          <div class="pdf-card">
            <div class="card-step-badge">TARJETA #${idx + 1}</div>
            <h3 class="card-step-title">Pregunta / Concepto: ${item.frente}</h3>
            <p class="card-instruccion"><strong>Respuesta / Explicación:</strong> ${item.dorso}</p>
            ${item.pista_didactica ? `<p style="font-style:italic; color:#64748b; margin-top:6px;">💡 Pista: ${item.pista_didactica}</p>` : ''}
          </div>
        `;
      } else if ('pregunta' in item) {
        itemsHtml += `
          <div class="pdf-card">
            <div class="card-step-badge">PREGUNTA #${idx + 1}</div>
            <h3 class="card-step-title">${item.pregunta}</h3>
            <ul class="quiz-options-list">
              ${(item.opciones || []).map((opt: string) => `
                <li class="${opt === item.respuesta_correcta ? 'is-correct-opt' : ''}">
                  ${opt === item.respuesta_correcta ? '✓ <strong>' + opt + ' (Respuesta Correcta)</strong>' : '⚪ ' + opt}
                </li>
              `).join('')}
            </ul>
            <div class="pdf-justification">
              <strong>💡 Justificación Pedagógica:</strong> ${item.justificacion || item.justificacion_didactica || ''}
            </div>
          </div>
        `;
      } else if ('punto_clave' in item) {
        itemsHtml += `
          <div class="pdf-card">
            <div class="card-step-badge">PUNTO CLAVE 0${idx + 1}</div>
            <h3 class="card-step-title">${item.punto_clave}</h3>
            <div class="impact-box">
              <strong>📊 IMPACTO DE NEGOCIO:</strong>
              <p>${item.impacto_negocio}</p>
            </div>
          </div>
        `;
      } else if ('escena' in item) {
        itemsHtml += `
          <div class="pdf-card">
            <div class="card-step-badge">ESCENA ${item.escena} (${item.duracion_seg}s)</div>
            <p style="margin-bottom:8px;"><strong>🎙️ Narración:</strong> ${item.narracion}</p>
            <p><strong>🎨 Apoyo Visual:</strong> ${item.apoyo_visual}</p>
          </div>
        `;
      }
    });

    const htmlContent = `
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta charset="utf-8">
        <title>${title} - PDF Didáctico NuevaMente</title>
        <style>
          @page { size: A4; margin: 1.5cm; }
          body { font-family: 'Helvetica Neue', Arial, sans-serif; color: #0f172a; line-height: 1.5; margin: 0; padding: 0; background: #f8fafc; }
          
          /* Top Action Bar (hidden when printing) */
          .no-print-bar {
            position: sticky; top: 0; z-index: 100;
            background: #0f172a; color: #ffffff;
            padding: 12px 24px; display: flex; justify-content: space-between; align-items: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          }
          .no-print-bar span { font-size: 14px; font-weight: 600; color: #e2e8f0; }
          .action-btns { display: flex; gap: 10px; }
          .btn-print { background: #4f46e5; color: #ffffff; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 13px; }
          .btn-print:hover { background: #4338ca; }
          .btn-close { background: rgba(255,255,255,0.15); color: #ffffff; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 13px; }
          .btn-close:hover { background: rgba(255,255,255,0.25); }

          @media print {
            .no-print-bar { display: none !important; }
            body { background: #ffffff; }
          }

          .document-wrapper { max-width: 800px; margin: 20px auto; padding: 30px; background: #ffffff; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
          .pdf-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #4f46e5; padding-bottom: 12px; margin-bottom: 24px; }
          .brand-title { font-size: 20px; font-weight: 800; color: #4f46e5; }
          .oracle-badge { font-size: 11px; font-weight: 700; color: #ea580c; background: #fff7ed; padding: 3px 8px; border-radius: 4px; border: 1px solid #ffedd5; }
          .meta-chips { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
          .chip { font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px; background: #f1f5f9; color: #475569; }
          .chip-profile { background: #eff6ff; color: #2563eb; }
          .chip-format { background: #f3e8ff; color: #7c3aed; }
          .doc-title { font-size: 24px; font-weight: 800; color: #0f172a; margin: 0 0 12px 0; }
          .intro-text { font-size: 14px; color: #475569; margin-bottom: 24px; line-height: 1.6; }
          .summary-flow { font-size: 14px; color: #334155; line-height: 1.75; }
          .summary-flow p { margin: 0 0 14px 0; }
          .pdf-card { border: 1px solid #cbd5e1; border-radius: 10px; padding: 18px; margin-bottom: 20px; page-break-inside: avoid; background: #ffffff; }
          .card-step-badge { font-size: 11px; font-weight: 800; color: #4f46e5; letter-spacing: 0.05em; margin-bottom: 6px; }
          .card-step-title { font-size: 16px; font-weight: 700; margin: 0 0 10px 0; color: #0f172a; }
          .card-instruccion { font-size: 13px; color: #334155; margin-bottom: 12px; }
          .pdf-code-block { background: #0d1117; color: #58a6ff; padding: 12px 16px; border-radius: 8px; font-family: 'Courier New', monospace; font-size: 12px; margin-bottom: 12px; }
          .code-title { font-size: 10px; font-weight: 700; color: #8b949e; margin-bottom: 4px; }
          .pdf-code-block pre { margin: 0; white-space: pre-wrap; word-break: break-all; }
          .pdf-warning-box { background: #fffbebfb; border: 1px solid #fde68a; border-radius: 8px; padding: 10px 14px; color: #d97706; font-size: 12px; }
          .quiz-options-list { list-style: none; padding: 0; margin: 10px 0; }
          .quiz-options-list li { padding: 6px 10px; margin-bottom: 4px; border-radius: 6px; font-size: 12px; background: #f8fafc; }
          .is-correct-opt { background: #ecfdf5 !important; color: #047857 !important; border: 1px solid #a7f3d0; }
          .pdf-justification { background: #f3e8ff; border: 1px solid #ddd6fe; border-radius: 8px; padding: 10px 14px; font-size: 12px; color: #6b21a8; }
          .quality-panel-pdf { border: 1px solid #10b981; background: #f0fdf4; border-radius: 10px; padding: 16px; margin-top: 30px; margin-bottom: 20px; page-break-inside: avoid; }
          .quality-title { font-size: 14px; font-weight: 800; color: #047857; margin-bottom: 8px; }
          .oci-footer-card { border: 1px solid #e2e8f0; background: #f8fafc; border-radius: 10px; padding: 14px; font-size: 11px; margin-bottom: 30px; }
          .pdf-footer { border-top: 1px solid #e2e8f0; padding-top: 12px; font-size: 10px; color: #94a3b8; display: flex; justify-content: space-between; }
        </style>
      </head>
      <body>
        <div class="no-print-bar">
          <span>📄 Vista Previa PDF — NuevaMente Adaptación Educativa</span>
          <div class="action-btns">
            <button onclick="window.print()" class="btn-print">🖨️ Imprimir / Guardar PDF</button>
            <button onclick="window.close()" class="btn-close">❌ Cerrar</button>
          </div>
        </div>

        <div class="document-wrapper">
          <div class="pdf-header">
            <div class="brand-title">🎓 NuevaMente — Adaptación Educativa</div>
            <div class="oracle-badge">Powered by Oracle Cloud Infrastructure</div>
          </div>

          <div class="meta-chips">
            <span class="chip chip-profile">👤 Perfil: ${response.metadatos.perfil_aplicado}</span>
            <span class="chip chip-format">🎯 Formato: ${response.metadatos.formato_generado}</span>
            <span class="chip">⏱️ Tiempo Estudio: ${response.metadatos.tiempo_estimado_estudio_minutos} min</span>
            <span class="chip">🛡️ Fidelidad RAG: ${scorePct}%</span>
          </div>

          <h1 class="doc-title">${title}</h1>
          <p class="intro-text">${response.contenido_adaptado.introduccion_contextualizada}</p>

          <div class="items-wrapper">
            ${itemsHtml}
          </div>

          <div class="quality-panel-pdf">
            <div class="quality-title">🛡️ Panel de Calidad y Anclaje RAG Verificado (Score: ${scorePct})</div>
            <p style="font-size:12px; color:#065f46; margin:0;">
              <strong>Claridad Pedagógica:</strong> ${response.evaluacion_calidad.claridad_pedagogica} | 
              <strong>Observaciones:</strong> ${response.evaluacion_calidad.observaciones}
            </p>
          </div>

          <div class="oci-footer-card">
            <strong>☁️ Persistencia OCI Object Storage:</strong> Bucket: <code>${response.almacenamiento_oci?.bucket || 'nuevamente-contenidos-educativos'}</code> | Objeto ID: <code>${response.almacenamiento_oci?.objeto_id || 'obj_' + Date.now()}</code>
          </div>

          <div class="pdf-footer">
            <span>Generado por NuevaMente RAG • Oracle Next Education × Alura (Grupo 10)</span>
            <span>${dateStr}</span>
          </div>
        </div>
      </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
  }

  /**
   * True when the response must render as one continuous summary text:
   * either structured `punto_clave` blocks or a legacy stored summary string.
   */
  private isSummaryItems(items: any[], storedText?: string): boolean {
    if (items.length > 0) {
      return items.every((item: any) => !!item && 'punto_clave' in item);
    }
    return !!storedText;
  }

  /** Summary blocks (or legacy stored text) joined into flowing paragraphs. */
  private composeSummaryParagraphs(items: any[], storedText?: string): string[] {
    if (items.length > 0) {
      const sentences = items
        .filter((item: any) => item && (item.punto_clave || item.impacto_negocio))
        .map((item: any) => {
          const point = String(item.punto_clave || '').trim().replace(/\.$/, '');
          const impact = String(item.impacto_negocio || '').trim();
          const parts: string[] = [];
          if (point) parts.push(point.charAt(0).toUpperCase() + point.slice(1) + '.');
          if (impact) parts.push(/\.$/.test(impact) ? impact : impact + '.');
          return parts.join(' ');
        })
        .filter((sentence: string) => sentence.length > 0);
      return this.groupIntoParagraphs(sentences);
    }

    const lines = String(storedText || '')
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0 && !/^(resumen ejecutivo|executive summary)/i.test(line))
      .map((line) => line.replace(/^\d+\.\s*/, ''));
    return this.groupIntoParagraphs(lines);
  }

  /** Groups consecutive sentences into paragraphs of two (mirrors the backend). */
  private groupIntoParagraphs(sentences: string[]): string[] {
    const paragraphs: string[] = [];
    for (let i = 0; i < sentences.length; i += 2) {
      paragraphs.push(sentences.slice(i, i + 2).join(' '));
    }
    return paragraphs;
  }

  triggerPrint(): void {
    window.print();
  }

  private cleanCodeSnippet(raw: string): string {
    return raw.replace(/^```[a-z]*\n?/i, '').replace(/```$/i, '').trim();
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }
}
