import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { LoadingComponent } from '../../../shared/components/loading/loading.component';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [FormsModule, RouterLink, LoadingComponent],
  template: `
    <div class="auth-page">
      <div class="auth-card">
        <h2 class="auth-card__title">Create Account</h2>
        <p class="auth-card__subtitle">Sign up to get started</p>

        @if (error()) {
          <div class="auth-card__error">{{ error() }}</div>
        }

        @if (loading()) {
          <app-loading message="Creating account..." />
        } @else {
          <form (ngSubmit)="onSubmit()" class="auth-form">
            <div class="form-row">
              <div class="form-group">
                <label for="firstName" class="form-label">First Name</label>
                <input
                  id="firstName"
                  type="text"
                  [(ngModel)]="firstName"
                  name="firstName"
                  class="form-input"
                  placeholder="John"
                  required
                />
              </div>
              <div class="form-group">
                <label for="lastName" class="form-label">Last Name</label>
                <input
                  id="lastName"
                  type="text"
                  [(ngModel)]="lastName"
                  name="lastName"
                  class="form-input"
                  placeholder="Doe"
                  required
                />
              </div>
            </div>

            <div class="form-group">
              <label for="email" class="form-label">Email</label>
              <input
                id="email"
                type="email"
                [(ngModel)]="email"
                name="email"
                class="form-input"
                placeholder="you&#64;example.com"
                required
              />
            </div>

            <div class="form-group">
              <label for="password" class="form-label">Password</label>
              <input
                id="password"
                type="password"
                [(ngModel)]="password"
                name="password"
                class="form-input"
                placeholder="Min 8 characters"
                required
                minlength="8"
              />
            </div>

            <button type="submit" class="auth-btn" [disabled]="!isFormValid()">
              Create Account
            </button>
          </form>
        }

        <p class="auth-card__footer">
          Already have an account?
          <a routerLink="/auth/login" class="auth-card__link">Sign In</a>
        </p>
      </div>
    </div>
  `,
  styles: [`
    .auth-page {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: calc(100vh - 128px);
      padding: 2rem;
    }

    .auth-card {
      background: #16213e;
      border-radius: 16px;
      padding: 2.5rem;
      width: 100%;
      max-width: 480px;
      border: 1px solid #1a1a2e;
    }

    .auth-card__title {
      color: #fff;
      font-size: 1.5rem;
      font-weight: 700;
      margin-bottom: 0.25rem;
    }

    .auth-card__subtitle {
      color: #a5b4c8;
      margin-bottom: 2rem;
      font-size: 0.9rem;
    }

    .auth-card__error {
      background: rgba(233, 69, 96, 0.1);
      border: 1px solid #e94560;
      color: #e94560;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      margin-bottom: 1.5rem;
      font-size: 0.85rem;
    }

    .auth-form {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .form-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }

    .form-group {
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }

    .form-label {
      color: #a5b4c8;
      font-size: 0.85rem;
      font-weight: 500;
    }

    .form-input {
      background: #0f3460;
      border: 1px solid #1a1a2e;
      color: #fff;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      font-size: 0.9rem;
      outline: none;
      transition: border-color 0.2s;

      &:focus { border-color: #e94560; }
      &::placeholder { color: #4a5568; }
    }

    .auth-btn {
      background: #e94560;
      color: #fff;
      border: none;
      padding: 0.75rem;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s;
      margin-top: 0.5rem;

      &:hover:not(:disabled) { background: #c73652; }
      &:disabled { opacity: 0.5; cursor: not-allowed; }
    }

    .auth-card__footer {
      text-align: center;
      color: #a5b4c8;
      font-size: 0.85rem;
      margin-top: 1.5rem;
    }

    .auth-card__link {
      color: #e94560;
      text-decoration: none;
      font-weight: 600;

      &:hover { text-decoration: underline; }
    }
  `],
})
export class RegisterComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  firstName = '';
  lastName = '';
  email = '';
  password = '';
  loading = signal(false);
  error = signal('');

  isFormValid(): boolean {
    return !!(this.firstName && this.lastName && this.email && this.password.length >= 8);
  }

  onSubmit(): void {
    this.loading.set(true);
    this.error.set('');

    this.authService
      .register({
        firstName: this.firstName,
        lastName: this.lastName,
        email: this.email,
        password: this.password,
      })
      .subscribe({
        next: () => {
          this.loading.set(false);
          void this.router.navigate(['/dashboard']);
        },
        error: (err: Error) => {
          this.loading.set(false);
          this.error.set(err.message);
        },
      });
  }
}
