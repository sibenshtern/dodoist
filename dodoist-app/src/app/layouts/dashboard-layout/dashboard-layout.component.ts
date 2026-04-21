import { Component, computed, inject, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import { UserService } from '../../services/user.service';
import { AuthService } from '../../services/auth.service';
import { DashboardService, ProjectSummary } from '../../services/dashboard.service';
import { signal } from '@angular/core';
import { switchMap, EMPTY, shareReplay } from 'rxjs';

interface NavItem {
  label: string;
  icon: string;
  path: string;
}

@Component({
  selector: 'app-dashboard-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, TuiIcon],
  templateUrl: './dashboard-layout.component.html',
  styleUrl: './dashboard-layout.component.scss',
})
export class DashboardLayoutComponent implements OnInit {
  private readonly userService = inject(UserService);
  private readonly authService = inject(AuthService);
  private readonly dashboardService = inject(DashboardService);

  readonly navItems: NavItem[] = [
    { label: 'Dashboard',  icon: '@tui.layout-dashboard', path: '/home' },
    { label: 'My Tasks',   icon: '@tui.check-square',     path: '/tasks' },
    { label: 'Today',      icon: '@tui.sun',              path: '/today' },
    { label: 'Inbox',      icon: '@tui.inbox',            path: '/inbox' },
    { label: 'Projects',   icon: '@tui.folder',           path: '/projects' },
  ];

  readonly projects = signal<ProjectSummary[]>([]);

  readonly currentUserName = computed(
    () => this.userService.currentUser()?.display_name ?? '',
  );

  readonly currentUserInitials = computed(() => {
    const name = this.currentUserName().trim();
    if (!name) return '?';
    return name
      .split(' ')
      .map(n => n[0] ?? '')
      .filter(Boolean)
      .join('')
      .toUpperCase()
      .slice(0, 2);
  });

  readonly workspaceName = computed(
    () => this.userService.currentWorkspace()?.name ?? '',
  );

  readonly workspacePlan = computed(() => {
    const plan = this.userService.currentWorkspace()?.plan;
    return plan ? `${plan.charAt(0).toUpperCase()}${plan.slice(1)} plan` : '';
  });

  readonly workspaceInitial = computed(() => {
    const name = this.workspaceName().trim();
    return name ? name[0].toUpperCase() : '';
  });

  ngOnInit(): void {
    if (!this.userService.currentUser()) {
      this.userService.loadCurrentUser().subscribe({ error: console.error });
    }

    if (!this.userService.currentWorkspace()) {
      this.userService.loadWorkspaces().pipe(
        switchMap(workspaces => {
          const ws = workspaces.find(w => w.is_personal) ?? workspaces[0];
          if (!ws) return EMPTY;
          return this.dashboardService.getProjects(ws.slug).pipe(shareReplay(1));
        }),
      ).subscribe({
        next: p => this.projects.set(p),
        error: console.error,
      });
    } else {
      const ws = this.userService.currentWorkspace()!;
      this.dashboardService.getProjects(ws.slug).subscribe({
        next: p => this.projects.set(p),
        error: console.error,
      });
    }
  }

  logout(): void {
    this.authService.logout();
  }
}
