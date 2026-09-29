import { Component, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NuevaMenteApi, NUEVAMENTE_API } from '../../core/api/nuevamente-api';
import { ScenarioComparison, PerfilDestinatario, FormatoSalida } from '../../core/models/adaptation.model';

@Component({
  selector: 'app-comparator',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="comparator-container">
      <div class="page-header">
        <div class="badge-tag">⚡ DEMO FEATURE: SCENARIO COMPARATOR</div>
        <h1>Comparador Multi-Escenario de Adaptación</h1>
        <p>Evalúa de lado a lado cómo el pipeline de IA ajusta el tono, profundidad, tiempo de estudio y citas RAG para un mismo documento.</p>
      </div>

      <!-- Comparison Grid (3 Columns) -->
      <div class="scenarios-grid">
        <div class="column-card glass-card" *ngFor="let sc of scenarios()">
          <div class="column-header" [style.borderTopColor]="getProfileColor(sc.request.perfil_destinatario)">
            <span class="profile-badge" [style.backgroundColor]="getProfileColor(sc.request.perfil_destinatario)">
              {{ sc.request.perfil_destinatario }}
            </span>
            <h3>{{ sc.titulo_escenario }}</h3>
            <span class="format-pill">{{ sc.request.formato_salida }}</span>
          </div>

          <!-- Metrics Matrix -->
          <div class="metrics-matrix">
            <div class="matrix-row">
              <span class="m-key">⏱️ Tiempo Estudio:</span>
              <span class="m-val font-bold">{{ sc.response.metadatos.tiempo_estimado_estudio_minutos }} min</span>
            </div>

            <div class="matrix-row">
              <span class="m-key">🛡️ Anclaje RAG:</span>
              <span class="m-val score-green">{{ (sc.response.evaluacion_calidad.anclaje_fuente_score * 100) | number:'1.0-0' }}%</span>
            </div>

            <div class="matrix-row">
              <span class="m-key">📊 Claridad:</span>
              <span class="m-val">{{ sc.response.evaluacion_calidad.claridad_pedagogica }}</span>
            </div>
          </div>

          <!-- Key Concepts Diff Tags -->
          <div class="concepts-section">
            <span class="section-label">CONCEPTOS CLAVE ADAPTADOS:</span>
            <div class="tags-cloud">
              <span class="tag-item" *ngFor="let concept of sc.response.metadatos.conceptos_clave">
                {{ concept }}
              </span>
            </div>
          </div>

          <!-- Sample Content Snippet -->
          <div class="snippet-preview">
            <span class="section-label">INTRODUCCIÓN CONTEXTUALIZADA:</span>
            <p>{{ sc.response.contenido_adaptado.introduccion_contextualizada }}</p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .comparator-container {
      max-width: 1280px;
      margin: 0 auto;
      padding: 1rem 0;
    }

    .badge-tag {
      font-size: 0.75rem;
      font-weight: 800;
      color: #7C3AED;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }

    .page-header h1 {
      font-size: 2.2rem;
      font-weight: 800;
      margin-bottom: 0.5rem;
    }

    .page-header p {
      color: var(--text-secondary);
      font-size: 1.05rem;
      margin-bottom: 2.5rem;
    }

    .scenarios-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1.5rem;
    }

    .column-card {
      padding: 1.75rem;
      border-radius: 20px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-top: 5px solid #4F46E5;
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .column-header {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .profile-badge {
      align-self: flex-start;
      color: #FFFFFF;
      font-size: 0.78rem;
      font-weight: 800;
      padding: 0.25rem 0.65rem;
      border-radius: 6px;
    }

    .column-header h3 {
      font-size: 1.25rem;
      line-height: 1.3;
    }

    .format-pill {
      font-size: 0.8rem;
      color: var(--text-muted);
      font-weight: 600;
    }

    .metrics-matrix {
      background: var(--bg-app);
      padding: 1rem;
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }

    .matrix-row {
      display: flex;
      justify-content: space-between;
      font-size: 0.88rem;
    }

    .m-key {
      color: var(--text-secondary);
    }

    .m-val.score-green {
      color: #10B981;
      font-weight: 800;
    }

    .section-label {
      font-size: 0.72rem;
      font-weight: 800;
      color: var(--text-muted);
      letter-spacing: 0.05em;
      display: block;
      margin-bottom: 0.5rem;
    }

    .tags-cloud {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }

    .tag-item {
      font-size: 0.78rem;
      background: rgba(99, 102, 241, 0.1);
      color: #4F46E5;
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-weight: 600;
    }

    .snippet-preview p {
      font-size: 0.9rem;
      color: var(--text-secondary);
      line-height: 1.5;
    }

    @media (max-width: 1024px) {
      .scenarios-grid { grid-template-columns: 1fr; }
    }
  `]
})
export class ComparatorComponent {
  private api = inject<NuevaMenteApi>(NUEVAMENTE_API);

  scenarios = signal<ScenarioComparison[]>([]);

  constructor() {
    this.loadMockScenarios();
  }

  getProfileColor(perfil: string): string {
    switch (perfil) {
      case 'Principiante': return '#3B82F6';
      case 'Desarrollador': return '#10B981';
      case 'Lider Tecnico': return '#8B5CF6';
      case 'Ejecutivo': return '#F59E0B';
      default: return '#6366F1';
    }
  }

  private loadMockScenarios(): void {
    const docTitle = 'Introducción a la Arquitectura de Redes VCN en OCI';
    const docText = 'Una Virtual Cloud Network (VCN) en Oracle Cloud Infrastructure...';

    // Scenario 1: Principiante - Flashcards
    this.api.adaptContent({
      documento_titulo: docTitle,
      documento_contenido: docText,
      perfil_destinatario: 'Principiante',
      formato_salida: 'Flashcards',
      nicho_sector: 'General',
      nivel_detalle: 'Didactico'
    }).subscribe(res1 => {
      // Scenario 2: Desarrollador - Tutorial
      this.api.adaptContent({
        documento_titulo: docTitle,
        documento_contenido: docText,
        perfil_destinatario: 'Desarrollador',
        formato_salida: 'Tutorial',
        nicho_sector: 'Fintech',
        nivel_detalle: 'Tecnico'
      }).subscribe(res2 => {
        // Scenario 3: Ejecutivo - Resumen Ejecutivo
        this.api.adaptContent({
          documento_titulo: docTitle,
          documento_contenido: docText,
          perfil_destinatario: 'Ejecutivo',
          formato_salida: 'Resumen Ejecutivo',
          nicho_sector: 'E-commerce',
          nivel_detalle: 'Conciso'
        }).subscribe(res3 => {
          this.scenarios.set([
            {
              id: 'sc-1',
              titulo_escenario: 'Principiante · Flashcards',
              request: { documento_titulo: docTitle, documento_contenido: docText, perfil_destinatario: 'Principiante', formato_salida: 'Flashcards', nicho_sector: 'General', nivel_detalle: 'Didactico' },
              response: res1,
              created_at: new Date()
            },
            {
              id: 'sc-2',
              titulo_escenario: 'Desarrollador · Tutorial CLI',
              request: { documento_titulo: docTitle, documento_contenido: docText, perfil_destinatario: 'Desarrollador', formato_salida: 'Tutorial', nicho_sector: 'Fintech', nivel_detalle: 'Tecnico' },
              response: res2,
              created_at: new Date()
            },
            {
              id: 'sc-3',
              titulo_escenario: 'Ejecutivo · Brief de Impacto',
              request: { documento_titulo: docTitle, documento_contenido: docText, perfil_destinatario: 'Ejecutivo', formato_salida: 'Resumen Ejecutivo', nicho_sector: 'E-commerce', nivel_detalle: 'Conciso' },
              response: res3,
              created_at: new Date()
            }
          ]);
        });
      });
    });
  }
}
