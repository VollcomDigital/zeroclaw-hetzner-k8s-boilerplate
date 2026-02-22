import { Injectable, signal, computed, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, switchMap, tap, map } from 'rxjs';
import { environment } from '../../../environments/environment';

interface AuthUser {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  role: string;
}

interface AuthResponse {
  success: boolean;
  data: {
    user: AuthUser;
  };
}

interface CsrfTokenResponse {
  success: boolean;
  data: {
    csrfToken: string;
  };
}

interface LoginPayload {
  email: string;
  password: string;
}

interface RegisterPayload extends LoginPayload {
  firstName: string;
  lastName: string;
}

const USER_KEY = 'auth_user';

function isAuthUser(value: unknown): value is AuthUser {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;

  return (
    typeof candidate['id'] === 'string' &&
    typeof candidate['email'] === 'string' &&
    typeof candidate['firstName'] === 'string' &&
    typeof candidate['lastName'] === 'string' &&
    typeof candidate['role'] === 'string'
  );
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly currentUser = signal<AuthUser | null>(this.loadStoredUser());
  private readonly csrfToken = signal<string | null>(null);
  private readonly apiUrl = `${environment.apiUrl}/auth`;
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  readonly user = this.currentUser.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUser() !== null);
  readonly userDisplayName = computed(() => {
    const user = this.currentUser();
    return user ? `${user.firstName} ${user.lastName}` : '';
  });

  constructor() {
    queueMicrotask(() => {
      this.refreshCsrfToken().subscribe({
        next: () => undefined,
        error: () => undefined,
      });
      this.restoreSession();
    });
  }

  login(payload: LoginPayload): Observable<AuthResponse> {
    return this.refreshCsrfToken().pipe(
      switchMap(() => this.http.post<AuthResponse>(`${this.apiUrl}/login`, payload)),
      tap((response) => {
        this.setSession(response.data.user);
      }),
    );
  }

  register(payload: RegisterPayload): Observable<AuthResponse> {
    return this.refreshCsrfToken().pipe(
      switchMap(() => this.http.post<AuthResponse>(`${this.apiUrl}/register`, payload)),
      tap((response) => {
        this.setSession(response.data.user);
      }),
    );
  }

  logout(): void {
    const logoutRequest$ = this.csrfToken()
      ? this.http.post(`${this.apiUrl}/logout`, {})
      : this.refreshCsrfToken().pipe(switchMap(() => this.http.post(`${this.apiUrl}/logout`, {})));

    logoutRequest$.subscribe({
      next: () => undefined,
      error: () => undefined,
    });
    this.clearSession();
    void this.router.navigate(['/auth/login']);
  }

  handleUnauthorized(): void {
    this.clearSession();
    void this.router.navigate(['/auth/login']);
  }

  getCsrfToken(): string | null {
    return this.csrfToken();
  }

  private setSession(user: AuthUser): void {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    this.currentUser.set(user);
  }

  private clearSession(): void {
    localStorage.removeItem(USER_KEY);
    this.currentUser.set(null);
  }

  private refreshCsrfToken(): Observable<string> {
    return this.http.get<CsrfTokenResponse>(`${this.apiUrl}/csrf-token`).pipe(
      tap((response) => {
        this.csrfToken.set(response.data.csrfToken);
      }),
      map((response) => response.data.csrfToken),
    );
  }

  private restoreSession(): void {
    this.http.get<AuthResponse>(`${this.apiUrl}/me`).subscribe({
      next: (response) => {
        this.setSession(response.data.user);
      },
      error: () => {
        this.clearSession();
      },
    });
  }

  private loadStoredUser(): AuthUser | null {
    const stored = localStorage.getItem(USER_KEY);
    if (!stored) return null;

    try {
      const parsed: unknown = JSON.parse(stored);
      if (isAuthUser(parsed)) {
        return parsed;
      }
    } catch {
      // Ignore parse errors and clear invalid persisted state below.
    }

    localStorage.removeItem(USER_KEY);
    return null;
  }
}
