import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import { TaskService, Task } from '../../services/task.service';
import { hexToRgba } from '../../utils/color.util';

interface Column {
  key: string;
  label: string;
  color: string;
}

@Component({
  selector: 'app-my-tasks',
  standalone: true,
  imports: [TuiIcon],
  templateUrl: './my-tasks.component.html',
  styleUrl: './my-tasks.component.scss',
})
export class MyTasksComponent implements OnInit {
  private readonly taskService = inject(TaskService);
  private readonly router = inject(Router);

  readonly COLUMNS: Column[] = [
    { key: 'backlog',     label: 'Backlog',      color: '#94a3b8' },
    { key: 'todo',        label: 'To Do',        color: '#64748b' },
    { key: 'in_progress', label: 'In Progress',  color: '#246fe0' },
    { key: 'in_review',   label: 'In Review',    color: '#ff9800' },
    { key: 'done',        label: 'Done',         color: '#299438' },
  ];

  readonly tasks     = signal<Task[]>([]);
  readonly isLoading = signal(true);
  readonly loadError = signal(false);

  readonly tasksByStatus = computed(() => {
    const grouped: Record<string, Task[]> = {};
    for (const col of this.COLUMNS) grouped[col.key] = [];
    for (const task of this.tasks()) {
      if (grouped[task.status]) grouped[task.status].push(task);
    }
    return grouped;
  });

  private draggedId: string | null = null;
  private dragMoved = false;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.isLoading.set(true);
    this.loadError.set(false);
    this.taskService.getMyTasks().subscribe({
      next:  tasks => { this.tasks.set(tasks); this.isLoading.set(false); },
      error: ()    => { this.isLoading.set(false); this.loadError.set(true); },
    });
  }

  navigateToNewTask(): void {
    this.router.navigate(['/task/new']);
  }

  onDragStart(taskId: string): void {
    this.draggedId = taskId;
    this.dragMoved = true;
  }

  onDragEnd(): void {
    this.dragMoved = false;
  }

  onCardClick(taskId: string): void {
    if (this.dragMoved) { this.dragMoved = false; return; }
    this.router.navigate(['/task', taskId]);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
  }

  onDrop(targetStatus: string): void {
    const id = this.draggedId;
    this.draggedId = null;
    if (!id) return;

    const task = this.tasks().find(t => t.id === id);
    if (!task || task.status === targetStatus) return;

    // Optimistic update
    this.tasks.update(ts => ts.map(t => t.id === id ? { ...t, status: targetStatus } : t));

    this.taskService.updateTask(id, { status: targetStatus }).subscribe({
      error: () => this.load(), // revert on failure
    });
  }

  assigneeInitial(task: Task): string {
    return task.assigned_to?.display_name[0]?.toUpperCase() ?? '?';
  }

  formatDue(dateStr: string | null): string {
    if (!dateStr) return '–';
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  priorityColor(priority: string): string {
    const map: Record<string, string> = {
      critical: '#db4035',
      high:     '#ff9800',
      medium:   '#a16207',
      low:      '#299438',
      none:     '#8a8680',
    };
    return map[priority] ?? '#8a8680';
  }

  labelBg(hex: string): string {
    return hexToRgba(hex, 0.12);
  }
}
