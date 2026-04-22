import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { TuiIcon } from '@taiga-ui/core';
import { SprintsService, Sprint } from '../../services/sprints.service';
import { ProjectsService, Project } from '../../services/projects.service';
import { TaskService, Task } from '../../services/task.service';

@Component({
  selector: 'app-project-sprint-detail',
  standalone: true,
  imports: [RouterLink, TuiIcon],
  template: `
    <div class="page">
      <header class="page-header">
        <a [routerLink]="['/projects', projectId()]" class="back-link">
          <tui-icon icon="@tui.arrow-left" /> {{ project()?.name ?? 'Project' }}
        </a>
        @if (sprint()) {
          <div class="sprint-title-row">
            <h1>{{ sprint()!.name }}</h1>
            <span class="status-badge" [attr.data-status]="sprint()!.status">{{ sprint()!.status }}</span>
          </div>
          @if (sprint()!.goal) { <p class="goal">{{ sprint()!.goal }}</p> }
        }
      </header>

      @if (isLoading()) {
        <p class="loading">Loading…</p>
      } @else if (sprint()) {
        <div class="sprint-meta">
          @if (sprint()!.start_date) { <span>Start: {{ sprint()!.start_date }}</span> }
          @if (sprint()!.end_date) { <span>End: {{ sprint()!.end_date }}</span> }
        </div>

        <div class="actions">
          @if (sprint()!.status === 'planned') {
            <button class="btn-primary" (click)="startSprint()" [disabled]="actionLoading()">Start sprint</button>
          }
          @if (sprint()!.status === 'active') {
            <button class="btn-warning" (click)="completeSprint()" [disabled]="actionLoading()">Complete sprint</button>
          }
        </div>
        @if (actionError()) { <p class="error">{{ actionError() }}</p> }

        <section class="section">
          <h2>Tasks ({{ tasks().length }})</h2>
          @if (tasks().length === 0) {
            <p class="empty">No tasks in this sprint.</p>
          } @else {
            <ul class="task-list">
              @for (task of tasks(); track task.id) {
                <li class="task-item">
                  <a [routerLink]="['/task', task.id]" class="task-link">{{ task.title }}</a>
                  <span class="task-status" [attr.data-status]="task.status">{{ task.status }}</span>
                </li>
              }
            </ul>
          }
        </section>
      }
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 720px; margin: 0 auto; }
    .page-header { margin-bottom: 24px; }
    .back-link { display: flex; align-items: center; gap: 4px; color: var(--tui-text-secondary, #6b7280); text-decoration: none; font-size: 0.875rem; margin-bottom: 8px; }
    .sprint-title-row { display: flex; align-items: center; gap: 12px; }
    h1 { font-size: 1.5rem; font-weight: 700; }
    .status-badge { font-size: 0.75rem; padding: 2px 10px; border-radius: 10px; text-transform: capitalize; }
    .status-badge[data-status="planned"] { background: #f3f4f6; color: #6b7280; }
    .status-badge[data-status="active"] { background: #dbeafe; color: #1d4ed8; }
    .status-badge[data-status="completed"] { background: #dcfce7; color: #15803d; }
    .goal { color: var(--tui-text-secondary, #6b7280); font-style: italic; margin-top: 4px; }
    .sprint-meta { display: flex; gap: 20px; font-size: 0.875rem; color: var(--tui-text-secondary, #6b7280); margin-bottom: 16px; }
    .actions { display: flex; gap: 8px; margin-bottom: 16px; }
    .btn-primary { padding: 8px 20px; background: var(--tui-background-accent-1, #246fe0); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
    .btn-warning { padding: 8px 20px; background: #f59e0b; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
    .btn-primary:disabled, .btn-warning:disabled { opacity: 0.5; cursor: default; }
    .error { color: #ef4444; font-size: 0.875rem; }
    .section { border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 8px; padding: 20px; }
    h2 { font-size: 1rem; font-weight: 600; margin: 0 0 12px; }
    .task-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
    .task-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; }
    .task-link { text-decoration: none; color: inherit; font-size: 0.875rem; }
    .task-link:hover { color: var(--tui-text-accent, #246fe0); }
    .task-status { font-size: 0.75rem; padding: 2px 8px; border-radius: 10px; background: var(--tui-background-neutral-1, #f3f4f6); color: var(--tui-text-secondary, #6b7280); text-transform: capitalize; }
    .loading, .empty { color: var(--tui-text-secondary, #6b7280); font-size: 0.875rem; }
  `],
})
export class ProjectSprintDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly sprintsService = inject(SprintsService);
  private readonly projectsService = inject(ProjectsService);
  private readonly taskService = inject(TaskService);

  readonly projectId = signal('');
  readonly sprintId = signal('');
  readonly project = signal<Project | null>(null);
  readonly sprint = signal<Sprint | null>(null);
  readonly tasks = signal<Task[]>([]);
  readonly isLoading = signal(true);
  readonly actionLoading = signal(false);
  readonly actionError = signal('');

  ngOnInit(): void {
    this.projectId.set(this.route.snapshot.paramMap.get('id') ?? '');
    this.sprintId.set(this.route.snapshot.paramMap.get('sprintId') ?? '');

    forkJoin({
      project: this.projectsService.get(this.projectId()),
      sprint: this.sprintsService.getDetail(this.sprintId()),
      tasks: this.taskService.getProjectTasks(this.projectId()),
    }).subscribe({
      next: ({ project, sprint, tasks }) => {
        this.project.set(project);
        this.sprint.set(sprint);
        this.tasks.set(tasks.filter(t => t.sprint === this.sprintId()));
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  startSprint(): void {
    this.actionLoading.set(true);
    this.sprintsService.start(this.sprintId()).subscribe({
      next: s => { this.sprint.set(s); this.actionLoading.set(false); },
      error: (err) => { this.actionError.set(err?.error?.detail ?? 'Failed'); this.actionLoading.set(false); },
    });
  }

  completeSprint(): void {
    this.actionLoading.set(true);
    this.sprintsService.complete(this.sprintId(), { incomplete_tasks_action: 'backlog' }).subscribe({
      next: s => { this.sprint.set(s); this.actionLoading.set(false); },
      error: (err) => { this.actionError.set(err?.error?.detail ?? 'Failed'); this.actionLoading.set(false); },
    });
  }
}
