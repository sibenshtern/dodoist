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
import { UserService } from '../../services/user.service';
import { TaskService } from '../../services/task.service';
import { switchMap, of, EMPTY, shareReplay } from 'rxjs';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [DatePipe, RouterLink, TuiIcon],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent implements OnInit {
  private readonly dashboardService = inject(DashboardService);
  private readonly userService = inject(UserService);
  private readonly taskService = inject(TaskService);

  readonly today = new Date();

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
    const errorHandler = (err: unknown) => {
      console.error('Dashboard load error', err);
      this.loadError.set('Failed to load some dashboard data. Please refresh.');
    };

    this.userService.loadWorkspaces().pipe(
      switchMap(workspaces => {
        const ws = workspaces.find(w => w.is_personal) ?? workspaces[0];
        if (!ws) return EMPTY;

        const projects$ = this.dashboardService.getProjects(ws.slug).pipe(shareReplay(1));

        projects$.subscribe({
          next: p => this.projects.set(p),
          error: errorHandler,
        });

        projects$.pipe(
          switchMap(projects => {
            const first = projects[0];
            return first ? this.dashboardService.getActiveSprint(first.id) : of(null);
          }),
        ).subscribe({
          next: sprint => this.activeSprint.set(sprint),
          error: errorHandler,
        });

        return EMPTY;
      }),
    ).subscribe({ error: errorHandler });

    this.dashboardService.getStats().subscribe({ next: s => this.stats.set(s), error: errorHandler });
    this.dashboardService.getTodayTasks().subscribe({ next: t => this.todayTasks.set(t), error: errorHandler });
    this.dashboardService.getActivity().subscribe({ next: a => this.activity.set(a), error: errorHandler });
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
