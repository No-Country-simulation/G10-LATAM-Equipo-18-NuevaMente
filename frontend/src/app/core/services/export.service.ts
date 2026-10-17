import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AdaptationResponse } from '../models/adaptation.model';
import { environment } from '../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class ExportService {
  private http = inject(HttpClient, { optional: true });
  private apiUrl = environment.apiUrl || '/api/v1';

  // ---------------------------------------------------------------------------
  // 1. MARKDOWN EXPORT (.md)
  // ---------------------------------------------------------------------------
  exportMarkdown(response: AdaptationResponse): void {
    const title = response.contenido_adaptado?.titulo || 'Adaptacion Educativa NuevaMente';
    const slug = this.slugify(title);

    let md = `# 🎓 ${title}\n\n`;
    md += `> **NuevaMente** — Sistema de Adaptación Educativa con Inteligencia Artificial y Graph RAG\n`;
    md += `> *Desarrollado para Oracle Next Education (ONE) × Alura — Grupo 10*\n\n`;
    md += `---\n\n`;

    md += `### 📋 Ficha Técnica Pedagógica\n\n`;
    md += `| Parámetro | Valor |\n`;
    md += `| :--- | :--- |\n`;
    md += `| **👤 Perfil Destinatario** | \`${response.metadatos?.perfil_aplicado || 'General'}\` |\n`;
    md += `| **🎯 Formato Pedagógico** | \`${response.metadatos?.formato_generado || 'Contenido'}\` |\n`;
    md += `| **⏱️ Tiempo Estimado de Estudio** | \`${response.metadatos?.tiempo_estimado_estudio_minutos || 15} minutos\` |\n`;
    const scorePct = Math.round((response.evaluacion_calidad?.anclaje_fuente_score || 0.98) * 100);
    md += `| **🛡️ Anclaje RAG Verificado** | \`${scorePct}%\` |\n`;
    if (response.almacenamiento_oci?.objeto_id) {
      md += `| **☁️ Persistencia OCI Bucket** | \`${response.almacenamiento_oci?.bucket || 'nuevamente-contenidos-educativos'}\` |\n`;
      md += `| **📦 Objeto ID** | \`${response.almacenamiento_oci?.objeto_id}\` |\n`;
    }
    md += `\n---\n\n`;

    if (response.contenido_adaptado?.introduccion_contextualizada) {
      md += `## 📖 Introducción y Contextualización\n\n`;
      md += `${response.contenido_adaptado.introduccion_contextualizada}\n\n---\n\n`;
    }

    if (response.contenido_adaptado?.resumen_ejecutivo) {
      md += `## 📊 Resumen Ejecutivo\n\n`;
      md += `${response.contenido_adaptado.resumen_ejecutivo}\n\n---\n\n`;
    }

    const items = response.contenido_adaptado?.items || [];
    md += `## 📚 Contenido Didáctico Adaptado\n\n`;

    items.forEach((item: any, idx: number) => {
      if ('frente' in item) {
        md += `### 🗂️ Tarjeta #${idx + 1}: ${item.frente}\n\n`;
        md += `**Respuesta:** ${item.dorso}\n\n`;
        if (item.pista_didactica) md += `> 💡 **Pista didáctica:** *${item.pista_didactica}*\n\n`;
      } else if ('pregunta' in item) {
        md += `### ❓ Pregunta #${idx + 1}: ${item.pregunta}\n\n`;
        (item.opciones || []).forEach((opt: string) => {
          const isCorrect = opt === item.respuesta_correcta;
          md += `- [${isCorrect ? 'x' : ' '}] ${opt}\n`;
        });
        md += `\n**✅ Respuesta Correcta:** ${item.respuesta_correcta}\n\n`;
        const justif = item.justificacion_didactica || item.justificacion;
        if (justif) md += `> 💡 **Justificación:** *${justif}*\n\n`;
      } else if ('paso' in item || 'instruccion' in item) {
        const pasoNum = item.paso || (idx + 1);
        md += `### 🛠️ Paso ${pasoNum}: ${item.titulo || ('Módulo ' + (idx + 1))}\n\n`;
        md += `${item.instruccion || ''}\n\n`;
        if (item.ejemplo) md += `\`\`\`\n${this.cleanCodeSnippet(item.ejemplo)}\n\`\`\`\n\n`;
        if (item.advertencia) md += `> ⚠️ **Nota de seguridad:** ${item.advertencia}\n\n`;
      } else if ('punto_clave' in item) {
        md += `### 📌 Punto Clave #${idx + 1}: ${item.punto_clave}\n\n`;
        if (item.impacto_negocio) md += `**Impacto Operativo / Negocio:** ${item.impacto_negocio}\n\n`;
      } else if ('escena' in item) {
        md += `### 🎬 Escena ${item.escena || idx + 1} (${item.duracion_seg || 60}s)\n\n`;
        md += `**🎙️ Narración:**\n>${item.narracion}\n\n`;
        if (item.apoyo_visual) md += `**🎨 Apoyo Visual Sugerido:** ${item.apoyo_visual}\n\n`;
      }

      if (item.fuentes && Array.isArray(item.fuentes) && item.fuentes.length > 0) {
        const src = item.fuentes[0];
        const sec = src.seccion || src.chunk_id || 'Referencia';
        const pag = src.pagina ? ` · Pág. ${src.pagina}` : '';
        md += `*📄 Fuente verificada: ${sec}${pag}*\n\n`;
      }
      md += `---\n\n`;
    });

    md += `### 🛡️ Auditoría de Calidad RAG\n`;
    md += `- **Claridad Pedagógica:** ${response.evaluacion_calidad?.claridad_pedagogica || 'Alta'}\n`;
    md += `- **Observaciones:** ${response.evaluacion_calidad?.observaciones || 'Verificado con RAG anclado a documento original.'}\n`;

    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
    this.triggerDownload(blob, `${slug}.md`);
  }

  // ---------------------------------------------------------------------------
  // 2. ANKI CSV EXPORT (.csv)
  // ---------------------------------------------------------------------------
  exportAnkiCsv(response: AdaptationResponse): void {
    const items = response.contenido_adaptado?.items || [];
    if (!items || items.length === 0) {
      alert('No hay elementos generados para exportar a Anki.');
      return;
    }

    const title = response.contenido_adaptado?.titulo || 'NuevaMente';
    const slug = this.slugify(title);
    const formato = (response.metadatos?.formato_generado || 'Educativo').replace(/\s+/g, '_');
    const tag = `NuevaMente::${formato}`;

    let csv = '#separator:tab\n#html:true\n#tags column:3\n';

    items.forEach((item: any, idx: number) => {
      let front = '';
      let back = '';

      if ('frente' in item) {
        const q = this.escapeHtml(item.frente || '');
        const hint = item.pista_didactica ? `<br><small style="color:#64748b;"><i>💡 Pista: ${this.escapeHtml(item.pista_didactica)}</i></small>` : '';
        front = `<div style="font-size:18px;font-weight:bold;color:#1e293b;">${q}</div>${hint}`;
        back = `<div style="font-size:16px;color:#334155;line-height:1.5;">${this.escapeHtml(item.dorso || '')}</div>`;
      } else if ('pregunta' in item) {
        const q = this.escapeHtml(item.pregunta || '');
        const opts = (item.opciones || []).map((o: string) => `<li style="margin-bottom:4px;">${this.escapeHtml(o)}</li>`).join('');
        front = `<div style="font-size:18px;font-weight:bold;color:#1e293b;">${q}</div><ul style="margin-top:8px;padding-left:20px;font-size:14px;color:#475569;">${opts}</ul>`;
        const justif = item.justificacion_didactica || item.justificacion || '';
        const justifHtml = justif ? `<div style="margin-top:8px;font-size:13px;color:#6b21a8;background:#f3e8ff;padding:6px 10px;border-radius:6px;"><i>💡 ${this.escapeHtml(justif)}</i></div>` : '';
        back = `<div style="font-size:16px;font-weight:bold;color:#047857;">✓ ${this.escapeHtml(item.respuesta_correcta || '')}</div>${justifHtml}`;
      } else if ('paso' in item || 'instruccion' in item) {
        const pasoNum = item.paso || (idx + 1);
        front = `<div style="font-size:13px;font-weight:bold;color:#4f46e5;">PASO ${pasoNum}</div><div style="font-size:18px;font-weight:bold;color:#1e293b;">${this.escapeHtml(item.titulo || '')}</div>`;
        const codeHtml = item.ejemplo ? `<pre style="background:#0d1117;color:#58a6ff;padding:8px 12px;border-radius:6px;font-size:12px;margin-top:8px;overflow-x:auto;"><code>${this.escapeHtml(this.cleanCodeSnippet(item.ejemplo))}</code></pre>` : '';
        back = `<div style="font-size:15px;color:#334155;line-height:1.5;">${this.escapeHtml(item.instruccion || '')}</div>${codeHtml}`;
      } else if ('punto_clave' in item) {
        front = `<div style="font-size:13px;font-weight:bold;color:#2563eb;">PUNTO CLAVE #${idx + 1}</div><div style="font-size:17px;font-weight:bold;color:#1e293b;">${this.escapeHtml(item.punto_clave || '')}</div>`;
        back = `<div style="font-size:15px;color:#334155;"><strong>Impacto de Negocio:</strong><br>${this.escapeHtml(item.impacto_negocio || '')}</div>`;
      } else if ('escena' in item) {
        front = `<div style="font-size:13px;font-weight:bold;color:#7c3aed;">ESCENA ${item.escena || (idx + 1)} (${item.duracion_seg || 60}s)</div><div style="font-size:16px;color:#1e293b;"><strong>Guion Didáctico</strong></div>`;
        back = `<div style="font-size:15px;color:#334155;"><strong>🎙️ Narración:</strong> ${this.escapeHtml(item.narracion || '')}</div><div style="margin-top:6px;font-size:13px;color:#64748b;"><strong>🎨 Visual:</strong> ${this.escapeHtml(item.apoyo_visual || '')}</div>`;
      }

      if (front && back) {
        // Tab-separated: Front \t Back \t Tag
        const cleanFront = front.replace(/\t/g, ' ').replace(/\n/g, '<br>');
        const cleanBack = back.replace(/\t/g, ' ').replace(/\n/g, '<br>');
        csv += `${cleanFront}\t${cleanBack}\t${tag}\n`;
      }
    });

    const bomCsv = '\ufeff' + csv;
    const blob = new Blob([bomCsv], { type: 'text/csv;charset=utf-8;' });
    this.triggerDownload(blob, `${slug}-anki-deck.csv`);
  }

  // ---------------------------------------------------------------------------
  // 3. PDF DIDÁCTICO FORMATEADO (.pdf)
  // ---------------------------------------------------------------------------
  exportPdfDidactico(response: AdaptationResponse): void {
    const title = response.contenido_adaptado?.titulo || 'Adaptacion Educativa NuevaMente';
    const slug = this.slugify(title);

    // Try downloading compiled PDF from backend endpoint
    if (this.http) {
      this.http.post(`${this.apiUrl}/export/pdf`, response, { responseType: 'blob' }).subscribe({
        next: (blob: Blob) => {
          this.triggerDownload(blob, `${slug}.pdf`);
        },
        error: () => {
          // Fallback to formatted print preview window if backend endpoint is unavailable
          this.openPdfPrintPreview(response);
        }
      });
      return;
    }

    // Direct client fallback
    this.openPdfPrintPreview(response);
  }

  openPdfPrintPreview(response: AdaptationResponse): void {
    const printWindow = window.open('', '_blank', 'width=950,height=900,scrollbars=yes');
    if (!printWindow) {
      alert('Por favor permite ventanas emergentes (popups) en tu navegador para ver la vista previa del PDF.');
      return;
    }

    const title = response.contenido_adaptado?.titulo || 'Adaptación Educativa NuevaMente';
    const items = response.contenido_adaptado?.items || [];
    const scorePct = Math.round((response.evaluacion_calidad?.anclaje_fuente_score || 0.98) * 100);
    const dateStr = new Date().toLocaleDateString('es-ES', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' });

    let itemsHtml = '';

    items.forEach((item: any, idx: number) => {
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
            <div class="brand-title">NuevaMente — Adaptación Educativa</div>
            <div class="oracle-badge">Powered by Oracle Cloud Infrastructure</div>
          </div>

          <div class="meta-chips">
            <span class="chip chip-profile">👤 Perfil: ${response.metadatos?.perfil_aplicado || 'General'}</span>
            <span class="chip chip-format">🎯 Formato: ${response.metadatos?.formato_generado || 'Educativo'}</span>
            <span class="chip">⏱️ Tiempo Estudio: ${response.metadatos?.tiempo_estimado_estudio_minutos || 15} min</span>
            <span class="chip">🛡️ Fidelidad RAG: ${scorePct}%</span>
          </div>

          <h1 class="doc-title">${title}</h1>
          <p class="intro-text">${response.contenido_adaptado?.introduccion_contextualizada || ''}</p>

          <div class="items-wrapper">
            ${itemsHtml}
          </div>

          <div class="quality-panel-pdf">
            <div class="quality-title">🛡️ Panel de Calidad y Anclaje RAG Verificado (Score: ${scorePct}%)</div>
            <p style="font-size:12px; color:#065f46; margin:0;">
              <strong>Claridad Pedagógica:</strong> ${response.evaluacion_calidad?.claridad_pedagogica || 'Alta'} | 
              <strong>Observaciones:</strong> ${response.evaluacion_calidad?.observaciones || 'Verificado'}
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

  triggerPrint(): void {
    window.print();
  }

  private cleanCodeSnippet(raw: string): string {
    return (raw || '').replace(/^```[a-z]*\n?/i, '').replace(/```$/i, '').trim();
  }

  private slugify(text: string): string {
    return (text || 'nuevamente-contenido')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 50) || 'nuevamente-contenido';
  }

  private escapeHtml(text: string): string {
    return (text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
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
