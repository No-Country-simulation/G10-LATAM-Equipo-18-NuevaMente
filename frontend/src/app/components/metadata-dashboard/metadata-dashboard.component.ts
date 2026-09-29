import { Component, Input } from '@angular/core';
import { Metadatos, EvaluacionCalidad, AlmacenamientoOCI } from '../../core/models/adaptation.model';

@Component({
  selector: 'app-metadata-dashboard',
  template: `
    <div class="metadata-wrapper">
      <h3 class="meta-section-title">📊 Metadatos del Procesamiento RAG & OCI</h3>

      <div class="metadata-grid">
        <!-- Card 1: Metadatos Didácticos -->
        <div class="meta-card">
          <h4>🎯 Perfil y Conceptos Clave</h4>
          <div class="meta-row">
            <span class="label">Perfil Aplicado:</span>
            <span class="value">{{ metadatos?.perfil_aplicado || 'Principiante' }}</span>
          </div>
          <div class="meta-row">
            <span class="label">Formato Generado:</span>
            <span class="value">{{ metadatos?.formato_generado || 'Tutorial' }}</span>
          </div>
          <div class="meta-row">
            <span class="label">Estudio Estimado:</span>
            <span class="value">{{ metadatos?.tiempo_estimado_estudio_minutos || 5 }} min</span>
          </div>

          <div class="concepts-box">
            <div class="box-label">Conceptos Clave (Graph RAG DAG):</div>
            <div class="concept-tags">
              <span *ngFor="let c of metadatos?.conceptos_clave" class="badge-tag">{{ c }}</span>
              <span *ngIf="!metadatos?.conceptos_clave" class="badge-tag">VCN</span>
              <span *ngIf="!metadatos?.conceptos_clave" class="badge-tag">Subredes</span>
              <span *ngIf="!metadatos?.conceptos_clave" class="badge-tag">Security Lists</span>
            </div>
          </div>
        </div>

        <!-- Card 2: Evaluación de Calidad -->
        <div class="meta-card">
          <h4>⚖️ Evaluación & Anclaje de Fuentes</h4>
          <div class="meta-row">
            <span class="label">Score Anclaje Fuente:</span>
            <span class="value text-success font-bold">
              {{ (evaluacion?.anclaje_fuente_score || 0.98) * 100 }}%
            </span>
          </div>
          <div class="meta-row">
            <span class="label">Claridad Pedagógica:</span>
            <span class="value">{{ evaluacion?.claridad_pedagogica || 'Alta' }}</span>
          </div>
          <div class="obs-box">
            <strong>Observaciones del Auditor:</strong>
            <p>{{ evaluacion?.observaciones || 'Lenguaje ajustado con analogías para público principiante.' }}</p>
          </div>
        </div>

        <!-- Card 3: Persistencia OCI -->
        <div class="meta-card">
          <h4>☁️ Oracle Cloud (OCI Always Free)</h4>
          <div class="meta-row">
            <span class="label">Bucket OCI:</span>
            <span class="value font-mono">{{ oci?.bucket || 'nuevamente-contenidos-educativos' }}</span>
          </div>
          <div class="meta-row">
            <span class="label">Objeto ID:</span>
            <span class="value font-mono">{{ oci?.objeto_id || 'contenido-vcn-001.json' }}</span>
          </div>
          <div class="meta-row">
            <span class="label">Estado de Carga:</span>
            <span class="badge badge-green">{{ oci?.status_upload || 'completado' }}</span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .metadata-wrapper {
      margin-bottom: 2rem;
    }
    .meta-section-title {
      font-size: 1.2rem;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 1.25rem;
    }

    .metadata-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 1.25rem;
    }

    .meta-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 1.5rem;
    }
    .meta-card h4 {
      font-size: 1rem;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 1rem;
      border-bottom: 1px solid #f1f5f9;
      padding-bottom: 0.5rem;
    }

    .meta-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.75rem;
      font-size: 0.88rem;
    }
    .label { color: #64748b; font-weight: 600; }
    .value { color: #0f172a; font-weight: 700; }
    .text-success { color: #16a34a; }
    .font-bold { font-weight: 800; }
    .font-mono { font-family: monospace; font-size: 0.8rem; color: #475569; }

    .concepts-box {
      margin-top: 1rem;
      padding-top: 0.75rem;
      border-top: 1px solid #f1f5f9;
    }
    .box-label {
      font-size: 0.78rem;
      color: #64748b;
      margin-bottom: 0.5rem;
      font-weight: 700;
    }
    .concept-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }
    .badge-tag {
      background: #eff6ff;
      color: #2563eb;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.2rem 0.6rem;
      border-radius: 12px;
      border: 1px solid #bfdbfe;
    }

    .obs-box {
      margin-top: 1rem;
      background: #f8fafc;
      border-left: 3px solid #3b82f6;
      padding: 0.75rem;
      border-radius: 6px;
      font-size: 0.82rem;
      color: #334155;
    }
  `]
})
export class MetadataDashboardComponent {
  @Input() metadatos?: Metadatos;
  @Input() evaluacion?: EvaluacionCalidad;
  @Input() oci?: AlmacenamientoOCI;
}
