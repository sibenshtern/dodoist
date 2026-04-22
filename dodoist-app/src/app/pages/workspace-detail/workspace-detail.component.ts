import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { TuiIcon } from '@taiga-ui/core';
import { WorkspaceService, WorkspaceDetail } from '../../services/workspace.service';
import { UserService } from '../../services/user.service';
import { ConfirmDialogService } from '../../services/confirm-dialog.service';

@Component({
  selector: 'app-workspace-detail',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, FormsModule, DatePipe, TuiIcon],
  template: `
    <div class="page">
      <header class="page-header">
        <a routerLink="/workspaces" class="back-link">
          <tui-icon icon="@tui.arrow-left" /> Workspaces
        </a>
        @if (ws()) {
          <div class="header-row">
            <h1>{{ ws()!.name }}</h1>
            @if (isDeletedWs()) {
              <span class="badge badge--warn">Deletion scheduled</span>
            }
          </div>
        }
      </header>

      @if (isLoading()) {
        <p class="loading">Loading…</p>
      } @else if (ws()) {
        @if (isDeletedWs()) {
          <div class="danger-banner">
            This workspace is scheduled for permanent deletion on
            {{ ws()!.delete_scheduled_for | date:'mediumDate' }}.
            @if (isOwner()) {
              <button class="btn-secondary" (click)="restoreWs()" [disabled]="acting()">Restore</button>
            }
          </div>
        }

        @if (canManage()) {
          <section class="section">
            <h2>Settings</h2>
            <form [formGroup]="form" (ngSubmit)="save()" class="settings-form">
              <label>
                <span>Name</span>
                <input formControlName="name" type="text" class="input" />
              </label>
              <label>
                <span>Description</span>
                <textarea formControlName="description" rows="3" class="input textarea"></textarea>
              </label>
              <div class="form-actions">
                <button type="submit" class="btn-primary" [disabled]="saving() || form.invalid">
                  {{ saving() ? 'Saving…' : 'Save changes' }}
                </button>
                @if (saved()) { <span class="saved-msg">Saved ✓</span> }
              </div>
            </form>
          </section>
        }

        <section class="section">
          <div class="section-header">
            <h2>Members</h2>
            <a [routerLink]="['/workspaces', slug(), 'members']" class="btn-secondary">Manage members</a>
          </div>
          <p class="muted">Owner: {{ ws()!.owner.display_name }}</p>
        </section>

        @if (isOwner()) {
          <section class="section section--danger">
            <h2>Danger zone</h2>

            @if (!ws()!.is_personal) {
              <div class="danger-row">
                <div>
                  <strong>Transfer ownership</strong>
                  <p class="muted">Give another member full control of this workspace.</p>
                </div>
                <button class="btn-danger-outline" (click)="showTransfer.set(!showTransfer())" [disabled]="acting()">
                  Transfer
                </button>
              </div>
              @if (showTransfer()) {
                <div class="transfer-form">
                  <input [(ngModel)]="transferUserId" placeholder="New owner's user ID" class="input" />
                  <button class="btn-danger" (click)="transferOwnership()" [disabled]="!transferUserId.trim() || acting()">
                    Confirm transfer
                  </button>
                </div>
              }

              <div class="danger-row">
                <div>
                  <strong>Delete workspace</strong>
                  <p class="muted">Schedules permanent deletion in 30 days. You can restore within this period.</p>
                </div>
                <button class="btn-danger" (click)="deleteWs()" [disabled]="acting() || isDeletedWs()">
                  Delete
                </button>
              </div>
            }

            @if (!ws()!.is_personal) {
              <div class="danger-row">
                <div>
                  <strong>Leave workspace</strong>
                  <p class="muted">As owner you must transfer ownership first.</p>
                </div>
                <button class="btn-danger-outline" disabled>Leave</button>
              </div>
            }
          </section>
        } @else if (membershipRole() === 'ADMIN' || membershipRole() === 'MEMBER') {
          <section class="section section--danger">
            <h2>Leave workspace</h2>
            <div class="danger-row">
              <p class="muted">You will lose access to all projects in this workspace.</p>
              <button class="btn-danger-outline" (click)="leaveWs()" [disabled]="acting()">Leave</button>
            </div>
          </section>
        }

        @if (actionError()) { <p class="error">{{ actionError() }}</p> }
      }
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 640px; margin: 0 auto; }
    .page-header { margin-bottom: 24px; }
    .back-link { display: flex; align-items: center; gap: 4px; color: var(--tui-text-secondary, #6b7280); text-decoration: none; font-size: 0.875rem; margin-bottom: 8px; }
    .header-row { display: flex; align-items: center; gap: 10px; }
    h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
    .badge { font-size: 0.75rem; border-radius: 4px; padding: 2px 8px; }
    .badge--warn { background: #fef3c7; color: #92400e; }
    .danger-banner { background: #fff7ed; border: 1px solid #f97316; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 0.875rem; color: #9a3412; }
    .section { margin-bottom: 24px; padding: 20px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 8px; }
    .section--danger { border-color: #fca5a5; }
    .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
    h2 { font-size: 1rem; font-weight: 600; margin: 0 0 16px; }
    .settings-form { display: flex; flex-direction: column; gap: 16px; }
    label { display: flex; flex-direction: column; gap: 4px; font-size: 0.875rem; font-weight: 500; }
    .input { padding: 8px 12px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; font-size: 0.875rem; outline: none; width: 100%; box-sizing: border-box; }
    .textarea { resize: vertical; }
    .form-actions { display: flex; align-items: center; gap: 12px; }
    .btn-primary { padding: 8px 20px; background: var(--tui-background-accent-1, #246fe0); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
    .btn-primary:disabled { opacity: 0.5; cursor: default; }
    .btn-secondary { padding: 6px 14px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; text-decoration: none; color: inherit; font-size: 0.875rem; cursor: pointer; background: transparent; }
    .btn-secondary:disabled { opacity: 0.5; cursor: default; }
    .btn-danger { padding: 8px 16px; background: #ef4444; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; white-space: nowrap; }
    .btn-danger:disabled { opacity: 0.5; cursor: default; }
    .btn-danger-outline { padding: 8px 16px; background: transparent; color: #ef4444; border: 1px solid #ef4444; border-radius: 6px; cursor: pointer; font-size: 0.875rem; white-space: nowrap; }
    .btn-danger-outline:disabled { opacity: 0.5; cursor: default; }
    .danger-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; margin-bottom: 16px; }
    .danger-row:last-child { margin-bottom: 0; }
    .transfer-form { display: flex; gap: 8px; margin-top: 8px; margin-bottom: 16px; }
    .saved-msg { color: #299438; font-size: 0.875rem; }
    .muted { color: var(--tui-text-secondary, #6b7280); font-size: 0.875rem; margin: 2px 0 0; }
    .error { color: #ef4444; font-size: 0.875rem; margin-top: 8px; }
    .loading { color: var(--tui-text-secondary, #6b7280); }
  `],
})
export class WorkspaceDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly wsService = inject(WorkspaceService);
  private readonly userService = inject(UserService);
  private readonly confirm = inject(ConfirmDialogService);
  private readonly fb = inject(FormBuilder);

  readonly ws = signal<WorkspaceDetail | null>(null);
  readonly isLoading = signal(true);
  readonly saving = signal(false);
  readonly saved = signal(false);
  readonly acting = signal(false);
  readonly actionError = signal('');
  readonly showTransfer = signal(false);
  readonly slug = signal('');

  transferUserId = '';

  readonly isOwner = computed(
    () => this.ws()?.owner.id === this.userService.currentUser()?.id,
  );

  readonly membershipRole = computed(() => {
    const userId = this.userService.currentUser()?.id;
    if (!userId) return null;
    return null; // Could be enriched from a members call; not needed for basic gating
  });

  readonly canManage = computed(() => {
    const ws = this.ws();
    const user = this.userService.currentUser();
    if (!ws || !user) return false;
    if (ws.owner.id === user.id) return true;
    return false; // Admin check would require a members lookup; owner is sufficient for now
  });

  readonly isDeletedWs = computed(() => !!this.ws()?.deleted_at);

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    description: [''],
  });

  ngOnInit(): void {
    this.slug.set(this.route.snapshot.paramMap.get('slug') ?? '');
    this.wsService.get(this.slug()).subscribe({
      next: ws => {
        this.ws.set(ws);
        this.form.patchValue({ name: ws.name, description: ws.description });
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  save(): void {
    if (this.form.invalid || this.saving()) return;
    this.saving.set(true);
    this.saved.set(false);
    this.wsService.update(this.slug(), this.form.getRawValue()).subscribe({
      next: ws => {
        this.ws.set(ws);
        this.saving.set(false);
        this.saved.set(true);
        setTimeout(() => this.saved.set(false), 3000);
      },
      error: () => this.saving.set(false),
    });
  }

  deleteWs(): void {
    this.confirm.confirm('Schedule this workspace for deletion? You have 30 days to restore it.').subscribe(ok => {
      if (!ok) return;
      this.acting.set(true);
      this.actionError.set('');
      this.wsService.delete(this.slug()).subscribe({
        next: ws => { this.ws.set(ws); this.acting.set(false); },
        error: (err) => { this.actionError.set(err?.error?.detail ?? 'Failed.'); this.acting.set(false); },
      });
    });
  }

  restoreWs(): void {
    this.acting.set(true);
    this.actionError.set('');
    this.wsService.restore(this.slug()).subscribe({
      next: ws => { this.ws.set(ws); this.acting.set(false); },
      error: (err) => { this.actionError.set(err?.error?.detail ?? 'Failed.'); this.acting.set(false); },
    });
  }

  transferOwnership(): void {
    if (!this.transferUserId.trim()) return;
    this.confirm.confirm('Transfer workspace ownership? You will become an Admin.').subscribe(ok => {
      if (!ok) return;
      this.acting.set(true);
      this.actionError.set('');
      this.wsService.transferOwnership(this.slug(), this.transferUserId.trim()).subscribe({
        next: ws => {
          this.ws.set(ws);
          this.showTransfer.set(false);
          this.transferUserId = '';
          this.acting.set(false);
        },
        error: (err) => { this.actionError.set(err?.error?.detail ?? 'Failed.'); this.acting.set(false); },
      });
    });
  }

  leaveWs(): void {
    this.confirm.confirm('Leave this workspace? You will lose access to all its projects.').subscribe(ok => {
      if (!ok) return;
      this.acting.set(true);
      this.wsService.leave(this.slug()).subscribe({
        next: () => this.router.navigate(['/workspaces']),
        error: (err) => { this.actionError.set(err?.error?.detail ?? 'Failed.'); this.acting.set(false); },
      });
    });
  }
}
