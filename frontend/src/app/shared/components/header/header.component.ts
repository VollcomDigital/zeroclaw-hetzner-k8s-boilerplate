import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <header class="header">
      <nav class="header__nav">
        <a routerLink="/" class="header__brand">MEAN Boilerplate</a>

        <div class="header__links">
          @if (authService.isAuthenticated()) {
            <a routerLink="/dashboard" routerLinkActive="active" class="header__link">
              Dashboard
            </a>
            <span class="header__user">{{ authService.userDisplayName() }}</span>
            <button (click)="authService.logout()" class="header__btn header__btn--logout">
              Logout
            </button>
          } @else {
            <a routerLink="/auth/login" routerLinkActive="active" class="header__link">
              Login
            </a>
            <a routerLink="/auth/register" routerLinkActive="active" class="header__btn header__btn--primary">
              Register
            </a>
          }
        </div>
      </nav>
    </header>
  `,
  styles: [`
    .header {
      background: #1a1a2e;
      padding: 0 2rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    .header__nav {
      max-width: 1200px;
      margin: 0 auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 64px;
    }

    .header__brand {
      color: #e94560;
      font-size: 1.25rem;
      font-weight: 700;
      text-decoration: none;
      letter-spacing: -0.025em;
    }

    .header__links {
      display: flex;
      align-items: center;
      gap: 1.5rem;
    }

    .header__link {
      color: #a5b4c8;
      text-decoration: none;
      font-size: 0.9rem;
      transition: color 0.2s;

      &:hover, &.active {
        color: #fff;
      }
    }

    .header__user {
      color: #a5b4c8;
      font-size: 0.85rem;
    }

    .header__btn {
      padding: 0.5rem 1.25rem;
      border-radius: 6px;
      font-size: 0.9rem;
      cursor: pointer;
      border: none;
      transition: all 0.2s;
    }

    .header__btn--primary {
      background: #e94560;
      color: #fff;
      text-decoration: none;

      &:hover {
        background: #c73652;
      }
    }

    .header__btn--logout {
      background: transparent;
      color: #a5b4c8;
      border: 1px solid #a5b4c8;

      &:hover {
        color: #fff;
        border-color: #fff;
      }
    }
  `],
})
export class HeaderComponent {
  readonly authService = inject(AuthService);
}
