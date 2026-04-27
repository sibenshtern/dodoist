import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { DatePipe, TitleCasePipe } from '@angular/common';
import { TuiIcon } from '@taiga-ui/core';
import {
  WorkspaceDetail,
  WorkspaceInvitation,
  WorkspaceMember,
  WorkspaceService,
} from '../../services/workspace.service';
import { UserService } from '../../services/user.service';
import { ConfirmDialogService } from '../../services/confirm-dialog.service';

@Component({
  selector: 'app-workspace-detail',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, FormsModule, DatePipe, TitleCasePipe, TuiIcon],
  templateUrl: './workspace-detail.component.html',
  styleUrl: './workspace-detail.component.scss',
})
export class WorkspaceDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly wsService = inject(WorkspaceService);
  private readonly userService = inject(UserService);
  private readonly confirm = inject(ConfirmDialogService);
  private readonly fb = inject(FormBuilder);

  readonly ws = signal<WorkspaceDetail | null>(null);
  readonly members = signal<WorkspaceMember[]>([]);
  readonly invitations = signal<WorkspaceInvitation[]>([]);
  readonly isLoading = signal(true);
  readonly saving = signal(false);
  readonly saved = signal(false);
  readonly acting = signal(false);
  readonly actionError = signal('');
  readonly showTransfer = signal(false);
  readonly showEmailInvite = signal(false);
  readonly generatedLink = signal('');
  readonly slug = signal('');

  transferMemberId = '';
  inviteEmail = '';
  inviteRole: 'ADMIN' | 'MEMBER' = 'MEMBER';

  readonly isOwner = computed(
    () => this.ws()?.owner.id === this.userService.currentUser()?.id,
  );

  readonly currentUserRole = computed(() => {
    const userId = this.userService.currentUser()?.id;
    return this.members().find(m => m.user.id === userId)?.role ?? null;
  });

  readonly canManage = computed(
    () => this.isOwner() || this.currentUserRole() === 'ADMIN',
  );

  readonly isDeletedWs = computed(() => !!this.ws()?.deleted_at);

  readonly transferableMembers = computed(() =>
    this.members().filter(m => m.role !== 'OWNER'),
  );

  readonly pendingInvitations = computed(() =>
    this.invitations().filter(i => !i.accepted_at && !i.revoked_at),
  );

  readonly visibleMembers = computed(() => this.members().slice(0, 8));
  readonly overflowMemberCount = computed(() => Math.max(0, this.members().length - 8));

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
        this.loadMembers();
      },
      error: () => this.isLoading.set(false),
    });
  }

  private loadMembers(): void {
    this.wsService.listMembers(this.slug()).subscribe({
      next: members => {
        this.members.set(members);
        if (this.canManage()) this.loadInvitations();
      },
      error: () => {},
    });
  }

  private loadInvitations(): void {
    this.wsService.listInvitations(this.slug()).subscribe({
      next: inv => this.invitations.set(inv),
      error: () => {},
    });
  }

  save(): void {
    if (this.form.invalid || this.saving()) return;
    this.saving.set(true);
    this.saved.set(false);
    this.wsService.update(this.slug(), this.form.getRawValue()).subscribe({
      next: ws => {
        this.ws.set(ws);
        this.form.markAsPristine();
        this.saving.set(false);
        this.saved.set(true);
        setTimeout(() => this.saved.set(false), 3000);
      },
      error: () => this.saving.set(false),
    });
  }

  sendEmailInvite(): void {
    if (!this.inviteEmail.trim() || this.acting()) return;
    this.acting.set(true);
    this.actionError.set('');
    this.wsService.createEmailInvite(this.slug(), this.inviteEmail.trim(), this.inviteRole).subscribe({
      next: inv => {
        this.invitations.update(list => [inv, ...list]);
        this.inviteEmail = '';
        this.showEmailInvite.set(false);
        this.acting.set(false);
      },
      error: err => { this.actionError.set(err?.error?.detail ?? 'Failed to send invite.'); this.acting.set(false); },
    });
  }

  generateInviteLink(): void {
    if (this.acting()) return;
    this.acting.set(true);
    this.actionError.set('');
    this.wsService.createInviteLink(this.slug(), this.inviteRole).subscribe({
      next: res => {
        this.generatedLink.set(`${window.location.origin}/invites/${res.token}`);
        this.acting.set(false);
        this.loadInvitations();
      },
      error: err => { this.actionError.set(err?.error?.detail ?? 'Failed to generate link.'); this.acting.set(false); },
    });
  }

  copyLink(): void {
    navigator.clipboard.writeText(this.generatedLink()).catch(() => {});
  }

  revokeInvitation(id: string): void {
    this.wsService.revokeInvitation(this.slug(), id).subscribe({
      next: () => this.invitations.update(list => list.filter(i => i.id !== id)),
      error: err => this.actionError.set(err?.error?.detail ?? 'Failed to revoke.'),
    });
  }

  transferOwnership(): void {
    if (!this.transferMemberId) return;
    this.confirm.confirm('Transfer workspace ownership? You will become an Admin.').subscribe(ok => {
      if (!ok) return;
      this.acting.set(true);
      this.actionError.set('');
      this.wsService.transferOwnership(this.slug(), this.transferMemberId).subscribe({
        next: ws => {
          this.ws.set(ws);
          this.showTransfer.set(false);
          this.transferMemberId = '';
          this.acting.set(false);
          this.loadMembers();
        },
        error: err => { this.actionError.set(err?.error?.detail ?? 'Failed.'); this.acting.set(false); },
      });
    });
  }

  deleteWs(): void {
    this.confirm.confirm('Schedule this workspace for deletion? You have 30 days to restore it.').subscribe(ok => {
      if (!ok) return;
      this.acting.set(true);
      this.actionError.set('');
      this.wsService.delete(this.slug()).subscribe({
        next: ws => { this.ws.set(ws); this.acting.set(false); },
        error: err => { this.actionError.set(err?.error?.detail ?? 'Failed.'); this.acting.set(false); },
      });
    });
  }

  restoreWs(): void {
    this.acting.set(true);
    this.actionError.set('');
    this.wsService.restore(this.slug()).subscribe({
      next: ws => { this.ws.set(ws); this.acting.set(false); },
      error: err => { this.actionError.set(err?.error?.detail ?? 'Failed.'); this.acting.set(false); },
    });
  }

  leaveWs(): void {
    this.confirm.confirm('Leave this workspace? You will lose access to all its projects.').subscribe(ok => {
      if (!ok) return;
      this.acting.set(true);
      this.wsService.leave(this.slug()).subscribe({
        next: () => this.router.navigate(['/workspaces']),
        error: err => { this.actionError.set(err?.error?.detail ?? 'Failed.'); this.acting.set(false); },
      });
    });
  }

  initials(name: string): string {
    return name?.trim() ? name.trim()[0].toUpperCase() : '?';
  }
}
