import { Component, inject, signal, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink, Router } from '@angular/router';
import { forkJoin, of, switchMap } from 'rxjs';
import { TaskService, TaskCreatePayload } from '../../services/task.service';
import { UserService } from '../../services/user.service';
import { RichEditorComponent } from '../../components/rich-editor/rich-editor.component';

export type TaskType = 'task' | 'bug' | 'story' | 'epic' | 'personal';
export type TaskPriority = 'critical' | 'high' | 'medium' | 'low' | 'none';
export type TaskStatus = 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'cancelled';

interface TypeMeta {
  value: TaskType;
  label: string;
  emoji: string;
  bg: string;
  color: string;
}
interface PriorityMeta {
  value: TaskPriority;
  label: string;
  emoji: string;
  bg: string;
  color: string;
}
interface ProjectOption {
  id: string;
  name: string;
  color: string;
}
interface MemberOption {
  id: string;
  displayName: string;
}
interface SprintOption {
  id: string;
  name: string;
}
interface LabelOption {
  id: string;
  name: string;
  color: string;
}

@Component({
  selector: 'app-task-create',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink, RichEditorComponent],
  templateUrl: './task-create.component.html',
  styleUrl: './task-create.component.scss',
})
export class TaskCreateComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly taskService = inject(TaskService);
  private readonly userService = inject(UserService);
  private readonly router = inject(Router);

  readonly form = this.fb.nonNullable.group({
    title: ['', [Validators.required, Validators.maxLength(500)]],
    type: ['task' as TaskType],
    status: ['backlog' as TaskStatus],
    priority: ['none' as TaskPriority],
    project_id: ['' as string],
    assigned_to: ['' as string],
    sprint_id: ['' as string],
    parent_task_id: [''],
    story_points: [null as number | null],
    due_date: [''],
    start_date: [''],
    reminder_at: [''],
    is_private: [false],
  });

  readonly types: TypeMeta[] = [
    { value: 'task', label: 'Task', emoji: '✓', bg: '#f0eee9', color: '#1a1814' },
    { value: 'bug', label: 'Bug', emoji: '🐛', bg: '#fff0ef', color: '#db4035' },
    { value: 'story', label: 'Story', emoji: '📖', bg: '#ebf2fd', color: '#246fe0' },
    { value: 'epic', label: 'Epic', emoji: '⚡', bg: '#f3eeff', color: '#7c3aed' },
    { value: 'personal', label: 'Personal', emoji: '◎', bg: '#f0fdf4', color: '#15803d' },
  ];

  readonly priorities: PriorityMeta[] = [
    { value: 'critical', label: 'Critical', emoji: '🔥', bg: '#fff0ef', color: '#db4035' },
    { value: 'high', label: 'High', emoji: '⬆', bg: '#fff7ed', color: '#c2610c' },
    { value: 'medium', label: 'Medium', emoji: '▶', bg: '#fefce8', color: '#a16207' },
    { value: 'low', label: 'Low', emoji: '⬇', bg: '#f0fdf4', color: '#15803d' },
    { value: 'none', label: 'No priority', emoji: '—', bg: '#f0eee9', color: '#8a8680' },
  ];

  readonly projects = signal<ProjectOption[]>([]);
  readonly members = signal<MemberOption[]>([]);
  readonly sprints = signal<SprintOption[]>([]);
  readonly labels = signal<LabelOption[]>([]);
  readonly isLoading = signal(false);
  readonly serverError = signal<string | null>(null);

  readonly selectedLabelIds = signal<string[]>([]);
  readonly descriptionJson = signal<unknown>(null);

  get currentType(): TypeMeta {
    return this.types.find((t) => t.value === this.form.controls.type.value)!;
  }
  get currentPriority(): PriorityMeta {
    return this.priorities.find((p) => p.value === this.form.controls.priority.value)!;
  }
  get titleInvalid(): boolean {
    const c = this.form.controls.title;
    return c.invalid && (c.dirty || c.touched);
  }

  setType(v: TaskType): void {
    this.form.controls.type.setValue(v);
  }
  setPriority(v: TaskPriority): void {
    this.form.controls.priority.setValue(v);
  }

  assignToMe(): void {
    const me = this.userService.currentUser();
    if (!me) return;
    if (!this.members().find((m) => m.id === me.id)) {
      this.members.update((ms) => [{ id: me.id, displayName: me.display_name }, ...ms]);
    }
    this.form.controls.assigned_to.setValue(me.id);
  }

  get isAssignedToMe(): boolean {
    return this.form.controls.assigned_to.value === this.userService.currentUser()?.id;
  }

  toggleLabel(labelId: string): void {
    this.selectedLabelIds.update((ids) =>
      ids.includes(labelId) ? ids.filter((l) => l !== labelId) : [...ids, labelId],
    );
  }

  isLabelSelected(labelId: string): boolean {
    return this.selectedLabelIds().includes(labelId);
  }

  ngOnInit(): void {
    this.userService.loadWorkspaces().subscribe((workspaces) => {
      const ws = workspaces.find((w) => w.is_personal) ?? workspaces[0];
      if (!ws) return;
      this.taskService
        .getWorkspaceProjects(ws.slug)
        .subscribe((ps) =>
          this.projects.set(
            ps.map((p) => ({ id: p.id, name: p.name, color: p.color || '#6b7280' })),
          ),
        );
      this.taskService
        .getWorkspaceLabels(ws.slug)
        .subscribe((ls) =>
          this.labels.set(ls.map((l) => ({ id: l.id, name: l.name, color: l.color || '#6b7280' }))),
        );
    });

    this.form.controls.project_id.valueChanges.subscribe((projectId) => {
      this.members.set([]);
      this.sprints.set([]);
      if (!projectId) return;
      this.taskService
        .getProjectMembers(projectId)
        .subscribe((ms) =>
          this.members.set(ms.map((m) => ({ id: m.user.id, displayName: m.user.display_name }))),
        );
      this.taskService
        .getProjectSprints(projectId)
        .subscribe((ss) => this.sprints.set(ss.map((s) => ({ id: s.id, name: s.name }))));
    });
  }

  submit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) return;

    this.isLoading.set(true);
    this.serverError.set(null);

    const raw = this.form.getRawValue();
    console.log(raw);

    const payload: TaskCreatePayload = {
      title: raw.title,
      task_type: raw.type,
      priority: raw.priority,
      status: raw.status,
      is_private: raw.is_private,
      description: this.descriptionJson() ?? undefined,
      project_id: raw.project_id || undefined,
      assigned_to_id: raw.assigned_to || undefined,
      sprint_id: raw.sprint_id || undefined,
      parent_task_id: raw.parent_task_id || undefined,
      story_points: raw.story_points ?? undefined,
      due_date: raw.due_date || undefined,
      start_date: raw.start_date || undefined,
      reminder_at: raw.reminder_at || undefined,
    };

    this.taskService
      .createTask(payload)
      .pipe(
        switchMap((task) => {
          const labelIds = this.selectedLabelIds();
          if (labelIds.length === 0) return of({ taskId: task.id, labelsOk: true });
          return forkJoin(labelIds.map((id) => this.taskService.addLabel(task.id, id))).pipe(
            switchMap(() => of({ taskId: task.id, labelsOk: true })),
          );
        }),
      )
      .subscribe({
        next: () => {
          this.isLoading.set(false);
          this.router.navigate(['/home']);
        },
        error: (err) => {
          this.serverError.set(
            err.error?.detail ?? err.error?.title?.[0] ?? 'Failed to create task.',
          );
          this.isLoading.set(false);
        },
      });
  }
}
