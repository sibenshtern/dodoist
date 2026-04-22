import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CdkDragDrop, DragDropModule, moveItemInArray } from '@angular/cdk/drag-drop';
import { TuiIcon } from '@taiga-ui/core';
import { ProjectsService, Project } from '../../services/projects.service';
import { TaskService, Task } from '../../services/task.service';

@Component({
  selector: 'app-project-backlog',
  standalone: true,
  imports: [RouterLink, DragDropModule, TuiIcon],
  template: `
    <div class="page">
      <header class="page-header">
        <a [routerLink]="['/projects', projectId()]" class="back-link">
          <tui-icon icon="@tui.arrow-left" /> {{ project()?.name ?? 'Project' }}
        </a>
        <h1>Backlog</h1>
      </header>

      @if (isLoading()) {
        <p class="loading">Loading…</p>
      } @else if (tasks().length === 0) {
        <p class="empty">No backlog items.</p>
      } @else {
        <ul
          cdkDropList
          class="backlog-list"
          (cdkDropListDropped)="onDrop($event)"
        >
          @for (task of tasks(); track task.id) {
            <li cdkDrag class="task-row">
              <tui-icon icon="@tui.grip-vertical" class="drag-handle" cdkDragHandle />
              <a [routerLink]="['/task', task.id]" class="task-title">{{ task.title }}</a>
              <span class="task-status" [attr.data-status]="task.status">{{ task.status }}</span>
              @if (task.priority !== 'none') {
                <span class="task-priority" [attr.data-priority]="task.priority">{{ task.priority }}</span>
              }
            </li>
          }
        </ul>
      }
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 760px; margin: 0 auto; }
    .page-header { margin-bottom: 20px; }
    .back-link { display: flex; align-items: center; gap: 4px; color: var(--tui-text-secondary, #6b7280); text-decoration: none; font-size: 0.875rem; margin-bottom: 8px; }
    h1 { font-size: 1.5rem; font-weight: 700; }
    .backlog-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 4px; }
    .task-row { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #fff; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; cursor: default; }
    .drag-handle { color: var(--tui-text-tertiary, #9ca3af); cursor: grab; flex-shrink: 0; }
    .drag-handle:active { cursor: grabbing; }
    .task-title { flex: 1; text-decoration: none; color: inherit; font-size: 0.875rem; }
    .task-title:hover { color: var(--tui-text-accent, #246fe0); }
    .task-status { font-size: 0.75rem; padding: 2px 8px; border-radius: 10px; background: var(--tui-background-neutral-1, #f3f4f6); color: var(--tui-text-secondary, #6b7280); text-transform: capitalize; }
    .task-priority { font-size: 0.7rem; padding: 1px 6px; border-radius: 3px; text-transform: capitalize; }
    .task-priority[data-priority="critical"] { background: #fee2e2; color: #b91c1c; }
    .task-priority[data-priority="high"] { background: #fef3c7; color: #b45309; }
    .task-priority[data-priority="medium"] { background: #fefce8; color: #854d0e; }
    .cdk-drag-preview { box-shadow: 0 4px 16px rgba(0,0,0,0.12); opacity: 0.95; }
    .cdk-drag-placeholder { opacity: 0.3; }
    .loading, .empty { color: var(--tui-text-secondary, #6b7280); }
  `],
})
export class ProjectBacklogComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly projectsService = inject(ProjectsService);
  private readonly taskService = inject(TaskService);

  readonly projectId = signal('');
  readonly project = signal<Project | null>(null);
  readonly tasks = signal<Task[]>([]);
  readonly isLoading = signal(true);

  ngOnInit(): void {
    this.projectId.set(this.route.snapshot.paramMap.get('id') ?? '');
    this.projectsService.get(this.projectId()).subscribe({
      next: p => this.project.set(p),
      error: console.error,
    });
    this.taskService.getProjectTasks(this.projectId()).subscribe({
      next: tasks => {
        // Sort by position for backlog order
        this.tasks.set([...tasks].sort((a, b) => a.position - b.position));
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  onDrop(event: CdkDragDrop<Task[]>): void {
    const list = [...this.tasks()];
    moveItemInArray(list, event.previousIndex, event.currentIndex);
    this.tasks.set(list);

    // Persist new position for the moved task
    const movedTask = list[event.currentIndex];
    this.taskService.updateTask(movedTask.id, { position: event.currentIndex }).subscribe({
      error: () => {
        // Revert on failure
        const reverted = [...list];
        moveItemInArray(reverted, event.currentIndex, event.previousIndex);
        this.tasks.set(reverted);
      },
    });
  }
}
