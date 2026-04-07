import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';
import { publicGuard } from './guards/public.guard';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () =>
      import('./pages/landing/landing.component').then(m => m.LandingComponent),
  },
  {
    path: 'login',
    canActivate: [publicGuard],
    loadComponent: () =>
      import('./pages/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'signup',
    canActivate: [publicGuard],
    loadComponent: () =>
      import('./pages/signup/signup.component').then(m => m.SignupComponent),
  },
  {
    path: 'docs',
    loadComponent: () =>
      import('./pages/docs/docs.component').then(m => m.DocsComponent),
  },
  {
    path: 'home',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/home/home.component').then(m => m.HomeComponent),
  },
  {
    path: 'tasks',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/my-tasks/my-tasks.component').then(m => m.MyTasksComponent),
  },
  {
    path: 'task/new',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/task-create/task-create.component').then(m => m.TaskCreateComponent),
  },
  // Placeholder routes — prevent silent redirects to landing page
  {
    path: 'today',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/coming-soon/coming-soon.component').then(m => m.ComingSoonComponent),
  },
  {
    path: 'inbox',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/coming-soon/coming-soon.component').then(m => m.ComingSoonComponent),
  },
  {
    path: 'projects',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./pages/coming-soon/coming-soon.component').then(m => m.ComingSoonComponent),
  },
  { path: '**', redirectTo: 'home' },
];
