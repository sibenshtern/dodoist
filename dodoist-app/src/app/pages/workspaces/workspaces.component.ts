import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { TuiIcon } from '@taiga-ui/core';
import { WorkspaceService, WorkspaceDetail } from '../../services/workspace.service';
import { UserService } from '../../services/user.service';
import { ConfirmDialogService } from '../../services/confirm-dialog.service';

@Component({
  selector: 'app-workspaces',
  standalone: true,
  imports: [RouterLink, FormsModule, DatePipe, TuiIcon],
  template: `
    <div class="page">
      <header class="page-header">
        <h1>Workspaces</h1>
        <button class="btn-primary" (click)="showForm.set(!showForm())">
          <tui-icon icon="@tui.plus" />
          New workspace
        </button>
      </header>

      @if (showForm()) {
        <div class="create-form">
          <h2>Create workspace</h2>
          <div class="field">
            <label for="ws-name">Name <span class="required">*</span></label>
            <input id="ws-name" [(ngModel)]="newName" placeholder="e.g. My Team" [disabled]="isCreating()" />
          </div>
          <div class="field">
            <label for="ws-slug">Slug <span class="hint">(optional — auto-generated)</span></label>
            <input id="ws-slug" [(ngModel)]="newSlug" placeholder="e.g. my-team" [disabled]="isCreating()" />
          </div>
          <div class="field">
            <label for="ws-desc">Description</label>
            <textarea id="ws-desc" [(ngModel)]="newDescription" rows="2" [disabled]="isCreating()"></textarea>
          </div>
          @if (createError()) {
            <p class="error">{{ createError() }}</p>
          }
          <div class="form-actions">
            <button class="btn-secondary" (click)="cancelCreate()" [disabled]="isCreating()">Cancel</button>
            <button class="btn-primary" (click)="submitCreate()" [disabled]="!newName.trim() || isCreating()">
              {{ isCreating() ? 'Creating…' : 'Create' }}
            </button>
          </div>
        </div>
      }

      @if (isLoading()) {
        <p class="loading">Loading…</p>
      } @else if (workspaces().length === 0) {
        <p class="empty">No workspaces yet. Create one above.</p>
      } @else {
        <ul class="workspace-list">
          @for (ws of workspaces(); track ws.id) {
            <li class="workspace-card" [class.workspace-card--deleted]="ws.deleted_at">
              <div class="workspace-main">
                <a [routerLink]="['/workspaces', ws.slug]" class="workspace-link">
                  <span class="ws-initial">{{ ws.name[0]?.toUpperCase() }}</span>
                  <div class="ws-info">
                    <div class="ws-name-row">
                      <strong>{{ ws.name }}</strong>
                      @if (isOwner(ws)) {
                        <span class="role-badge role-badge--owner">Owner</span>
                      } @else {
                        <span class="role-badge role-badge--member">Member</span>
                      }
                      @if (ws.deleted_at) {
                        <span class="badge badge--warn">Deletion scheduled</span>
                      }
                    </div>
                    @if (ws.deleted_at && ws.delete_scheduled_for) {
                      <span class="ws-deleted-note">Deletes {{ ws.delete_scheduled_for | date:'mediumDate' }}</span>
                    }
                  </div>
                </a>
                <div class="ws-actions">
                  @if (!ws.deleted_at && ws.id !== userService.currentWorkspace()?.id) {
                    <button class="btn-switch" (click)="switchTo(ws)" [disabled]="isSwitching()">
                      Switch to
                    </button>
                  }
                  @if (ws.id === userService.currentWorkspace()?.id) {
                    <span class="active-badge">Active</span>
                  }
                  @if (isOwner(ws) && !ws.is_personal) {
                    @if (ws.deleted_at) {
                      <button class="btn-secondary btn-sm" (click)="restoreWs(ws)" [disabled]="actingId() === ws.id">
                        Restore
                      </button>
                    } @else {
                      <button class="btn-danger-outline btn-sm" (click)="deleteWs(ws)" [disabled]="actingId() === ws.id">
                        Delete
                      </button>
                    }
                  }
                </div>
              </div>
            </li>
          }
        </ul>
      }

      @if (actionError()) { <p class="error">{{ actionError() }}</p> }
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 660px; margin: 0 auto; }
    .page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
    h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
    .btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; background: var(--tui-background-accent-1, #246fe0); color: #fff; border: none; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; }
    .btn-primary:hover:not(:disabled) { opacity: 0.9; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { padding: 8px 16px; background: transparent; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; font-size: 0.875rem; cursor: pointer; }
    .btn-secondary:hover:not(:disabled) { background: var(--tui-background-neutral-1, #f9fafb); }
    .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-danger-outline { padding: 6px 12px; background: transparent; color: #ef4444; border: 1px solid #ef4444; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
    .btn-danger-outline:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-sm { padding: 5px 12px; font-size: 0.8rem; }
    .btn-switch { padding: 5px 12px; background: transparent; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; font-size: 0.8rem; cursor: pointer; }
    .btn-switch:hover:not(:disabled) { background: var(--tui-background-neutral-1, #f9fafb); }
    .btn-switch:disabled { opacity: 0.5; cursor: not-allowed; }
    .create-form { border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 8px; padding: 20px; margin-bottom: 24px; display: flex; flex-direction: column; gap: 16px; }
    .create-form h2 { font-size: 1rem; font-weight: 600; margin: 0; }
    .field { display: flex; flex-direction: column; gap: 4px; }
    .field label { font-size: 0.875rem; font-weight: 500; }
    .field input, .field textarea { padding: 8px 10px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; font-size: 0.875rem; width: 100%; box-sizing: border-box; }
    .required { color: #ef4444; }
    .hint { font-size: 0.78rem; color: var(--tui-text-secondary, #6b7280); font-weight: 400; }
    .form-actions { display: flex; gap: 8px; justify-content: flex-end; }
    .error { color: #ef4444; font-size: 0.875rem; margin: 0; }
    .workspace-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
    .workspace-card { border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 8px; overflow: hidden; }
    .workspace-card--deleted { border-color: #fca5a5; background: #fff7ed; }
    .workspace-main { display: flex; align-items: center; justify-content: space-between; padding: 4px 12px 4px 0; }
    .workspace-link { display: flex; align-items: center; gap: 12px; padding: 12px 16px; text-decoration: none; color: inherit; flex: 1; min-width: 0; }
    .workspace-link:hover { background: var(--tui-background-neutral-1, #f9fafb); }
    .ws-initial { width: 40px; height: 40px; border-radius: 8px; background: var(--tui-background-accent-1, #246fe0); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.1rem; flex-shrink: 0; }
    .ws-info { flex: 1; min-width: 0; }
    .ws-name-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .ws-deleted-note { font-size: 0.78rem; color: #9a3412; margin-top: 2px; display: block; }
    .ws-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
    .role-badge { font-size: 0.7rem; font-weight: 600; border-radius: 4px; padding: 2px 6px; text-transform: uppercase; letter-spacing: 0.03em; }
    .role-badge--owner { background: #ede9fe; color: #5b21b6; }
    .role-badge--member { background: #f3f4f6; color: #374151; }
    .active-badge { font-size: 0.75rem; color: #16a34a; font-weight: 500; background: #d1fae5; border-radius: 4px; padding: 2px 8px; }
    .badge { font-size: 0.72rem; border-radius: 4px; padding: 2px 6px; }
    .badge--warn { background: #fef3c7; color: #92400e; }
    .loading, .empty { color: var(--tui-text-secondary, #6b7280); }
  `],
})
export class WorkspacesComponent implements OnInit {
  private readonly wsService = inject(WorkspaceService);
  private readonly router = inject(Router);
  private readonly confirm = inject(ConfirmDialogService);
  readonly userService = inject(UserService);

  readonly workspaces = signal<WorkspaceDetail[]>([]);
  readonly isLoading = signal(true);
  readonly showForm = signal(false);
  readonly isCreating = signal(false);
  readonly createError = signal<string | null>(null);
  readonly isSwitching = signal(false);
  readonly actingId = signal<string | null>(null);
  readonly actionError = signal('');

  newName = '';
  newSlug = '';
  newDescription = '';

  readonly currentUserId = computed(() => this.userService.currentUser()?.id ?? '');

  isOwner(ws: WorkspaceDetail): boolean {
    return ws.owner.id === this.currentUserId();
  }

  ngOnInit(): void {
    this.wsService.list().subscribe({
      next: ws => { this.workspaces.set(ws); this.isLoading.set(false); },
      error: () => this.isLoading.set(false),
    });
  }

  cancelCreate(): void {
    this.showForm.set(false);
    this.newName = '';
    this.newSlug = '';
    this.newDescription = '';
    this.createError.set(null);
  }

  submitCreate(): void {
    const name = this.newName.trim();
    if (!name) return;
    this.isCreating.set(true);
    this.createError.set(null);
    const payload: { name: string; slug?: string; description?: string } = { name };
    if (this.newSlug.trim()) payload.slug = this.newSlug.trim();
    if (this.newDescription.trim()) payload.description = this.newDescription.trim();
    this.wsService.create(payload).subscribe({
      next: ws => {
        this.workspaces.update(list => [ws, ...list]);
        this.isCreating.set(false);
        this.cancelCreate();
        this.router.navigate(['/workspaces', ws.slug]);
      },
      error: (err) => {
        const detail = err?.error?.detail ?? err?.error?.name?.[0] ?? 'Failed to create workspace.';
        this.createError.set(detail);
        this.isCreating.set(false);
      },
    });
  }

  switchTo(ws: WorkspaceDetail): void {
    if (this.isSwitching()) return;
    this.isSwitching.set(true);
    this.userService.switchWorkspace({
      id: ws.id, slug: ws.slug, name: ws.name, plan: ws.plan, is_personal: ws.is_personal,
    }).subscribe({
      next: () => {
        this.isSwitching.set(false);
        this.router.navigate(['/home']);
      },
      error: () => this.isSwitching.set(false),
    });
  }

  deleteWs(ws: WorkspaceDetail): void {
    this.confirm.confirm('Schedule this workspace for deletion? You have 30 days to restore it.').subscribe(ok => {
      if (!ok) return;
      this.actingId.set(ws.id);
      this.actionError.set('');
      this.wsService.delete(ws.slug).subscribe({
        next: updated => {
          this.workspaces.update(list => list.map(w => w.id === updated.id ? updated : w));
          this.actingId.set(null);
        },
        error: (err) => {
          this.actionError.set(err?.error?.detail ?? 'Failed to delete workspace.');
          this.actingId.set(null);
        },
      });
    });
  }

  restoreWs(ws: WorkspaceDetail): void {
    this.actingId.set(ws.id);
    this.actionError.set('');
    this.wsService.restore(ws.slug).subscribe({
      next: updated => {
        this.workspaces.update(list => list.map(w => w.id === updated.id ? updated : w));
        this.actingId.set(null);
      },
      error: (err) => {
        this.actionError.set(err?.error?.detail ?? 'Failed to restore workspace.');
        this.actingId.set(null);
      },
    });
  }
}
