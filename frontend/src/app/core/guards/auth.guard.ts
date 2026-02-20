import { inject } from '@angular/core';
import { Router } from '@angular/router';

export const authGuard = () => {
  const router = inject(Router);
  const token = localStorage.getItem('auth_token');
  if (token) return true;
  router.navigate(['/auth']);
  return false;
};
