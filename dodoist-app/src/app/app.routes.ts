import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./pages/landing/landing.component').then(m => m.LandingComponent),
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./pages/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'signup',
    loadComponent: () =>
      import('./pages/signup/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'docs',
    loadComponent: () =>
      import('./pages/docs/docs.component').then(m => m.DocsComponent),
  },
  {
    path: 'task/new',
    loadComponent: () =>
      import('./pages/task-create/task-create.component').then(m => m.TaskCreateComponent),
  },
  { path: '**', redirectTo: '' },
];
