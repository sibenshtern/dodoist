import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import {
  TaskService,
  TaskDetail,
  Comment,
  TimeLog,
  ActivityLogEntry,
} from '../../services/task.service';
import { AttachmentsService, Attachment } from '../../services/attachments.service';
import { ToastService } from '../../services/toast.service';
import { UserService } from '../../services/user.service';
import { RichEditorComponent } from '../../components/rich-editor/rich-editor.component';

type ActiveTab = 'comments' | 'activity' | 'time-logs' | 'attachments';

const STATUS_META: Record<string, { label: string; color: string; bg: string }> = {
  backlog: { label: 'Backlog', color: '#8a8680', bg: '#f0eee9' },
  todo: { label: 'To Do', color: '#64748b', bg: '#f1f5f9' },
  in_progress: { label: 'In Progress', color: '#246fe0', bg: '#ebf2fd' },
  in_review: { label: 'In Review', color: '#ff9800', bg: '#fff7ed' },
  done: { label: 'Done', color: '#299438', bg: '#f0fdf4' },
  cancelled: { label: 'Cancelled', color: '#8a8680', bg: '#f0eee9' },
};

const PRIORITY_META: Record<string, { label: string; color: string; bg: string; emoji: string }> = {
  critical: { label: 'Critical', color: '#db4035', bg: '#fff0ef', emoji: '🔥' },
  high:     { label: 'High',     color: '#c2610c', bg: '#fff7ed', emoji: '⬆' },
  medium:   { label: 'Medium',   color: '#a16207', bg: '#fefce8', emoji: '▶' },
  low:      { label: 'Low',      color: '#15803d', bg: '#f0fdf4', emoji: '⬇' },
  none:     { label: 'None',     color: '#8a8680', bg: '#f0eee9', emoji: '—' },
};

@Component({
  selector: 'app-task-detail',
  standalone: true,
  imports: [DatePipe, RouterLink, ReactiveFormsModule, RichEditorComponent],
  templateUrl: './task-detail.component.html',
  styleUrl: './task-detail.component.scss',
})
export class TaskDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly taskService = inject(TaskService);
  private readonly attachmentsService = inject(AttachmentsService);
  private readonly toast = inject(ToastService);
  private readonly userService = inject(UserService);
  private readonly fb = inject(FormBuilder);

  readonly task = signal<TaskDetail | null>(null);
  readonly comments = signal<Comment[]>([]);
  readonly timeLogs = signal<TimeLog[]>([]);
  readonly activity = signal<ActivityLogEntry[]>([]);
  readonly attachments = signal<Attachment[]>([]);
  readonly isLoading = signal(true);
  readonly activeTab = signal<ActiveTab>('comments');
  readonly totalMinutes = signal(0);
  readonly isDragging = signal(false);
  readonly isUploading = signal(false);

  readonly AttachmentsService = this.attachmentsService;

  readonly STATUS_META = STATUS_META;
  readonly PRIORITY_META = PRIORITY_META;

  readonly statusOptions = Object.keys(STATUS_META);
  readonly priorityOptions = Object.keys(PRIORITY_META);

  readonly commentForm = this.fb.nonNullable.group({ body: [''] });
  readonly timeLogForm = this.fb.nonNullable.group({
    logged_minutes: [30],
    logged_date: [new Date().toISOString().slice(0, 10)],
    description: [''],
  });

  readonly isEditingTitle = signal(false);
  readonly editedTitle = signal('');
  readonly isSaving = signal(false);

  readonly descriptionDraft = signal<unknown>(null);
  readonly descriptionDirty = signal(false);
  readonly isSavingDesc = signal(false);

  readonly currentUserId = computed(() => this.userService.currentUser()?.id ?? '');

  readonly taskStatus = computed(
    () => STATUS_META[this.task()?.status ?? ''] ?? STATUS_META['backlog'],
  );
  readonly taskPriority = computed(
    () => PRIORITY_META[this.task()?.priority ?? ''] ?? PRIORITY_META['none'],
  );

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.router.navigate(['/home']);
      return;
    }
    this.load(id);
  }

  load(id: string): void {
    this.isLoading.set(true);
    this.taskService.getTask(id).subscribe({
      next: (task) => {
        this.task.set(task);
        this.editedTitle.set(task.title);
        this.descriptionDraft.set(task.description);
        this.descriptionDirty.set(false);
        this.isLoading.set(false);
        this.loadComments(id);
        this.loadAttachments(id);
      },
      error: () => {
        this.isLoading.set(false);
        this.toast.error('Failed to load task.');
        this.router.navigate(['/home']);
      },
    });
  }

  loadComments(id: string): void {
    this.taskService.getComments(id).subscribe({
      next: (c) => this.comments.set(c),
      error: () => this.toast.error('Failed to load comments.'),
    });
  }

  loadTimeLogs(id: string): void {
    this.taskService.getTimeLogs(id).subscribe({
      next: (res) => {
        this.timeLogs.set(res.data);
        this.totalMinutes.set(res.meta.total_minutes);
      },
      error: () => this.toast.error('Failed to load time logs.'),
    });
  }

  loadActivity(id: string): void {
    this.taskService.getActivity(id).subscribe({
      next: (a) => this.activity.set(a),
      error: () => this.toast.error('Failed to load activity.'),
    });
  }

  setTab(tab: ActiveTab): void {
    this.activeTab.set(tab);
    const id = this.task()?.id;
    if (!id) return;
    if (tab === 'time-logs' && this.timeLogs().length === 0) this.loadTimeLogs(id);
    if (tab === 'activity' && this.activity().length === 0) this.loadActivity(id);
  }

  loadAttachments(id: string): void {
    this.attachmentsService.list(id).subscribe({
      next: (list) => this.attachments.set(list),
      error: () => this.toast.error('Failed to load attachments.'),
    });
  }

  // ── Inline title edit ────────────────────────────────────────────────────

  startEditTitle(): void {
    this.editedTitle.set(this.task()?.title ?? '');
    this.isEditingTitle.set(true);
  }

  saveTitle(): void {
    const task = this.task();
    const newTitle = this.editedTitle().trim();
    if (!task || !newTitle || newTitle === task.title) {
      this.isEditingTitle.set(false);
      return;
    }
    this.isSaving.set(true);
    this.taskService.updateTask(task.id, { title: newTitle }).subscribe({
      next: () => {
        this.task.set({ ...task, title: newTitle });
        this.isEditingTitle.set(false);
        this.isSaving.set(false);
        this.toast.success('Title updated.');
      },
      error: () => {
        this.toast.error('Failed to update title.');
        this.isSaving.set(false);
      },
    });
  }

  cancelEditTitle(): void {
    this.isEditingTitle.set(false);
  }

  // ── Status / priority change ─────────────────────────────────────────────

  changeStatus(newStatus: string): void {
    const task = this.task();
    if (!task) return;
    const prev = task.status;
    this.task.set({ ...task, status: newStatus });
    this.taskService.updateTask(task.id, { status: newStatus }).subscribe({
      error: () => {
        this.task.set({ ...task, status: prev });
        this.toast.error('Failed to update status.');
      },
    });
  }

  assignToMe(): void {
    const task = this.task();
    const me = this.userService.currentUser();
    if (!task || !me) return;
    const prev = task.assigned_to;
    this.task.set({
      ...task,
      assigned_to: { id: me.id, display_name: me.display_name, email: me.email },
    });
    this.taskService.updateTask(task.id, { assigned_to_id: me.id }).subscribe({
      error: () => {
        this.task.set({ ...task, assigned_to: prev });
        this.toast.error('Failed to assign task.');
      },
    });
  }

  changePriority(newPriority: string): void {
    const task = this.task();
    if (!task) return;
    const prev = task.priority;
    this.task.set({ ...task, priority: newPriority });
    this.taskService.updateTask(task.id, { priority: newPriority }).subscribe({
      error: () => {
        this.task.set({ ...task, priority: prev });
        this.toast.error('Failed to update priority.');
      },
    });
  }

  // ── Description ──────────────────────────────────────────────────────────

  onDescriptionChange(json: unknown): void {
    this.descriptionDraft.set(json);
    this.descriptionDirty.set(true);
  }

  saveDescription(): void {
    const task = this.task();
    if (!task) return;
    this.isSavingDesc.set(true);
    this.taskService.updateTask(task.id, { description: this.descriptionDraft() }).subscribe({
      next: () => {
        this.task.set({ ...task, description: this.descriptionDraft() });
        this.descriptionDirty.set(false);
        this.isSavingDesc.set(false);
        this.toast.success('Description saved.');
      },
      error: () => {
        this.toast.error('Failed to save description.');
        this.isSavingDesc.set(false);
      },
    });
  }

  discardDescription(): void {
    const task = this.task();
    this.descriptionDraft.set(task?.description ?? null);
    this.descriptionDirty.set(false);
  }

  // ── Delete task ──────────────────────────────────────────────────────────

  deleteTask(): void {
    const task = this.task();
    if (!task || !confirm('Delete this task?')) return;
    this.taskService.deleteTask(task.id).subscribe({
      next: () => {
        this.toast.success('Task deleted.');
        this.router.navigate(['/tasks']);
      },
      error: () => this.toast.error('Failed to delete task.'),
    });
  }

  // ── Comments ─────────────────────────────────────────────────────────────

  submitComment(): void {
    const task = this.task();
    const body = this.commentForm.controls.body.value.trim();
    if (!task || !body) return;
    const proseMirrorBody = {
      type: 'doc',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: body }] }],
    };
    this.taskService.addComment(task.id, proseMirrorBody).subscribe({
      next: (comment) => {
        this.comments.update((cs) => [comment, ...cs]);
        this.commentForm.reset({ body: '' });
      },
      error: () => this.toast.error('Failed to post comment.'),
    });
  }

  deleteComment(commentId: string): void {
    if (!confirm('Delete this comment?')) return;
    this.taskService.deleteComment(commentId).subscribe({
      next: () => this.comments.update((cs) => cs.filter((c) => c.id !== commentId)),
      error: () => this.toast.error('Failed to delete comment.'),
    });
  }

  commentText(comment: Comment): string {
    try {
      const doc = comment.body as any;
      return (
        doc?.content
          ?.flatMap((b: any) => b.content?.map((n: any) => n.text ?? '') ?? [])
          .join(' ') ?? ''
      );
    } catch {
      return '';
    }
  }

  isOwnComment(comment: Comment): boolean {
    return comment.author.id === this.currentUserId();
  }

  // ── Time logs ────────────────────────────────────────────────────────────

  submitTimeLog(): void {
    const task = this.task();
    if (!task) return;
    const { logged_minutes, logged_date, description } = this.timeLogForm.getRawValue();
    this.taskService
      .addTimeLog(task.id, {
        logged_minutes: Number(logged_minutes),
        logged_date,
        description,
      })
      .subscribe({
        next: (log) => {
          this.timeLogs.update((ls) => [log, ...ls]);
          this.totalMinutes.update((m) => m + log.logged_minutes);
          this.timeLogForm.reset({
            logged_minutes: 30,
            logged_date: new Date().toISOString().slice(0, 10),
            description: '',
          });
          this.toast.success('Time logged.');
        },
        error: () => this.toast.error('Failed to log time.'),
      });
  }

  deleteTimeLog(logId: string, minutes: number): void {
    if (!confirm('Remove this time log?')) return;
    this.taskService.deleteTimeLog(logId).subscribe({
      next: () => {
        this.timeLogs.update((ls) => ls.filter((l) => l.id !== logId));
        this.totalMinutes.update((m) => m - minutes);
      },
      error: () => this.toast.error('Failed to delete time log.'),
    });
  }

  minutesToHours(minutes: number): string {
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  }

  // ── Attachments ──────────────────────────────────────────────────────────

  onFileDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
    const files = event.dataTransfer?.files;
    if (files?.length) this.uploadFile(files[0]);
  }

  onFileSelect(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) this.uploadFile(input.files[0]);
    input.value = '';
  }

  uploadFile(file: File): void {
    const task = this.task();
    if (!task) return;
    this.isUploading.set(true);
    this.attachmentsService.upload(task.id, file).subscribe({
      next: (attachment) => {
        this.attachments.update((list) => [attachment, ...list]);
        this.isUploading.set(false);
        this.toast.success('File uploaded.');
      },
      error: (err) => {
        const msg = err?.error?.detail ?? 'Upload failed.';
        this.toast.error(msg);
        this.isUploading.set(false);
      },
    });
  }

  deleteAttachment(id: string, filename: string): void {
    if (!confirm(`Delete "${filename}"?`)) return;
    this.attachmentsService.delete(id).subscribe({
      next: () => this.attachments.update((list) => list.filter((a) => a.id !== id)),
      error: () => this.toast.error('Failed to delete attachment.'),
    });
  }

  isOwnAttachment(attachment: Attachment): boolean {
    return attachment.uploaded_by.id === this.currentUserId();
  }

  // ── Reactions ────────────────────────────────────────────────────────────

  react(commentId: string, emoji: string): void {
    this.taskService.addReaction(commentId, emoji).subscribe({
      error: () => this.toast.error('Failed to add reaction.'),
    });
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  initials(name: string): string {
    return (
      name
        .split(' ')
        .map((n) => n[0] ?? '')
        .filter(Boolean)
        .join('')
        .toUpperCase()
        .slice(0, 2) || '?'
    );
  }

  formatDate(dateStr: string | null | undefined): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }
}
