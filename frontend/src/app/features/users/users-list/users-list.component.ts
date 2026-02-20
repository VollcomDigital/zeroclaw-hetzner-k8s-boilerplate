import { Component, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

interface User {
  _id: string;
  email: string;
  name: string;
}

@Component({
  selector: 'app-users-list',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="users">
      <h2>Users</h2>
      @if (loading()) {
        <p>Loading...</p>
      } @else if (error()) {
        <p class="error">{{ error() }}</p>
      } @else {
        <ul>
          @for (user of users(); track user._id) {
            <li>{{ user.name }} — {{ user.email }}</li>
          }
        </ul>
      }
      <a routerLink="/">Back to Home</a>
    </div>
  `,
  styles: [
    `
      .users {
        padding: 2rem;
      }
      .error {
        color: #c00;
      }
      ul {
        list-style: none;
        padding: 0;
      }
      li {
        padding: 0.5rem 0;
      }
      a {
        color: #0066cc;
      }
    `,
  ],
})
export class UsersListComponent implements OnInit {
  users = signal<User[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);

  constructor(private readonly api: ApiService) {}

  ngOnInit(): void {
    this.api.get<User[]>('/users').subscribe({
      next: (res) => {
        this.loading.set(false);
        if (res.success && res.data) this.users.set(res.data);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.message ?? 'Failed to load users');
      },
    });
  }
}
