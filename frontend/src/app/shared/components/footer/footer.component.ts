import { Component } from '@angular/core';

@Component({
  selector: 'app-footer',
  standalone: true,
  template: `
    <footer class="footer">
      <p>&copy; {{ currentYear }} MEAN Boilerplate. Cloud-Native Starter Template.</p>
    </footer>
  `,
  styles: [`
    .footer {
      background: #1a1a2e;
      color: #a5b4c8;
      text-align: center;
      padding: 1.5rem;
      font-size: 0.85rem;
      margin-top: auto;
    }
  `],
})
export class FooterComponent {
  readonly currentYear = new Date().getFullYear();
}
