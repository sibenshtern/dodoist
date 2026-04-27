import { Component, computed, HostListener, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import { interval, Subscription, switchMap, EMPTY } from 'rxjs';
import { UserService } from '../../services/user.service';
import { AuthService } from '../../services/auth.service';
import { DashboardService, ProjectSummary } from '../../services/dashboard.service';
import { NotificationsService } from '../../services/notifications.service';
import { SearchPaletteComponent } from '../../shared/search-palette/search-palette.component';

interface NavItem {
  label: string;
  icon: string;
  path: string;
}

@Component({
  selector: 'app-dashboard-layout',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, TuiIcon, SearchPaletteComponent],
  templateUrl: './dashboard-layout.component.html',
  styleUrl: './dashboard-layout.component.scss',
})
export class DashboardLayoutComponent implements OnInit, OnDestroy {
  private readonly userService = inject(UserService);
  private readonly authService = inject(AuthService);
  private readonly dashboardService = inject(DashboardService);
  readonly notifService = inject(NotificationsService);

  private pollSub?: Subscription;

  readonly navItems: NavItem[] = [
    { label: 'Dashboard',  icon: '@tui.layout-dashboard', path: '/home' },
    { label: 'My Tasks',   icon: '@tui.check-square',     path: '/tasks' },
    { label: 'Today',      icon: '@tui.sun',              path: '/today' },
    { label: 'Inbox',      icon: '@tui.inbox',            path: '/inbox' },
    { label: 'Projects',   icon: '@tui.folder',           path: '/projects' },
  ];

  readonly projects = signal<ProjectSummary[]>([]);
  readonly searchOpen = signal(false);

  @HostListener('document:keydown', ['$event'])
  onGlobalKeydown(event: KeyboardEvent): void {
    const isK = event.key === 'k' || event.key === 'K';
    if ((event.metaKey || event.ctrlKey) && isK) {
      event.preventDefault();
      this.searchOpen.update(v => !v);
    }
  }

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

    this.userService.loadWorkspaces().pipe(
      switchMap(workspaces => {
        if (workspaces.length === 0) return EMPTY;
        return this.dashboardService.getAllProjects(workspaces.map(w => w.slug));
      }),
    ).subscribe({
      next: p => this.projects.set(p),
      error: console.error,
    });

    // Initial load + 60-second polling for notifications
    this.notifService.list({ limit: 50 }).subscribe({ error: console.error });
    this.pollSub = interval(60_000).subscribe(() => {
      this.notifService.list({ limit: 50 }).subscribe({ error: console.error });
    });
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }

  logout(): void {
    this.authService.logout();
  }
}
