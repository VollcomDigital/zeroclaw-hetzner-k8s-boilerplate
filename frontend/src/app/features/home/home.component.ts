import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="home">
      <h1>Cloud-Native MEAN Boilerplate</h1>
      <p>MongoDB · Express · Angular · Node.js</p>
      <p>12-Factor App · TypeScript Strict · Standalone Components</p>
    </div>
  `,
  styles: [
    `
      .home {
        text-align: center;
        padding: 3rem;
      }
      h1 {
        font-size: 2rem;
        margin-bottom: 1rem;
      }
      p {
        color: #666;
        margin: 0.5rem 0;
      }
    `,
  ],
})
export class HomeComponent {}
