import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const token = authService.getToken();

  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        authService.logout();
      }

      if (error.status === 0) {
        return throwError(() => new Error('Network error. Please check your connection.'));
      }

      const serverMessage =
        (error.error as { error?: { message?: string } })?.error?.message ?? 'An unexpected error occurred';

      return throwError(() => new Error(serverMessage));
    }),
  );
};
