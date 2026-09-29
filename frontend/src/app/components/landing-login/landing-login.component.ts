import { Component, EventEmitter, Output } from '@angular/core';
import { ApiService } from '../../core/services/api.service';

export interface LoginEvent {
  email: string;
  name: string;
  token?: string;
}

@Component({
  selector: 'app-landing-login',
  template: `
    <div class="landing-page">
      <!-- Navbar header for Landing -->
      <header class="top-nav">
        <div class="brand" (click)="scrollToSection('top')">
          <div class="logo-icon">🎓</div>
          <span class="brand-name">NuevaMente</span>
        </div>

        <nav class="nav-links">
          <a (click)="scrollToSection('producto')">Producto</a>
          <a (click)="scrollToSection('beneficios')">Beneficios</a>
          <a (click)="scrollToSection('recursos')">Recursos</a>
          <a (click)="scrollToSection('precios')">Precios</a>
        </nav>

        <button class="btn btn-primary btn-access" (click)="activateRegisterMode()">
          Registrarse gratis
        </button>
      </header>

      <!-- Hero Section & Auth Card -->
      <section id="top" class="landing-hero">
        <!-- Left Hero Section -->
        <div class="hero-content">
          <div class="tag-pill">DOCUMENTACIÓN QUE ENSEÑA</div>
          <h1 class="hero-title">
            Convierte documentación técnica en experiencias de aprendizaje
          </h1>
          <p class="hero-description">
            NuevaMente transforma manuales, guías y documentación técnica en contenido educativo claro, estructurado y atractivo.
          </p>

          <ul class="features-list">
            <li>
              <span class="check-icon">✓</span>
              <span>Ahorra tiempo en la creación de contenido</span>
            </li>
            <li>
              <span class="check-icon">✓</span>
              <span>Facilita el aprendizaje de temas complejos</span>
            </li>
            <li>
              <span class="check-icon">✓</span>
              <span>Impulsa el conocimiento en tu equipo</span>
            </li>
          </ul>

          <div class="hero-illustration-box">
            <div class="graphic-card">
              <div class="card-icon">📄</div>
              <div class="card-text">
                <span class="label">Documentación técnica</span>
                <span class="sub">Texto denso / Manuales</span>
              </div>
            </div>

            <div class="arrow-connector">➔</div>

            <div class="graphic-card highlight">
              <div class="card-icon">📚</div>
              <div class="card-text">
                <span class="label">Contenido educativo</span>
                <span class="sub">Guías, Flashcards & Quiz</span>
              </div>
            </div>
          </div>
          <div class="hero-footer-tagline">MISMA INFORMACIÓN, MÁS APRENDIZAJE.</div>
        </div>

        <!-- Right Login / Register Card -->
        <div class="login-wrapper" id="auth-card">
          <div class="login-card">
            <!-- Mode Toggle Tabs -->
            <div class="auth-tabs">
              <button 
                type="button" 
                class="auth-tab-btn" 
                [class.active]="!isRegisterMode" 
                (click)="toggleMode('login')"
              >
                Iniciar sesión
              </button>
              <button 
                type="button" 
                class="auth-tab-btn" 
                [class.active]="isRegisterMode" 
                (click)="toggleMode('register')"
              >
                Registrarse gratis
              </button>
            </div>

            <h2 class="login-title">
              {{ isRegisterMode ? 'Crea tu cuenta' : 'Bienvenido de nuevo' }}
            </h2>
            <p class="login-subtitle">
              {{ isRegisterMode ? 'Ingresa tus datos para registrarte gratis' : 'Inicia sesión para continuar' }}
            </p>

            <div *ngIf="errorMessage" class="alert-error">
              ⚠️ {{ errorMessage }}
            </div>

            <div *ngIf="successMessage" class="alert-success">
              ✅ {{ successMessage }}
            </div>

            <form (ngSubmit)="onFormSubmit()" class="login-form">
              <!-- Name Input (Shown in Register mode) -->
              <div class="form-group" *ngIf="isRegisterMode">
                <label>Nombre Completo</label>
                <input 
                  type="text" 
                  id="name-input"
                  class="form-control" 
                  [(ngModel)]="name" 
                  name="name" 
                  placeholder="Ej. Ana Martínez" 
                  required 
                />
              </div>

              <!-- Email Input -->
              <div class="form-group">
                <label>Correo electrónico</label>
                <input 
                  type="email" 
                  class="form-control" 
                  [(ngModel)]="email" 
                  name="email" 
                  placeholder="tu@empresa.com" 
                  required 
                />
              </div>

              <!-- Password Input -->
              <div class="form-group">
                <div class="pwd-header">
                  <label>Contraseña</label>
                  <a *ngIf="!isRegisterMode" href="#" class="forgot-link" (click)="$event.preventDefault()">¿Olvidaste tu contraseña?</a>
                </div>
                <div class="pwd-input-wrapper">
                  <input 
                    [type]="showPassword ? 'text' : 'password'" 
                    class="form-control" 
                    [(ngModel)]="password" 
                    name="password" 
                    placeholder="Tu contraseña" 
                    required 
                  />
                  <span class="eye-toggle" (click)="showPassword = !showPassword">
                    {{ showPassword ? '👁️' : '👁️‍🗨️' }}
                  </span>
                </div>
              </div>

              <div class="form-remember" *ngIf="!isRegisterMode">
                <label class="checkbox-label">
                  <input type="checkbox" [(ngModel)]="rememberMe" name="rememberMe" />
                  <span>Recordarme</span>
                </label>
              </div>

              <button type="submit" class="btn btn-primary btn-submit-login" [disabled]="isLoading">
                <span *ngIf="!isLoading">{{ isRegisterMode ? 'Crear mi cuenta gratis' : 'Iniciar sesión' }}</span>
                <span *ngIf="isLoading" class="spinner">⏳ Procesando...</span>
              </button>

              <div class="divider">
                <span>o</span>
              </div>

              <!-- Google Sign-In Button -->
              <button type="button" class="btn btn-google-sso" (click)="onGoogleLogin()">
                <svg class="google-icon" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                <span>Continuar con Google</span>
              </button>

              <div class="signup-prompt">
                <ng-container *ngIf="!isRegisterMode">
                  ¿No tienes una cuenta? <a href="#" (click)="$event.preventDefault(); toggleMode('register')">Regístrate gratis</a>
                </ng-container>
                <ng-container *ngIf="isRegisterMode">
                  ¿Ya tienes una cuenta? <a href="#" (click)="$event.preventDefault(); toggleMode('login')">Iniciar sesión</a>
                </ng-container>
              </div>
            </form>
          </div>
        </div>
      </section>

      <!-- SECTION 1: PRODUCTO -->
      <section id="producto" class="landing-section bg-white">
        <div class="section-container">
          <div class="section-badge">TECNOLOGÍA DE VANGUARDIA</div>
          <h2 class="section-title">Arquitectura RAG Multimodal & Multi-Agente</h2>
          <p class="section-subtitle">
            Combina los mejores modelos de procesamiento de texto con grafos de conocimiento y re-ranking híbrido para una adaptación literaria y técnica impecable.
          </p>

          <div class="features-grid">
            <div class="feature-card">
              <div class="feature-icon">🧠</div>
              <h3>RAG Híbrido + Re-ranking Cohere</h3>
              <p>Búsqueda léxica BM25 combinada con similitud coseno densa y Reciprocal Rank Fusion (RRF) para recuperar los fragmentos con mayor precisión contextual.</p>
            </div>

            <div class="feature-card">
              <div class="feature-icon">🕸️</div>
              <h3>Graph RAG & DAG de Conceptos</h3>
              <p>Extracción semántica de conceptos clave y sus dependencias para construir un Grafo Acíclico Dirigido (DAG) que estructura el flujo de aprendizaje.</p>
            </div>

            <div class="feature-card">
              <div class="feature-icon">🤖</div>
              <h3>Orquestación Multi-Agente LLM</h3>
              <p>Ruteo inteligente entre Gemini 1.5 Pro, Gemini Flash y Groq Llama 3 para lograr la máxima velocidad sin comprometer la profundidad pedagógica.</p>
            </div>

            <div class="feature-card">
              <div class="feature-icon">📄</div>
              <h3>Generador PDF en OCI</h3>
              <p>Exportación de documentos formativos con maquetación limpia a 0px de margen, listos para descargar o guardar en Oracle Cloud Infrastructure.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- SECTION 2: BENEFICIOS -->
      <section id="beneficios" class="landing-section bg-light">
        <div class="section-container">
          <div class="section-badge">VALOR MEDIBLE</div>
          <h2 class="section-title">¿Por qué elegir NuevaMente?</h2>
          <p class="section-subtitle">
            Aumenta el compromiso y retención de conocimiento en equipos de ingeniería, tecnología y educación.
          </p>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-number">85%</div>
              <div class="stat-label">Ahorro de Tiempo</div>
              <p class="stat-desc">Reduce horas de lectura manual transformando archivos extensos en minutos.</p>
            </div>

            <div class="stat-card">
              <div class="stat-number">98%+</div>
              <div class="stat-label">Anclaje a Fuentes</div>
              <p class="stat-desc">Garantía de fidelidad estricta al documento original sin invención ni alucinaciones.</p>
            </div>

            <div class="stat-card">
              <div class="stat-number">3x</div>
              <div class="stat-label">Retención Didáctica</div>
              <p class="stat-desc">Flashcards y quizzes interactivos diseñados según principios de repetición espaciada.</p>
            </div>

            <div class="stat-card">
              <div class="stat-number">100%</div>
              <div class="stat-label">Multi-Audiencia</div>
              <p class="stat-desc">Personalización automática de tono y nivel de detalle desde Principiante a Experto.</p>
            </div>
          </div>
        </div>
      </section>

      <!-- SECTION 3: RECURSOS -->
      <section id="recursos" class="landing-section bg-white">
        <div class="section-container">
          <div class="section-badge">RECURSOS & EJEMPLOS</div>
          <h2 class="section-title">Explora Ejemplos de Contenido Adaptado</h2>
          <p class="section-subtitle">
            Prueba cómo la plataforma transforma documentación técnica real en experiencias formativas.
          </p>

          <div class="resources-grid">
            <div class="resource-card">
              <div class="resource-type">FLASHCARDS</div>
              <h3>Redes VCN en Oracle Cloud</h3>
              <p>Manual técnico de 40 páginas sintetizado en 10 tarjetas dinámicas con pistas didácticas.</p>
              <button class="btn-link" (click)="activateRegisterMode()">Probar ejemplo ➔</button>
            </div>

            <div class="resource-card">
              <div class="resource-type">QUIZ INTERACTIVO</div>
              <h3>Evaluación de Microservicios</h3>
              <p>Cuestionario de opción múltiple con justificación pedagógica en tiempo real para cada respuesta.</p>
              <button class="btn-link" (click)="activateRegisterMode()">Probar ejemplo ➔</button>
            </div>

            <div class="resource-card">
              <div class="resource-type">RESUMEN TL;DR</div>
              <h3>Manual de Seguridad IAM</h3>
              <p>Resumen ejecutivo estructurado en 5 puntos clave con terminología técnica contextualizada.</p>
              <button class="btn-link" (click)="activateRegisterMode()">Probar ejemplo ➔</button>
            </div>
          </div>
        </div>
      </section>

      <!-- SECTION 4: PRECIOS -->
      <section id="precios" class="landing-section bg-light">
        <div class="section-container">
          <div class="section-badge">PLANES & PRECIOS</div>
          <h2 class="section-title">Elige el plan ideal para tus necesidades</h2>
          <p class="section-subtitle">
            Comienza gratis hoy mismo y escala según el volumen de documentación de tu equipo.
          </p>

          <div class="pricing-grid">
            <!-- Free Plan -->
            <div class="pricing-card">
              <div class="pricing-header">
                <h3>Starter</h3>
                <p>Ideal para probar el motor de adaptación</p>
                <div class="price">$0 <span>/ mes</span></div>
              </div>
              <ul class="pricing-features">
                <li>✓ 5 Adaptaciones de contenido al mes</li>
                <li>✓ RAG Híbrido Estándar</li>
                <li>✓ Flashcards y Quizzes interactivos</li>
                <li>✓ Exportación PDF sin marcas</li>
              </ul>
              <button class="btn btn-outline btn-pricing" (click)="activateRegisterMode()">
                Registrarse gratis
              </button>
            </div>

            <!-- Pro Plan (Popular) -->
            <div class="pricing-card popular">
              <div class="popular-tag">MÁS POPULAR</div>
              <div class="pricing-header">
                <h3>Pro Educador</h3>
                <p>Para ingenieros, docentes y creadores de contenido</p>
                <div class="price">$19 <span>/ mes</span></div>
              </div>
              <ul class="pricing-features">
                <li>✓ Adaptaciones ilimitadas</li>
                <li>✓ Graph RAG & DAG de Conceptos</li>
                <li>✓ Re-ranking multilingüe Cohere</li>
                <li>✓ Personalización de perfil de audiencia</li>
                <li>✓ Soporte prioritario por correo</li>
              </ul>
              <button class="btn btn-primary btn-pricing" (click)="activateRegisterMode()">
                Registrarse gratis
              </button>
            </div>

            <!-- Enterprise Plan -->
            <div class="pricing-card">
              <div class="pricing-header">
                <h3>Enterprise</h3>
                <p>Para empresas y equipos de alta escala</p>
                <div class="price">$49 <span>/ mes</span></div>
              </div>
              <ul class="pricing-features">
                <li>✓ Todo lo del plan Pro</li>
                <li>✓ Integración privada OCI Storage</li>
                <li>✓ API Dedicada & Conectores LMS</li>
                <li>✓ Modelos ajustados a tu dominio</li>
                <li>✓ Gestor de cuenta dedicado</li>
              </ul>
              <button class="btn btn-outline btn-pricing" (click)="activateRegisterMode()">
                Registrarse gratis
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Footer -->
      <footer class="landing-footer">
        <div class="footer-links">
          <a (click)="scrollToSection('top')">Inicio</a>
          <a (click)="scrollToSection('producto')">Producto</a>
          <a (click)="scrollToSection('beneficios')">Beneficios</a>
          <a (click)="scrollToSection('precios')">Precios</a>
        </div>
        <div class="footer-copy">© 2026 NuevaMente - Sistema Inteligente de Adaptación Educativa.</div>
      </footer>
    </div>
  `,
  styles: [`
    .landing-page {
      min-height: 100vh;
      background: linear-gradient(135deg, #f8fafc 0%, #edf2f7 100%);
      display: flex;
      flex-direction: column;
      font-family: system-ui, -apple-system, sans-serif;
    }
    .top-nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1.25rem 4rem;
      background: #ffffff;
      border-bottom: 1px solid #e2e8f0;
      position: sticky;
      top: 0;
      z-index: 1000;
      box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      cursor: pointer;
    }
    .logo-icon {
      font-size: 1.75rem;
    }
    .brand-name {
      font-size: 1.35rem;
      font-weight: 800;
      color: #0f172a;
    }
    .nav-links {
      display: flex;
      gap: 2rem;
    }
    .nav-links a {
      color: #475569;
      font-weight: 600;
      font-size: 0.95rem;
      cursor: pointer;
      transition: color 0.2s;
    }
    .nav-links a:hover {
      color: #2563eb;
    }
    .btn-access {
      padding: 0.6rem 1.25rem;
      font-size: 0.9rem;
      border-radius: 8px;
    }

    .landing-hero {
      max-width: 1200px;
      margin: 3rem auto;
      padding: 0 2rem;
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 4rem;
      align-items: center;
      flex: 1;
    }

    .tag-pill {
      display: inline-block;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      color: #2563eb;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      padding: 0.3rem 0.8rem;
      border-radius: 20px;
      margin-bottom: 1.25rem;
    }

    .hero-title {
      font-size: 2.75rem;
      font-weight: 800;
      color: #0f172a;
      line-height: 1.15;
      margin-bottom: 1.25rem;
      letter-spacing: -0.02em;
    }

    .hero-description {
      font-size: 1.1rem;
      color: #64748b;
      line-height: 1.6;
      margin-bottom: 2rem;
    }

    .features-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 0.85rem;
      margin-bottom: 2.5rem;
      padding-left: 0;
    }
    .features-list li {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 1rem;
      color: #334155;
      font-weight: 500;
    }
    .check-icon {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: #dbeafe;
      color: #2563eb;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      font-weight: 800;
    }

    .hero-illustration-box {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 1.5rem;
      display: flex;
      align-items: center;
      justify-content: space-around;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.04);
      margin-bottom: 1rem;
    }
    .graphic-card {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      background: #f8fafc;
      border-radius: 10px;
      border: 1px solid #e2e8f0;
    }
    .graphic-card.highlight {
      background: #eff6ff;
      border-color: #bfdbfe;
    }
    .card-icon {
      font-size: 1.5rem;
    }
    .card-text {
      display: flex;
      flex-direction: column;
    }
    .card-text .label {
      font-size: 0.85rem;
      font-weight: 700;
      color: #0f172a;
    }
    .card-text .sub {
      font-size: 0.75rem;
      color: #64748b;
    }
    .arrow-connector {
      font-size: 1.25rem;
      color: #2563eb;
    }
    .hero-footer-tagline {
      font-size: 0.75rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      color: #94a3b8;
    }

    /* Auth Card & Tabs */
    .login-card {
      background: #ffffff;
      border-radius: 20px;
      padding: 2.5rem;
      border: 1px solid #e2e8f0;
      box-shadow: 0 20px 40px -15px rgba(0,0,0,0.08);
      transition: all 0.3s ease;
    }

    .auth-tabs {
      display: flex;
      background: #f1f5f9;
      padding: 4px;
      border-radius: 12px;
      margin-bottom: 1.75rem;
    }
    .auth-tab-btn {
      flex: 1;
      padding: 0.6rem 0.5rem;
      border: none;
      background: transparent;
      border-radius: 8px;
      font-size: 0.88rem;
      font-weight: 600;
      color: #64748b;
      cursor: pointer;
      transition: all 0.2s;
    }
    .auth-tab-btn.active {
      background: #ffffff;
      color: #2563eb;
      font-weight: 700;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    .login-title {
      font-size: 1.65rem;
      font-weight: 800;
      color: #0f172a;
      text-align: center;
      margin-bottom: 0.25rem;
    }
    .login-subtitle {
      font-size: 0.9rem;
      color: #64748b;
      text-align: center;
      margin-bottom: 1.5rem;
    }

    .alert-error {
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #991b1b;
      padding: 0.75rem 1rem;
      border-radius: 10px;
      font-size: 0.85rem;
      margin-bottom: 1.25rem;
    }

    .alert-success {
      background: #f0fdf4;
      border: 1px solid #bbf7d0;
      color: #166534;
      padding: 0.75rem 1rem;
      border-radius: 10px;
      font-size: 0.85rem;
      margin-bottom: 1.25rem;
    }

    .pwd-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .forgot-link {
      font-size: 0.8rem;
      color: #2563eb;
    }
    .pwd-input-wrapper {
      position: relative;
    }
    .eye-toggle {
      position: absolute;
      right: 1rem;
      top: 50%;
      transform: translateY(-50%);
      cursor: pointer;
      font-size: 0.9rem;
    }
    .form-remember {
      margin-bottom: 1.25rem;
    }
    .checkbox-label {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.85rem;
      color: #475569;
      cursor: pointer;
    }
    .btn-submit-login {
      width: 100%;
      padding: 0.9rem;
      font-size: 1rem;
      border-radius: 10px;
    }
    .divider {
      text-align: center;
      position: relative;
      margin: 1.25rem 0;
    }
    .divider::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 0;
      right: 0;
      height: 1px;
      background: #e2e8f0;
    }
    .divider span {
      position: relative;
      background: #ffffff;
      padding: 0 0.75rem;
      font-size: 0.8rem;
      color: #94a3b8;
    }
    
    .btn-google-sso {
      width: 100%;
      padding: 0.85rem;
      border-radius: 10px;
      margin-bottom: 1.25rem;
      background: #ffffff;
      border: 1px solid #cbd5e1;
      color: #334155;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.75rem;
      box-shadow: 0 1px 2px rgba(0,0,0,0.05);
      transition: all 0.2s;
      cursor: pointer;
    }
    .btn-google-sso:hover {
      background: #f8fafc;
      border-color: #94a3b8;
    }
    .google-icon {
      width: 20px;
      height: 20px;
    }

    .signup-prompt {
      text-align: center;
      font-size: 0.85rem;
      color: #64748b;
    }
    .signup-prompt a {
      font-weight: 700;
      color: #2563eb;
    }

    /* Landing Sections Styling */
    .landing-section {
      padding: 5rem 2rem;
    }
    .bg-white { background: #ffffff; }
    .bg-light { background: #f8fafc; }

    .section-container {
      max-width: 1150px;
      margin: 0 auto;
    }
    .section-badge {
      font-size: 0.75rem;
      font-weight: 800;
      letter-spacing: 0.08em;
      color: #2563eb;
      text-transform: uppercase;
      margin-bottom: 0.5rem;
    }
    .section-title {
      font-size: 2.25rem;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 0.75rem;
      letter-spacing: -0.02em;
    }
    .section-subtitle {
      font-size: 1.1rem;
      color: #64748b;
      max-width: 700px;
      margin-bottom: 3rem;
      line-height: 1.5;
    }

    /* Features Grid (Producto) */
    .features-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 2rem;
    }
    .feature-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 2rem;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    .feature-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 12px 24px -6px rgba(0,0,0,0.06);
    }
    .feature-icon {
      font-size: 2.5rem;
      margin-bottom: 1rem;
    }
    .feature-card h3 {
      font-size: 1.2rem;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 0.5rem;
    }
    .feature-card p {
      font-size: 0.92rem;
      color: #64748b;
      line-height: 1.5;
    }

    /* Stats Grid (Beneficios) */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 2rem;
    }
    .stat-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 2rem;
      text-align: center;
      box-shadow: 0 4px 12px rgba(0,0,0,0.02);
    }
    .stat-number {
      font-size: 2.75rem;
      font-weight: 900;
      color: #2563eb;
      margin-bottom: 0.25rem;
    }
    .stat-label {
      font-size: 1.05rem;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 0.5rem;
    }
    .stat-desc {
      font-size: 0.88rem;
      color: #64748b;
      line-height: 1.4;
    }

    /* Resources Grid */
    .resources-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 2rem;
    }
    .resource-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      padding: 2rem;
      display: flex;
      flex-direction: column;
    }
    .resource-type {
      font-size: 0.72rem;
      font-weight: 800;
      color: #2563eb;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }
    .resource-card h3 {
      font-size: 1.25rem;
      font-weight: 700;
      color: #0f172a;
      margin-bottom: 0.5rem;
    }
    .resource-card p {
      font-size: 0.9rem;
      color: #64748b;
      margin-bottom: 1.5rem;
      flex: 1;
    }
    .btn-link {
      background: transparent;
      border: none;
      color: #2563eb;
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
      text-align: left;
      padding: 0;
    }

    /* Pricing Grid */
    .pricing-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 2rem;
      align-items: stretch;
    }
    .pricing-card {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 20px;
      padding: 2.5rem 2rem;
      display: flex;
      flex-direction: column;
      position: relative;
    }
    .pricing-card.popular {
      border: 2px solid #2563eb;
      box-shadow: 0 15px 30px -10px rgba(37,99,235,0.15);
    }
    .popular-tag {
      position: absolute;
      top: -14px;
      left: 50%;
      transform: translateX(-50%);
      background: #2563eb;
      color: #ffffff;
      font-size: 0.7rem;
      font-weight: 800;
      padding: 0.25rem 0.85rem;
      border-radius: 12px;
      letter-spacing: 0.05em;
    }
    .pricing-header h3 {
      font-size: 1.4rem;
      font-weight: 800;
      color: #0f172a;
    }
    .pricing-header p {
      font-size: 0.85rem;
      color: #64748b;
      margin-bottom: 1.25rem;
    }
    .price {
      font-size: 2.5rem;
      font-weight: 900;
      color: #0f172a;
      margin-bottom: 1.5rem;
    }
    .price span {
      font-size: 0.9rem;
      font-weight: 500;
      color: #64748b;
    }
    .pricing-features {
      list-style: none;
      padding-left: 0;
      margin-bottom: 2rem;
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      font-size: 0.9rem;
      color: #334155;
    }
    .btn-pricing {
      width: 100%;
      padding: 0.85rem;
      border-radius: 10px;
      font-weight: 700;
      cursor: pointer;
    }
    .btn-outline {
      background: transparent;
      border: 1px solid #cbd5e1;
      color: #0f172a;
    }
    .btn-outline:hover {
      background: #f8fafc;
      border-color: #94a3b8;
    }

    .landing-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 1.5rem 4rem;
      border-top: 1px solid #e2e8f0;
      background: #ffffff;
    }
    .footer-links {
      display: flex;
      gap: 1.5rem;
    }
    .footer-links a {
      color: #64748b;
      font-size: 0.85rem;
      cursor: pointer;
    }
    .footer-copy {
      font-size: 0.85rem;
      color: #94a3b8;
    }

    @media (max-width: 900px) {
      .landing-hero {
        grid-template-columns: 1fr;
        gap: 2.5rem;
      }
      .top-nav {
        padding: 1rem 1.5rem;
      }
      .nav-links { display: none; }
      .landing-footer {
        padding: 1rem 1.5rem;
        flex-direction: column;
        gap: 0.75rem;
      }
    }
  `]
})
export class LandingLoginComponent {
  @Output() loginSuccess = new EventEmitter<LoginEvent>();

  isRegisterMode: boolean = false;
  name: string = '';
  email: string = '';
  password: string = '';
  rememberMe: boolean = true;
  showPassword: boolean = false;
  isLoading: boolean = false;
  errorMessage: string = '';
  successMessage: string = '';

  constructor(private apiService: ApiService) {}

  toggleMode(mode: 'login' | 'register'): void {
    this.isRegisterMode = mode === 'register';
    this.errorMessage = '';
    this.successMessage = '';
  }

  activateRegisterMode(): void {
    this.isRegisterMode = true;
    this.errorMessage = '';
    this.successMessage = '';
    this.scrollToSection('auth-card');
    setTimeout(() => {
      const input = document.getElementById('name-input');
      if (input) input.focus();
    }, 200);
  }

  scrollToSection(sectionId: string): void {
    const elem = document.getElementById(sectionId);
    if (elem) {
      elem.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else if (sectionId === 'top') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  onFormSubmit(): void {
    this.errorMessage = '';
    this.successMessage = '';

    let finalName = this.name.trim();
    let finalEmail = this.email.trim();
    let finalPassword = this.password.trim();

    if (!finalEmail) {
      finalEmail = 'ana.martinez@empresa.com';
      this.email = finalEmail;
    }

    if (!finalPassword) {
      finalPassword = 'password123';
      this.password = finalPassword;
    }

    if (this.isRegisterMode && !finalName) {
      const parts = finalEmail.split('@');
      finalName = parts[0].replace(/[._-]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      this.name = finalName;
    }

    this.isLoading = true;

    if (this.isRegisterMode) {
      this.apiService.register(finalName || 'Usuario Registrado', finalEmail, finalPassword).subscribe({
        next: (res) => {
          this.isLoading = false;
          this.successMessage = res.message || 'Registro exitoso';
          const token = res.access_token;
          if (token) {
            localStorage.setItem('nuevamente_jwt_token', token);
          }
          setTimeout(() => {
            this.loginSuccess.emit({
              email: res.user?.email || finalEmail,
              name: res.user?.name || finalName,
              token: token
            });
          }, 400);
        },
        error: (err) => {
          this.isLoading = false;
          const detail = err?.error?.detail || 'Error al conectar con el servidor de autenticación.';
          this.errorMessage = detail;
        }
      });
    } else {
      this.apiService.login(finalEmail, finalPassword, finalName).subscribe({
        next: (res) => {
          this.isLoading = false;
          this.successMessage = res.message || 'Inicio de sesión exitoso';
          const token = res.access_token;
          if (token) {
            localStorage.setItem('nuevamente_jwt_token', token);
          }
          setTimeout(() => {
            this.loginSuccess.emit({
              email: res.user?.email || finalEmail,
              name: res.user?.name || finalName,
              token: token
            });
          }, 400);
        },
        error: (err) => {
          this.isLoading = false;
          const detail = err?.error?.detail || 'Credenciales incorrectas o error en el servidor.';
          this.errorMessage = detail;
        }
      });
    }
  }

  onGoogleLogin(): void {
    this.errorMessage = '';
    this.successMessage = '';
    this.isLoading = true;

    const googleName = this.name.trim() || 'Ana Martínez';
    const googleEmail = this.email.trim() || 'ana.martinez@gmail.com';

    this.apiService.googleAuth(googleEmail, googleName).subscribe({
      next: (res) => {
        this.isLoading = false;
        this.successMessage = 'Autenticado con Google exitosamente';
        const token = res.access_token;
        if (token) {
          localStorage.setItem('nuevamente_jwt_token', token);
        }
        setTimeout(() => {
          this.loginSuccess.emit({
            email: res.user?.email || googleEmail,
            name: res.user?.name || googleName,
            token: token
          });
        }, 400);
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = 'Error en autenticación de Google.';
      }
    });
  }
}
