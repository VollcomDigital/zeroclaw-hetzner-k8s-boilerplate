import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/home/home.component').then((m) => m.HomeComponent),
  },
  {
    path: 'auth',
    loadChildren: () => import('./features/auth/auth.routes').then((m) => m.authRoutes),
  },
  {
    path: 'users',
    loadChildren: () => import('./features/users/users.routes').then((m) => m.usersRoutes),
  },
  { path: '**', redirectTo: '' },
];
