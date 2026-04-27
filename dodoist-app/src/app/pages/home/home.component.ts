import { Component, computed, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import { toObservable } from '@angular/core/rxjs-interop';
import { filter, forkJoin, Subscription, switchMap } from 'rxjs';
import {
  ActivityItem,
  DashboardService,
  DashboardStats,
  ProjectSummary,
  SprintProgress,
  TodayTask,
} from '../../services/dashboard.service';
import { UserService } from '../../services/user.service';
import { TaskService } from '../../services/task.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [DatePipe, RouterLink, TuiIcon],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent implements OnInit, OnDestroy {
  private readonly dashboardService = inject(DashboardService);
  private readonly userService = inject(UserService);
  private readonly taskService = inject(TaskService);

  private readonly workspace$ = toObservable(this.userService.currentWorkspace);
  private sub?: Subscription;

  readonly today = new Date();
  readonly isLoading = signal(false);

  readonly currentUserName = computed(
    () => this.userService.currentUser()?.display_name ?? '',
  );

  readonly stats = signal<DashboardStats | null>(null);
  readonly todayTasks = signal<TodayTask[]>([]);
  readonly projects = signal<ProjectSummary[]>([]);
  readonly activity = signal<ActivityItem[]>([]);
  readonly activeSprint = signal<SprintProgress | null>(null);
  readonly loadError = signal<string | null>(null);

  readonly greeting = computed(() => {
    const hour = this.today.getHours();
    const firstName = this.currentUserName().split(' ')[0] || 'there';
    if (hour < 12) return `Good morning, ${firstName} 👋`;
    if (hour < 18) return `Good afternoon, ${firstName} 👋`;
    return `Good evening, ${firstName} 👋`;
  });

  readonly sprintProgressPct = computed(() => {
    const sprint = this.activeSprint();
    if (!sprint || sprint.storyPointsTotal === 0) return 0;
    return Math.round((sprint.storyPointsDone / sprint.storyPointsTotal) * 100);
  });

  readonly todayDueCount = computed(() =>
    this.todayTasks().filter(t => t.dueLabel === 'Today' && !t.done).length,
  );

  ngOnInit(): void {
    this.sub = this.workspace$.pipe(
      filter(Boolean),
      switchMap(ws => {
        this.isLoading.set(true);
        this.loadError.set(null);
        return forkJoin({
          stats: this.dashboardService.getStats(),
          todayTasks: this.dashboardService.getTodayTasks(),
          projects: this.dashboardService.getProjectsForActiveWorkspace(ws.slug),
          activity: this.dashboardService.getActivity(),
        });
      }),
    ).subscribe({
      next: ({ stats, todayTasks, projects, activity }) => {
        this.stats.set(stats);
        this.todayTasks.set(todayTasks);
        this.projects.set(projects);
        this.activity.set(activity);
        this.isLoading.set(false);

        const first = projects[0];
        if (first) {
          this.dashboardService.getActiveSprint(first.id).subscribe({
            next: sprint => this.activeSprint.set(sprint),
            error: () => this.activeSprint.set(null),
          });
        } else {
          this.activeSprint.set(null);
        }
      },
      error: (err: unknown) => {
        console.error('Dashboard load error', err);
        this.loadError.set('Failed to load dashboard data. Please refresh.');
        this.isLoading.set(false);
      },
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  toggleTask(taskId: string): void {
    const task = this.todayTasks().find(t => t.id === taskId);
    if (!task) return;

    const newDone = !task.done;
    this.todayTasks.update(tasks =>
      tasks.map(t => (t.id === taskId ? { ...t, done: newDone } : t)),
    );

    this.taskService.updateTask(taskId, { status: newDone ? 'done' : 'todo' }).subscribe({
      error: () => {
        this.todayTasks.update(tasks =>
          tasks.map(t => (t.id === taskId ? { ...t, done: task.done } : t)),
        );
      },
    });
  }

  initials(name: string): string {
    if (!name.trim()) return '?';
    return name
      .split(' ')
      .map(n => n[0] ?? '')
      .filter(Boolean)
      .join('')
      .toUpperCase()
      .slice(0, 2);
  }
}
