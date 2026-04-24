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
          import('./pages/today/today.component').then(m => m.TodayComponent),
      },
      {
        path: 'inbox',
        loadComponent: () =>
          import('./pages/inbox/inbox.component').then(m => m.InboxComponent),
      },
      {
        path: 'projects',
        loadComponent: () =>
          import('./pages/projects-list/projects-list.component').then(m => m.ProjectsListComponent),
      },
      {
        path: 'projects/:id',
        loadComponent: () =>
          import('./pages/project-detail/project-detail.component').then(m => m.ProjectDetailComponent),
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('./pages/notifications/notifications.component').then(m => m.NotificationsComponent),
      },
      {
        path: 'settings',
        loadComponent: () =>
          import('./pages/settings/settings.component').then(m => m.SettingsComponent),
      },
    ],
  },
  { path: '**', redirectTo: 'home' },
];
