import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import { ProjectsService, Project } from '../../services/projects.service';
import { TaskService, Task } from '../../services/task.service';

const STATUS_COLUMNS = [
  { key: 'backlog',     label: 'Backlog',     color: '#94a3b8' },
  { key: 'todo',        label: 'To Do',       color: '#64748b' },
  { key: 'in_progress', label: 'In Progress', color: '#246fe0' },
  { key: 'in_review',   label: 'In Review',   color: '#ff9800' },
  { key: 'done',        label: 'Done',        color: '#299438' },
];

@Component({
  selector: 'app-project-board',
  standalone: true,
  imports: [RouterLink, TuiIcon],
  template: `
    <div class="board-page">
      <header class="board-header">
        <a [routerLink]="['/projects', projectId()]" class="back-link">
          <tui-icon icon="@tui.arrow-left" /> {{ project()?.name ?? 'Project' }}
        </a>
        <h1>Board</h1>
      </header>

      @if (isLoading()) {
        <p class="loading">Loading…</p>
      } @else {
        <div class="board">
          @for (col of STATUS_COLUMNS; track col.key) {
            <div class="column">
              <div class="column-header" [style.borderTopColor]="col.color">
                <span class="col-label">{{ col.label }}</span>
                <span class="col-count">{{ tasksByStatus()[col.key].length }}</span>
              </div>
              <div class="column-body">
                @for (task of tasksByStatus()[col.key]; track task.id) {
                  <a class="task-card" [routerLink]="['/task', task.id]">
                    <span class="task-title">{{ task.title }}</span>
                    @if (task.priority !== 'none') {
                      <span class="task-priority" [attr.data-priority]="task.priority">{{ task.priority }}</span>
                    }
                  </a>
                }
              </div>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .board-page { padding: 24px; height: 100%; display: flex; flex-direction: column; }
    .board-header { margin-bottom: 20px; }
    .back-link { display: flex; align-items: center; gap: 4px; color: var(--tui-text-secondary, #6b7280); text-decoration: none; font-size: 0.875rem; margin-bottom: 8px; }
    h1 { font-size: 1.5rem; font-weight: 700; }
    .board { display: flex; gap: 12px; overflow-x: auto; flex: 1; align-items: flex-start; }
    .column { flex: 0 0 240px; display: flex; flex-direction: column; background: var(--tui-background-neutral-1, #f9fafb); border-radius: 8px; overflow: hidden; }
    .column-header { padding: 10px 12px; border-top: 3px solid; display: flex; align-items: center; justify-content: space-between; }
    .col-label { font-weight: 600; font-size: 0.875rem; }
    .col-count { font-size: 0.78rem; background: var(--tui-background-neutral-2, #e5e7eb); border-radius: 10px; padding: 1px 7px; }
    .column-body { padding: 8px; display: flex; flex-direction: column; gap: 6px; min-height: 60px; }
    .task-card { display: flex; flex-direction: column; gap: 4px; padding: 10px; background: #fff; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; text-decoration: none; color: inherit; cursor: pointer; transition: box-shadow 0.15s; }
    .task-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
    .task-title { font-size: 0.875rem; line-height: 1.4; }
    .task-priority { font-size: 0.7rem; text-transform: capitalize; padding: 1px 6px; border-radius: 3px; width: fit-content; }
    .task-priority[data-priority="critical"] { background: #fee2e2; color: #b91c1c; }
    .task-priority[data-priority="high"] { background: #fef3c7; color: #b45309; }
    .task-priority[data-priority="medium"] { background: #fefce8; color: #854d0e; }
    .task-priority[data-priority="low"] { background: #f0fdf4; color: #15803d; }
    .loading { color: var(--tui-text-secondary, #6b7280); padding: 24px; }
  `],
})
export class ProjectBoardComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly projectsService = inject(ProjectsService);
  private readonly taskService = inject(TaskService);

  readonly STATUS_COLUMNS = STATUS_COLUMNS;
  readonly projectId = signal('');
  readonly project = signal<Project | null>(null);
  readonly tasks = signal<Task[]>([]);
  readonly isLoading = signal(true);

  readonly tasksByStatus = computed(() => {
    const grouped: Record<string, Task[]> = {};
    for (const col of STATUS_COLUMNS) grouped[col.key] = [];
    for (const t of this.tasks()) {
      if (grouped[t.status]) grouped[t.status].push(t);
    }
    return grouped;
  });

  ngOnInit(): void {
    this.projectId.set(this.route.snapshot.paramMap.get('id') ?? '');
    this.projectsService.get(this.projectId()).subscribe({
      next: p => this.project.set(p),
      error: console.error,
    });
    this.taskService.getProjectTasks(this.projectId()).subscribe({
      next: tasks => { this.tasks.set(tasks); this.isLoading.set(false); },
      error: () => this.isLoading.set(false),
    });
  }
}
