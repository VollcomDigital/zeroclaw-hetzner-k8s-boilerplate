import { Component } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  template: `
    <div class="app-shell">
      <header class="header">
        <nav>
          <a routerLink="/">Home</a>
          <a routerLink="/auth">Auth</a>
          <a routerLink="/users">Users</a>
        </nav>
      </header>
      <main class="main">
        <router-outlet />
      </main>
    </div>
  `,
  styles: [
    `
      .app-shell {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
      }
      .header {
        padding: 1rem 2rem;
        background: #1a1a2e;
        color: #eee;
      }
      .header nav {
        display: flex;
        gap: 1.5rem;
      }
      .header a {
        color: #eee;
        text-decoration: none;
      }
      .header a:hover {
        text-decoration: underline;
      }
      .main {
        flex: 1;
        padding: 2rem;
      }
    `,
  ],
})
export class AppComponent {}
