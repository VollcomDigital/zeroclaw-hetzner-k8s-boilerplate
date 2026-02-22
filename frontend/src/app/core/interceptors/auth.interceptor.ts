import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authService = inject(AuthService);
  const authReq = req.clone({ withCredentials: true });

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      const isSessionBootstrapRequest = authReq.url.endsWith('/auth/me');
      const isAuthCredentialRequest =
        authReq.url.endsWith('/auth/login') || authReq.url.endsWith('/auth/register');

      if (error.status === 401 && !isSessionBootstrapRequest && !isAuthCredentialRequest) {
        authService.handleUnauthorized();
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
