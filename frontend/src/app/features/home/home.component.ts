import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink],
  template: `
    <section class="hero">
      <div class="hero__content">
        <h1 class="hero__title">
          Cloud-Native <span class="hero__accent">MEAN</span> Stack
        </h1>
        <p class="hero__subtitle">
          Production-ready boilerplate with MongoDB, Express, Angular, and Node.js.
          Built with TypeScript, Docker, and 12-Factor methodology.
        </p>
        <div class="hero__actions">
          <a routerLink="/auth/register" class="hero__btn hero__btn--primary">Get Started</a>
          <a href="https://github.com" target="_blank" rel="noopener" class="hero__btn hero__btn--outline">
            View on GitHub
          </a>
        </div>
      </div>

      <div class="features">
        <div class="feature-card">
          <div class="feature-card__icon">M</div>
          <h3 class="feature-card__title">MongoDB</h3>
          <p class="feature-card__desc">Mongoose ODM with schema validation and indexing</p>
        </div>
        <div class="feature-card">
          <div class="feature-card__icon">E</div>
          <h3 class="feature-card__title">Express.js</h3>
          <p class="feature-card__desc">Modular REST API with security middleware</p>
        </div>
        <div class="feature-card">
          <div class="feature-card__icon">A</div>
          <h3 class="feature-card__title">Angular</h3>
          <p class="feature-card__desc">Standalone components, Signals, and lazy routing</p>
        </div>
        <div class="feature-card">
          <div class="feature-card__icon">N</div>
          <h3 class="feature-card__title">Node.js</h3>
          <p class="feature-card__desc">TypeScript, structured logging, health checks</p>
        </div>
      </div>
    </section>
  `,
  styles: [`
    .hero {
      max-width: 1000px;
      margin: 0 auto;
      padding: 4rem 2rem;
    }

    .hero__content {
      text-align: center;
      margin-bottom: 4rem;
    }

    .hero__title {
      font-size: 3rem;
      font-weight: 800;
      color: #fff;
      margin-bottom: 1.5rem;
      letter-spacing: -0.03em;
    }

    .hero__accent {
      color: #e94560;
    }

    .hero__subtitle {
      color: #a5b4c8;
      font-size: 1.15rem;
      line-height: 1.7;
      max-width: 600px;
      margin: 0 auto 2.5rem;
    }

    .hero__actions {
      display: flex;
      gap: 1rem;
      justify-content: center;
    }

    .hero__btn {
      padding: 0.75rem 2rem;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 600;
      text-decoration: none;
      transition: all 0.2s;
    }

    .hero__btn--primary {
      background: #e94560;
      color: #fff;

      &:hover { background: #c73652; }
    }

    .hero__btn--outline {
      border: 2px solid #a5b4c8;
      color: #a5b4c8;

      &:hover {
        border-color: #fff;
        color: #fff;
      }
    }

    .features {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1.5rem;
    }

    .feature-card {
      background: #16213e;
      border-radius: 12px;
      padding: 2rem 1.5rem;
      text-align: center;
      border: 1px solid #1a1a2e;
      transition: transform 0.2s, border-color 0.2s;

      &:hover {
        transform: translateY(-4px);
        border-color: #e94560;
      }
    }

    .feature-card__icon {
      width: 48px;
      height: 48px;
      background: #e94560;
      color: #fff;
      border-radius: 10px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 1.25rem;
      font-weight: 700;
      margin-bottom: 1rem;
    }

    .feature-card__title {
      color: #fff;
      font-size: 1.1rem;
      margin-bottom: 0.5rem;
    }

    .feature-card__desc {
      color: #a5b4c8;
      font-size: 0.9rem;
      line-height: 1.5;
    }
  `],
})
export class HomeComponent {}
