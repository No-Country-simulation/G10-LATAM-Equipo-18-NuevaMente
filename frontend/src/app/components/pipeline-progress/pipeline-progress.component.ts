import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-pipeline-progress',
  template: `
    <div class="pipeline-container">
      <div class="pipeline-header">
        <div class="pipeline-tag">PROCESANDO TU CONTENIDO</div>
        <h1 class="pipeline-title">Generación en curso</h1>
        <p class="pipeline-sub">Tu contenido se está construyendo con RAG y validación pedagógica.</p>
      </div>

      <!-- Horizontal Pipeline Steps Bar -->
      <div class="pipeline-steps-bar">
        <div class="p-step checked">
          <div class="p-icon">✓</div>
          <span>Extracción</span>
        </div>
        <div class="p-line checked"></div>

        <div class="p-step checked">
          <div class="p-icon">✓</div>
          <span>Chunking</span>
        </div>
        <div class="p-line checked"></div>

        <div class="p-step checked">
          <div class="p-icon">✓</div>
          <span>Embeddings</span>
        </div>
        <div class="p-line active"></div>

        <div class="p-step active">
          <div class="p-icon spinner-small"></div>
          <span>Recuperación RAG</span>
        </div>
        <div class="p-line"></div>

        <div class="p-step">
          <div class="p-icon"></div>
          <span>Generación final</span>
        </div>
      </div>

      <div class="pipeline-grid">
        <!-- Main Circular Gauge Panel (Left) -->
        <div class="gauge-panel">
          <div class="gauge-card">
            <div class="radial-progress-box">
              <svg viewBox="0 0 36 36" class="circular-chart blue">
                <path class="circle-bg"
                  d="M18 2.0845
                    a 15.9155 15.9155 0 0 1 0 31.831
                    a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path class="circle"
                  [attr.stroke-dasharray]="progressPercentage + ', 100'"
                  d="M18 2.0845
                    a 15.9155 15.9155 0 0 1 0 31.831
                    a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <text x="18" y="20.35" class="percentage">{{ progressPercentage }}%</text>
              </svg>
            </div>

            <h2 class="gauge-status-title">Procesando documento</h2>
            <p class="gauge-status-desc">Estamos analizando, recuperando y generando contenido de alta calidad.</p>
            <div class="gauge-timer">
              <span class="clock-icon">🕒</span> Esto puede tomar unos minutos.
            </div>
          </div>

          <!-- Status Checklist items -->
          <div class="status-items-list">
            <div class="status-item">
              <div class="status-left">
                <div class="status-icon green">✓</div>
                <div>
                  <div class="status-name">Extracción + limpieza</div>
                  <div class="status-sub">Extrayendo texto, limpiando y estructurando el contenido del documento.</div>
                </div>
              </div>
              <span class="badge badge-green">Completado</span>
            </div>

            <div class="status-item">
              <div class="status-left">
                <div class="status-icon blue spinner-icon">↻</div>
                <div>
                  <div class="status-name">FAISS + recuperación</div>
                  <div class="status-sub">Generando embeddings y recuperando información relevante con RAG.</div>
                </div>
              </div>
              <span class="badge badge-blue">En curso</span>
            </div>

            <div class="status-item disabled">
              <div class="status-left">
                <div class="status-icon gray">🕒</div>
                <div>
                  <div class="status-name">Revisión de fidelidad</div>
                  <div class="status-sub">Validando precisión, coherencia y alineación pedagógica del contenido.</div>
                </div>
              </div>
              <span class="badge badge-gray">Pendiente</span>
            </div>
          </div>

          <div class="window-note">
            <span class="info-icon">ℹ️</span> No cierres esta ventana. El resultado aparecerá automáticamente.
          </div>
        </div>

        <!-- Pipeline Diagram Panel (Right) -->
        <div class="pipeline-diagram-panel">
          <h3 class="diagram-title">Vista del pipeline</h3>
          <p class="diagram-sub">Así se transforma tu documento en contenido de aprendizaje.</p>

          <div class="pipeline-flow-list">
            <div class="flow-step done">
              <div class="flow-icon">📄</div>
              <div class="flow-info">
                <div class="flow-name">Documento</div>
                <div class="flow-desc">Archivo cargado</div>
              </div>
              <div class="flow-check">✓</div>
            </div>
            <div class="flow-connector">↓</div>

            <div class="flow-step done">
              <div class="flow-icon">✂️</div>
              <div class="flow-info">
                <div class="flow-name">Chunking</div>
                <div class="flow-desc">División en fragmentos</div>
              </div>
              <div class="flow-check">✓</div>
            </div>
            <div class="flow-connector">↓</div>

            <div class="flow-step done">
              <div class="flow-icon">🗄️</div>
              <div class="flow-info">
                <div class="flow-name">Vector Store</div>
                <div class="flow-desc">Embeddings en FAISS</div>
              </div>
              <div class="flow-check">✓</div>
            </div>
            <div class="flow-connector">↓</div>

            <div class="flow-step active">
              <div class="flow-icon">🔍</div>
              <div class="flow-info">
                <div class="flow-name">RAG</div>
                <div class="flow-desc">Recuperación semántica</div>
              </div>
            </div>
            <div class="flow-connector">↓</div>

            <div class="flow-step">
              <div class="flow-icon">🧠</div>
              <div class="flow-info">
                <div class="flow-name">LLM</div>
                <div class="flow-desc">Generación de contenido</div>
              </div>
            </div>
            <div class="flow-connector">↓</div>

            <div class="flow-step">
              <div class="flow-icon">&#123; &#125;</div>
              <div class="flow-info">
                <div class="flow-name">JSON</div>
                <div class="flow-desc">Estructuración final</div>
              </div>
            </div>
            <div class="flow-connector">↓</div>

            <div class="flow-step">
              <div class="flow-icon">☁️</div>
              <div class="flow-info">
                <div class="flow-name">OCI</div>
                <div class="flow-desc">Almacenamiento en la nube</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .pipeline-container {
      max-width: 1100px;
      margin: 0 auto;
    }
    .pipeline-tag {
      font-size: 0.75rem;
      font-weight: 700;
      color: #3b82f6;
      letter-spacing: 0.08em;
      margin-bottom: 0.25rem;
    }
    .pipeline-title {
      font-size: 2.25rem;
      font-weight: 800;
      color: #0f172a;
    }
    .pipeline-sub {
      font-size: 1rem;
      color: #64748b;
      margin-bottom: 2rem;
    }

    /* Horizontal Steps Bar */
    .pipeline-steps-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 1.25rem 2rem;
      margin-bottom: 2rem;
    }
    .p-step {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      font-size: 0.85rem;
      font-weight: 600;
      color: #94a3b8;
    }
    .p-step.checked, .p-step.active {
      color: #0f172a;
    }
    .p-icon {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: #f1f5f9;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.75rem;
    }
    .p-step.checked .p-icon {
      background: #dbeafe;
      color: #2563eb;
    }
    .p-step.active .p-icon {
      background: #eff6ff;
      border: 2px solid #3b82f6;
    }
    .p-line {
      flex: 1;
      height: 2px;
      background: #e2e8f0;
      margin: 0 1rem;
    }
    .p-line.checked, .p-line.active {
      background: #3b82f6;
    }

    /* Pipeline Grid */
    .pipeline-grid {
      display: grid;
      grid-template-columns: 1.4fr 0.8fr;
      gap: 2rem;
    }

    .gauge-panel {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .gauge-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 20px;
      padding: 2.5rem;
      text-align: center;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02);
    }

    /* SVG Radial Chart */
    .radial-progress-box {
      width: 140px;
      height: 140px;
      margin: 0 auto 1.5rem;
    }
    .circular-chart {
      display: block;
      margin: 10px auto;
      max-width: 100%;
      max-height: 250px;
    }
    .circle-bg {
      fill: none;
      stroke: #f1f5f9;
      stroke-width: 3.8;
    }
    .circle {
      fill: none;
      stroke-width: 3.8;
      stroke-linecap: round;
      animation: progress 1s ease-out forwards;
      stroke: #3b82f6;
    }
    .percentage {
      fill: #0f172a;
      font-family: sans-serif;
      font-size: 0.55em;
      font-weight: 800;
      text-anchor: middle;
    }

    .gauge-status-title {
      font-size: 1.35rem;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 0.35rem;
    }
    .gauge-status-desc {
      font-size: 0.9rem;
      color: #64748b;
      margin-bottom: 1.25rem;
    }
    .gauge-timer {
      font-size: 0.82rem;
      color: #94a3b8;
    }

    /* Checklist */
    .status-items-list {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 20px;
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }
    .status-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 1rem;
      border-bottom: 1px solid #f1f5f9;
    }
    .status-item:last-child {
      border-bottom: none;
      padding-bottom: 0;
    }
    .status-left {
      display: flex;
      align-items: flex-start;
      gap: 0.85rem;
    }
    .status-icon {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.85rem;
    }
    .status-icon.green { background: #dcfce7; color: #16a34a; }
    .status-icon.blue { background: #dbeafe; color: #2563eb; }
    .status-icon.gray { background: #f1f5f9; color: #94a3b8; }

    .status-name {
      font-size: 0.92rem;
      font-weight: 700;
      color: #0f172a;
    }
    .status-sub {
      font-size: 0.78rem;
      color: #64748b;
    }

    .window-note {
      text-align: center;
      font-size: 0.82rem;
      color: #64748b;
      margin-top: 0.5rem;
    }

    /* Diagram Panel */
    .pipeline-diagram-panel {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 20px;
      padding: 1.75rem;
    }
    .diagram-title {
      font-size: 1.15rem;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 0.25rem;
    }
    .diagram-sub {
      font-size: 0.82rem;
      color: #64748b;
      margin-bottom: 1.5rem;
    }
    .pipeline-flow-list {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
    }
    .flow-step {
      width: 100%;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
    }
    .flow-step.done {
      background: #f0fdf4;
      border-color: #bbf7d0;
    }
    .flow-step.active {
      background: #eff6ff;
      border-color: #93c5fd;
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    .flow-icon {
      font-size: 1.1rem;
    }
    .flow-info { flex: 1; }
    .flow-name {
      font-size: 0.85rem;
      font-weight: 700;
      color: #0f172a;
    }
    .flow-desc {
      font-size: 0.72rem;
      color: #64748b;
    }
    .flow-check {
      color: #16a34a;
      font-weight: 800;
    }
    .flow-connector {
      color: #cbd5e1;
      font-size: 0.85rem;
    }

    .spinner-icon {
      animation: spin 1s linear infinite;
    }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

    @media (max-width: 900px) {
      .pipeline-grid { grid-template-columns: 1fr; }
    }
  `]
})
export class PipelineProgressComponent {
  @Input() progressPercentage: number = 78;
  @Input() currentStage: string = 'FAISS + recuperación';
}
