import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="login">
      <h2>Login</h2>
      <p>Auth stub — integrate JWT/bcrypt in production.</p>
      <a routerLink="/">Back to Home</a>
    </div>
  `,
  styles: [
    `
      .login {
        padding: 2rem;
      }
      h2 {
        margin-bottom: 1rem;
      }
      a {
        color: #0066cc;
      }
    `,
  ],
})
export class LoginComponent {
  loading = signal(false);
}
