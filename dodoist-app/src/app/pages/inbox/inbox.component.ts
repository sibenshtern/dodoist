import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TitleCasePipe, SlicePipe } from '@angular/common';
import { TuiIcon } from '@taiga-ui/core';
import { TaskService, Task } from '../../services/task.service';
import { UserService } from '../../services/user.service';
import { ProjectsService, Project } from '../../services/projects.service';
import { switchMap, EMPTY } from 'rxjs';

const PRIORITY_COLORS: Record<string, string> = {
  urgent: '#db4035',
  high:   '#e88c30',
  medium: '#4a90d9',
  low:    '#8a8680',
  none:   '#b0aea9',
};

@Component({
  selector: 'app-inbox',
  standalone: true,
  imports: [TuiIcon, RouterLink, TitleCasePipe, SlicePipe],
  templateUrl: './inbox.component.html',
  styleUrl: './inbox.component.scss',
})
export class InboxComponent implements OnInit {
  private readonly taskService = inject(TaskService);
  private readonly userService = inject(UserService);
  private readonly projectsService = inject(ProjectsService);

  readonly allTasks = signal<Task[]>([]);
  readonly projects = signal<Project[]>([]);
  readonly isLoading = signal(true);

  readonly statusFilter = signal<string>('');
  readonly priorityFilter = signal<string>('');

  readonly filteredTasks = computed(() => {
    let tasks = this.allTasks();
    const status = this.statusFilter();
    const priority = this.priorityFilter();
    if (status) tasks = tasks.filter(t => t.status === status);
    if (priority) tasks = tasks.filter(t => t.priority === priority);
    return tasks;
  });

  readonly groupedByProject = computed(() => {
    const projectMap = new Map(this.projects().map(p => [p.id, p.name]));
    const groups = new Map<string, { name: string; tasks: Task[] }>();
    for (const task of this.filteredTasks()) {
      const projectId = task.project;
      if (!groups.has(projectId)) {
        groups.set(projectId, {
          name: projectMap.get(projectId) ?? 'Unknown project',
          tasks: [],
        });
      }
      groups.get(projectId)!.tasks.push(task);
    }
    return [...groups.values()];
  });

  readonly totalCount = computed(() => this.filteredTasks().length);

  ngOnInit(): void {
    const ws = this.userService.currentWorkspace();
    const load$ = ws
      ? this.projectsService.list(ws.slug)
      : this.userService.loadWorkspaces().pipe(
          switchMap(workspaces => {
            const w = workspaces.find(x => x.is_personal) ?? workspaces[0];
            return w ? this.projectsService.list(w.slug) : EMPTY;
          }),
        );

    load$.subscribe({
      next: projects => this.projects.set(projects),
      error: console.error,
    });

    this.taskService.getMyTasks().subscribe({
      next: tasks => {
        this.allTasks.set(tasks);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  priorityColor(priority: string): string {
    return PRIORITY_COLORS[priority] ?? PRIORITY_COLORS['none'];
  }

  setStatus(value: string): void {
    this.statusFilter.set(this.statusFilter() === value ? '' : value);
  }

  setPriority(value: string): void {
    this.priorityFilter.set(this.priorityFilter() === value ? '' : value);
  }

  clearFilters(): void {
    this.statusFilter.set('');
    this.priorityFilter.set('');
  }

  hasFilters(): boolean {
    return !!(this.statusFilter() || this.priorityFilter());
  }
}
