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
  // ── Dashboard shell — all authenticated pages live here ──────────────────
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./layouts/dashboard-layout/dashboard-layout.component').then(
        m => m.DashboardLayoutComponent,
      ),
    children: [
      {
        path: 'home',
        loadComponent: () =>
          import('./pages/home/home.component').then(m => m.HomeComponent),
      },
      {
        path: 'tasks',
        loadComponent: () =>
          import('./pages/my-tasks/my-tasks.component').then(m => m.MyTasksComponent),
      },
      {
        path: 'task/new',
        loadComponent: () =>
          import('./pages/task-create/task-create.component').then(m => m.TaskCreateComponent),
      },
      {
        path: 'task/:id',
        loadComponent: () =>
          import('./pages/task-detail/task-detail.component').then(m => m.TaskDetailComponent),
      },
      {
        path: 'today',
        loadComponent: () =>
          import('./pages/coming-soon/coming-soon.component').then(m => m.ComingSoonComponent),
      },
      {
        path: 'inbox',
        loadComponent: () =>
          import('./pages/coming-soon/coming-soon.component').then(m => m.ComingSoonComponent),
      },
      {
        path: 'projects',
        loadComponent: () =>
          import('./pages/coming-soon/coming-soon.component').then(m => m.ComingSoonComponent),
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('./pages/coming-soon/coming-soon.component').then(m => m.ComingSoonComponent),
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./pages/coming-soon/coming-soon.component').then(m => m.ComingSoonComponent),
      },
    ],
  },
  { path: '**', redirectTo: 'home' },
];
