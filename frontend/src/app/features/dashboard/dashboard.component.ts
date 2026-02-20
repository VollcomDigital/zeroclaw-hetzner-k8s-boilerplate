import { Component, inject } from '@angular/core';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  template: `
    <div class="dashboard">
      <div class="dashboard__header">
        <h1 class="dashboard__title">Dashboard</h1>
        <p class="dashboard__welcome">Welcome back, {{ authService.userDisplayName() }}</p>
      </div>

      <div class="dashboard__grid">
        <div class="stat-card">
          <h3 class="stat-card__label">Status</h3>
          <p class="stat-card__value stat-card__value--success">Active</p>
        </div>
        <div class="stat-card">
          <h3 class="stat-card__label">Role</h3>
          <p class="stat-card__value">{{ authService.user()?.role ?? 'N/A' }}</p>
        </div>
        <div class="stat-card">
          <h3 class="stat-card__label">Email</h3>
          <p class="stat-card__value">{{ authService.user()?.email ?? 'N/A' }}</p>
        </div>
        <div class="stat-card">
          <h3 class="stat-card__label">Stack</h3>
          <p class="stat-card__value">MEAN + TS</p>
        </div>
      </div>

      <div class="dashboard__info">
        <h2>Getting Started</h2>
        <ul>
          <li>Customize the backend modules in <code>backend/src/modules/</code></li>
          <li>Add feature components in <code>frontend/src/app/features/</code></li>
          <li>Configure environment variables via <code>.env</code> files</li>
          <li>Run <code>docker compose up</code> for the full stack</li>
        </ul>
      </div>
    </div>
  `,
  styles: [`
    .dashboard {
      max-width: 1000px;
      margin: 0 auto;
      padding: 2rem;
    }

    .dashboard__header {
      margin-bottom: 2rem;
    }

    .dashboard__title {
      color: #fff;
      font-size: 2rem;
      font-weight: 700;
    }

    .dashboard__welcome {
      color: #a5b4c8;
      margin-top: 0.25rem;
    }

    .dashboard__grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2.5rem;
    }

    .stat-card {
      background: #16213e;
      border-radius: 12px;
      padding: 1.5rem;
      border: 1px solid #1a1a2e;
    }

    .stat-card__label {
      color: #a5b4c8;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }

    .stat-card__value {
      color: #fff;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .stat-card__value--success {
      color: #4ade80;
    }

    .dashboard__info {
      background: #16213e;
      border-radius: 12px;
      padding: 2rem;
      border: 1px solid #1a1a2e;

      h2 {
        color: #fff;
        font-size: 1.25rem;
        margin-bottom: 1rem;
      }

      ul {
        list-style: none;
        padding: 0;

        li {
          color: #a5b4c8;
          padding: 0.5rem 0;
          padding-left: 1.5rem;
          position: relative;
          font-size: 0.9rem;

          &::before {
            content: '→';
            position: absolute;
            left: 0;
            color: #e94560;
          }
        }
      }

      code {
        background: #0f3460;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        font-size: 0.85rem;
        color: #e94560;
      }
    }
  `],
})
export class DashboardComponent {
  readonly authService = inject(AuthService);
}
