import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import {
  DashboardService,
  DashboardStats,
  TodayTask,
  ProjectSummary,
  ActivityItem,
  SprintProgress,
} from '../../services/dashboard.service';

interface NavItem {
  label: string;
  icon: string;
  path: string;
}

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [DatePipe, RouterLink, TuiIcon],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent implements OnInit {
  private readonly dashboardService = inject(DashboardService);

  readonly today = new Date();

  readonly navItems: NavItem[] = [
    { label: 'Dashboard', icon: '@tui.layout-dashboard', path: '/home' },
    { label: 'My Tasks', icon: '@tui.check-square', path: '/tasks' },
    { label: 'Today', icon: '@tui.sun', path: '/today' },
    { label: 'Inbox', icon: '@tui.inbox', path: '/inbox' },
  ];

  readonly activeNav = signal<string>('/home');

  // TODO: Replace with actual authenticated user data from GET /api/users/me
  // once a user profile endpoint is implemented. The User model in users/models.py
  // has fields: display_name, email, avatar_url, timezone.
  readonly currentUserName = signal<string>('Alice Johnson');

  // TODO: Replace with actual workspace data from GET /api/workspaces/
  readonly workspaceName = signal<string>('Acme Corp');
  readonly workspacePlan = signal<string>('Pro workspace');

  readonly stats = signal<DashboardStats | null>(null);
  readonly todayTasks = signal<TodayTask[]>([]);
  readonly projects = signal<ProjectSummary[]>([]);
  readonly activity = signal<ActivityItem[]>([]);
  readonly activeSprint = signal<SprintProgress | null>(null);

  readonly greeting = computed(() => {
    const hour = this.today.getHours();
    const firstName = this.currentUserName().split(' ')[0];
    if (hour < 12) return `Good morning, ${firstName} 👋`;
    if (hour < 18) return `Good afternoon, ${firstName} 👋`;
    return `Good evening, ${firstName} 👋`;
  });

  readonly currentUserInitials = computed(() =>
    this.currentUserName()
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  );

  readonly sprintProgressPct = computed(() => {
    const sprint = this.activeSprint();
    if (!sprint || sprint.storyPointsTotal === 0) return 0;
    return Math.round((sprint.storyPointsDone / sprint.storyPointsTotal) * 100);
  });

  readonly todayDueCount = computed(() =>
    this.todayTasks().filter(t => t.dueLabel === 'Today' && !t.done).length
  );

  ngOnInit(): void {
    this.dashboardService.getStats().subscribe(s => this.stats.set(s));
    this.dashboardService.getTodayTasks().subscribe(t => this.todayTasks.set(t));
    this.dashboardService.getProjects().subscribe(p => this.projects.set(p));
    this.dashboardService.getActivity().subscribe(a => this.activity.set(a));
    this.dashboardService.getActiveSprint().subscribe(s => this.activeSprint.set(s));
  }

  toggleTask(taskId: string): void {
    this.todayTasks.update(tasks =>
      tasks.map(t => (t.id === taskId ? { ...t, done: !t.done } : t))
    );
  }

  initials(name: string): string {
    return name
      .split(' ')
      .map(n => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }
}
