import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import { DashboardService, TodayTask } from '../../services/dashboard.service';
import { TaskService } from '../../services/task.service';

@Component({
  selector: 'app-today',
  standalone: true,
  imports: [TuiIcon, RouterLink],
  templateUrl: './today.component.html',
  styleUrl: './today.component.scss',
})
export class TodayComponent implements OnInit {
  private readonly dashboardService = inject(DashboardService);
  private readonly taskService = inject(TaskService);

  readonly tasks = signal<TodayTask[]>([]);
  readonly isLoading = signal(true);

  readonly overdueGroup = computed(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    return this.tasks().filter(t => {
      if (!t.dueDate) return false;
      return new Date(t.dueDate) < now;
    });
  });

  readonly todayGroup = computed(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return this.tasks().filter(t => {
      if (!t.dueDate) return false;
      const d = new Date(t.dueDate);
      return d >= now && d < tomorrow;
    });
  });

  readonly upcomingGroup = computed(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const tomorrow = new Date(now);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return this.tasks().filter(t => {
      if (!t.dueDate) return false;
      return new Date(t.dueDate) >= tomorrow;
    });
  });

  readonly totalCount = computed(() => this.tasks().length);
  readonly doneCount = computed(() => this.tasks().filter(t => t.done).length);

  ngOnInit(): void {
    this.dashboardService.getTodayTasks().subscribe({
      next: tasks => {
        this.tasks.set(tasks);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  toggle(task: TodayTask): void {
    const newStatus = task.done ? 'todo' : 'done';
    this.tasks.update(list =>
      list.map(t => (t.id === task.id ? { ...t, done: !t.done } : t)),
    );
    this.taskService.updateTask(task.id, { status: newStatus }).subscribe({
      error: () => {
        this.tasks.update(list =>
          list.map(t => (t.id === task.id ? { ...t, done: task.done } : t)),
        );
      },
    });
  }
}
