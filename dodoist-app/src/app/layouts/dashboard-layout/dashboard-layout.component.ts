import { Component, computed, HostListener, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import { Subscription, switchMap, EMPTY, toObservable } from 'rxjs';
import { UserService } from '../../services/user.service';
import { AuthService } from '../../services/auth.service';
import { DashboardService, ProjectSummary } from '../../services/dashboard.service';
import { NotificationsService } from '../../services/notifications.service';
import { SseService } from '../../services/sse.service';
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
  readonly userService = inject(UserService);
  private readonly authService = inject(AuthService);
  private readonly dashboardService = inject(DashboardService);
  readonly notifService = inject(NotificationsService);
  private readonly sseService = inject(SseService);

  private projectSub?: Subscription;

  readonly navItems: NavItem[] = [
    { label: 'Dashboard',  icon: '@tui.layout-dashboard', path: '/home' },
    { label: 'My Tasks',   icon: '@tui.check-square',     path: '/tasks' },
    { label: 'Today',      icon: '@tui.sun',              path: '/today' },
    { label: 'Inbox',      icon: '@tui.inbox',            path: '/inbox' },
    { label: 'Projects',   icon: '@tui.folder',           path: '/projects' },
  ];

  readonly projects = signal<ProjectSummary[]>([]);
  readonly searchOpen = signal(false);
  readonly wsDropdownOpen = signal(false);
  readonly isSwitching = signal(false);

  readonly workspaceList = computed(() => this.userService.workspaces());
  private readonly router = inject(Router);

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

    // Load workspaces; then reactively refetch projects whenever the active workspace changes.
    this.projectSub = this.userService.loadWorkspaces().pipe(
      switchMap(() => toObservable(this.userService.currentWorkspace)),
      switchMap(ws => {
        if (!ws) return EMPTY;
        return this.dashboardService.getProjectsForActiveWorkspace(ws.slug);
      }),
    ).subscribe({
      next: p => this.projects.set(p),
      error: console.error,
    });

    // Initial notification load; subsequent updates come through SSE.
    this.notifService.list({ limit: 50 }).subscribe({ error: console.error });
    this.sseService.start();
  }

  ngOnDestroy(): void {
    this.projectSub?.unsubscribe();
    this.sseService.stop();
  }

  switchWorkspace(ws: import('../../services/user.service').Workspace): void {
    if (this.isSwitching()) return;
    this.isSwitching.set(true);
    this.userService.switchWorkspace(ws).subscribe({
      next: () => {
        this.wsDropdownOpen.set(false);
        this.isSwitching.set(false);
        this.router.navigate(['/home']);
      },
      error: () => this.isSwitching.set(false),
    });
  }

  logout(): void {
    this.authService.logout();
  }
}
