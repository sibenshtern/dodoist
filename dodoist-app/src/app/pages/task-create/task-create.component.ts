import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

export type TaskType     = 'task' | 'bug' | 'story' | 'epic' | 'personal';
export type TaskPriority = 'critical' | 'high' | 'medium' | 'low' | 'none';
export type TaskStatus   = 'backlog' | 'todo' | 'in_progress' | 'in_review' | 'done' | 'cancelled';

interface TypeMeta     { value: TaskType;     label: string; emoji: string; bg: string; color: string; }
interface PriorityMeta { value: TaskPriority; label: string; emoji: string; bg: string; color: string; }
interface StatusMeta   { value: TaskStatus;   label: string; bg: string; color: string; }

@Component({
  selector: 'app-task-create',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './task-create.component.html',
  styleUrl: './task-create.component.scss',
})
export class TaskCreateComponent {
  private readonly fb = inject(FormBuilder);

  readonly form = this.fb.nonNullable.group({
    title:           ['', [Validators.required, Validators.maxLength(500)]],
    description:     [''],
    type:            ['task' as TaskType],
    status:          ['backlog' as TaskStatus],
    priority:        ['none' as TaskPriority],
    project_id:      ['' as string],
    assigned_to:     ['' as string],
    sprint_id:       ['' as string],
    board_column_id: ['' as string],
    parent_task_id:  [''],
    story_points:    [null as number | null],
    due_date:        [''],
    start_date:      [''],
    reminder_at:     [''],
    is_private:      [false],
  });

  readonly types: TypeMeta[] = [
    { value: 'task',     label: 'Task',     emoji: '✓',  bg: '#f0eee9', color: '#1a1814' },
    { value: 'bug',      label: 'Bug',      emoji: '🐛', bg: '#fff0ef', color: '#db4035' },
    { value: 'story',    label: 'Story',    emoji: '📖', bg: '#ebf2fd', color: '#246fe0' },
    { value: 'epic',     label: 'Epic',     emoji: '⚡', bg: '#f3eeff', color: '#7c3aed' },
    { value: 'personal', label: 'Personal', emoji: '◎',  bg: '#f0fdf4', color: '#15803d' },
  ];

  readonly priorities: PriorityMeta[] = [
    { value: 'critical', label: 'Critical',    emoji: '🔥', bg: '#fff0ef', color: '#db4035' },
    { value: 'high',     label: 'High',        emoji: '⬆',  bg: '#fff7ed', color: '#c2610c' },
    { value: 'medium',   label: 'Medium',      emoji: '▶',  bg: '#fefce8', color: '#a16207' },
    { value: 'low',      label: 'Low',         emoji: '⬇',  bg: '#f0fdf4', color: '#15803d' },
    { value: 'none',     label: 'No priority', emoji: '—',  bg: '#f0eee9', color: '#8a8680' },
  ];

  readonly statuses: StatusMeta[] = [
    { value: 'backlog',     label: 'Backlog',     bg: '#f0eee9', color: '#8a8680' },
    { value: 'todo',        label: 'To Do',       bg: '#f0eee9', color: '#1a1814' },
    { value: 'in_progress', label: 'In Progress', bg: '#ebf2fd', color: '#246fe0' },
    { value: 'in_review',   label: 'In Review',   bg: '#f3eeff', color: '#7c3aed' },
    { value: 'done',        label: 'Done',        bg: '#f0fdf4', color: '#15803d' },
    { value: 'cancelled',   label: 'Cancelled',   bg: '#fff0ef', color: '#db4035' },
  ];

  // TODO: replace with GET /workspaces/{workspaceId}/projects
  readonly mockProjects = ['Dodoist Web', 'Dodoist Mobile', 'Design System'];
  // TODO: replace with GET /projects/{projectId}/members
  readonly mockUsers    = ['Alice Johnson', 'Bob Chen', 'Carol Davis'];
  // TODO: replace with GET /projects/{projectId}/sprints?status=active,planned
  readonly mockSprints  = ['Sprint 5 (Mar 3–17)', 'Sprint 6 (Mar 17–31)'];
  // TODO: replace with GET /boards/{boardId}/columns
  readonly mockColumns  = ['Backlog', 'To Do', 'In Progress', 'In Review', 'Done'];
  // TODO: replace with GET /workspaces/{workspaceId}/labels
  readonly mockLabels   = ['Authentication', 'Backend', 'Frontend', 'Bug', 'Enhancement', 'Security', 'Docs'];

  selectedLabelIds = signal<string[]>([]);

  get currentType():     TypeMeta     { return this.types.find(t => t.value === this.form.controls.type.value)!; }
  get currentStatus():   StatusMeta   { return this.statuses.find(s => s.value === this.form.controls.status.value)!; }
  get currentPriority(): PriorityMeta { return this.priorities.find(p => p.value === this.form.controls.priority.value)!; }
  get titleInvalid():    boolean {
    const c = this.form.controls.title;
    return c.invalid && (c.dirty || c.touched);
  }

  setType(v: TaskType):         void { this.form.controls.type.setValue(v); }
  setStatus(v: TaskStatus):     void { this.form.controls.status.setValue(v); }
  setPriority(v: TaskPriority): void { this.form.controls.priority.setValue(v); }

  toggleLabel(label: string): void {
    this.selectedLabelIds.update(ids =>
      ids.includes(label) ? ids.filter(l => l !== label) : [...ids, label]
    );
  }

  isLabelSelected(label: string): boolean { return this.selectedLabelIds().includes(label); }

  submit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) return;

    const raw = this.form.getRawValue();
    // TODO: POST /projects/{projectId}/tasks
    const payload = {
      title:           raw.title,
      description:     raw.description   || undefined,
      type:            raw.type,
      status:          raw.status,
      priority:        raw.priority,
      assigned_to:     raw.assigned_to   || undefined,
      sprint_id:       raw.sprint_id     || undefined,
      board_column_id: raw.board_column_id || undefined,
      parent_task_id:  raw.parent_task_id  || undefined,
      story_points:    raw.story_points  ?? undefined,
      due_date:        raw.due_date      || undefined,
      start_date:      raw.start_date    || undefined,
      reminder_at:     raw.reminder_at   || undefined,
      is_private:      raw.is_private,
      label_ids:       this.selectedLabelIds(),
    };
    console.log('Create task payload:', payload);
  }
}
