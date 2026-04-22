import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { DatePipe } from '@angular/common';
import { TuiIcon } from '@taiga-ui/core';
import { WorkspaceService, WorkspaceMember, WorkspaceInvitation } from '../../services/workspace.service';
import { UserService } from '../../services/user.service';
import { ConfirmDialogService } from '../../services/confirm-dialog.service';

type Tab = 'members' | 'invites' | 'link';

@Component({
  selector: 'app-workspace-members',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, FormsModule, DatePipe, TuiIcon],
  template: `
    <div class="page">
      <header class="page-header">
        <a [routerLink]="['/workspaces', slug()]" class="back-link">
          <tui-icon icon="@tui.arrow-left" /> Workspace settings
        </a>
        <h1>Members</h1>
      </header>

      <div class="tabs">
        <button class="tab" [class.tab--active]="activeTab() === 'members'" (click)="activeTab.set('members')">
          Members ({{ members().length }})
        </button>
        @if (canManage()) {
          <button class="tab" [class.tab--active]="activeTab() === 'invites'" (click)="activeTab.set('invites')">
            Pending invites @if (pendingEmailInvites().length > 0) { <span class="tab-badge">{{ pendingEmailInvites().length }}</span> }
          </button>
          <button class="tab" [class.tab--active]="activeTab() === 'link'" (click)="activeTab.set('link')">
            Invite link
          </button>
        }
      </div>

      @if (activeTab() === 'members') {
        @if (canManage()) {
          <section class="section">
            <h2>Invite by email</h2>
            <div class="invite-row">
              <input class="input input--grow" [(ngModel)]="inviteEmail" type="email" placeholder="name@example.com" [disabled]="inviting()" />
              <select class="select" [(ngModel)]="inviteRole" [disabled]="inviting()">
                <option value="MEMBER">Member</option>
                <option value="ADMIN">Admin</option>
              </select>
              <button class="btn-primary" (click)="sendEmailInvite()" [disabled]="!inviteEmail.trim() || inviting()">
                {{ inviting() ? 'Sending…' : 'Send invite' }}
              </button>
            </div>
            @if (inviteError()) { <p class="error">{{ inviteError() }}</p> }
            @if (inviteSuccess()) { <p class="success">{{ inviteSuccess() }}</p> }

            <div class="add-by-id-toggle">
              <button class="btn-text" (click)="showAddById.update(v => !v)">
                <tui-icon [icon]="showAddById() ? '@tui.chevron-up' : '@tui.chevron-down'" />
                Add by user ID
              </button>
            </div>
            @if (showAddById()) {
              <form class="add-id-form" [formGroup]="addForm" (ngSubmit)="addMemberById()">
                <input class="input input--grow" formControlName="userId" type="text" placeholder="User UUID" />
                <button class="btn-secondary" type="submit" [disabled]="addForm.invalid || adding()">
                  {{ adding() ? 'Adding…' : 'Add' }}
                </button>
              </form>
              @if (addError()) { <p class="error">{{ addError() }}</p> }
            }
          </section>
        }

        <section class="section">
          @if (isLoading()) {
            <p class="muted">Loading…</p>
          } @else if (members().length === 0) {
            <p class="muted">No members found.</p>
          } @else {
            <ul class="member-list">
              @for (m of members(); track m.id) {
                <li class="member-item">
                  <div class="member-info">
                    <span class="avatar">{{ m.user.display_name[0]?.toUpperCase() }}</span>
                    <div>
                      <strong>{{ m.user.display_name }}</strong>
                      <span class="email">{{ m.user.email }}</span>
                    </div>
                  </div>
                  <div class="member-actions">
                    @if (canManage() && m.role !== 'OWNER') {
                      <select class="role-select" [ngModel]="m.role" (ngModelChange)="changeRole(m, $event)" [disabled]="acting()">
                        <option value="ADMIN">Admin</option>
                        <option value="MEMBER">Member</option>
                      </select>
                    } @else {
                      <span class="role-badge" [class]="'role-badge--' + m.role.toLowerCase()">{{ m.role | titlecase }}</span>
                    }
                    @if (canManage() && m.user.id !== currentUserId() && m.role !== 'OWNER') {
                      <button class="btn-icon-danger" (click)="removeMember(m)" title="Remove member" [disabled]="acting()">
                        <tui-icon icon="@tui.trash" />
                      </button>
                    }
                  </div>
                </li>
              }
            </ul>
          }
        </section>
      }

      @else if (activeTab() === 'invites') {
        <section class="section">
          <h2>Pending email invitations</h2>
          @if (pendingEmailInvites().length === 0) {
            <p class="muted">No pending invitations.</p>
          } @else {
            <ul class="invite-list">
              @for (inv of pendingEmailInvites(); track inv.id) {
                <li class="invite-item">
                  <div class="invite-details">
                    <strong>{{ inv.email }}</strong>
                    <div class="invite-meta">
                      <span class="role-badge" [class]="'role-badge--' + inv.role_to_grant.toLowerCase()">{{ inv.role_to_grant | titlecase }}</span>
                      @if (inv.invited_by) { <span class="muted">by {{ inv.invited_by.display_name }}</span> }
                      <span class="muted">sent {{ inv.created_at | date:'mediumDate' }}</span>
                      @if (inv.expires_at) { <span class="muted">expires {{ inv.expires_at | date:'mediumDate' }}</span> }
                    </div>
                  </div>
                  <button class="btn-danger-outline btn-sm" (click)="revokeInvitation(inv)" [disabled]="acting()">Revoke</button>
                </li>
              }
            </ul>
          }
        </section>
      }

      @else if (activeTab() === 'link') {
        <section class="section">
          <h2>Invite link</h2>
          @if (activeLinkInvite(); as link) {
            <div class="link-active">
              <div class="link-info">
                <span class="role-badge" [class]="'role-badge--' + link.role_to_grant.toLowerCase()">{{ link.role_to_grant | titlecase }}</span>
                <span class="muted">{{ link.use_count }} use{{ link.use_count !== 1 ? 's' : '' }}</span>
                @if (link.max_uses) { <span class="muted">/ {{ link.max_uses }} max</span> }
                @if (link.expires_at) { <span class="muted">· expires {{ link.expires_at | date:'mediumDate' }}</span> }
              </div>
              <p class="muted link-note">An active invite link exists. Revoke it to generate a new one.</p>
              <button class="btn-danger-outline" (click)="revokeInvitation(link)" [disabled]="acting()">Revoke link</button>
            </div>
          } @else if (generatedToken()) {
            <p class="muted">Copy this link — it won't be shown again after you leave this page.</p>
            <div class="token-row">
              <input class="input input--grow input--mono" readonly [value]="inviteUrl()" />
              <button class="btn-secondary" (click)="copyLink()">{{ copied() ? 'Copied!' : 'Copy' }}</button>
            </div>
          } @else {
            <div class="generate-form">
              <div class="field-row">
                <label class="field-label">Role</label>
                <select class="select" [(ngModel)]="linkRole">
                  <option value="MEMBER">Member</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
              <div class="field-row">
                <label class="field-label">Max uses <span class="hint">(leave blank for unlimited)</span></label>
                <input class="input input--short" type="number" min="1" [(ngModel)]="linkMaxUses" placeholder="Unlimited" />
              </div>
              <div class="field-row">
                <label class="field-label">Expires <span class="hint">(leave blank for no expiry)</span></label>
                <input class="input" type="datetime-local" [(ngModel)]="linkExpiresAt" />
              </div>
              @if (linkError()) { <p class="error">{{ linkError() }}</p> }
              <button class="btn-primary" (click)="generateLink()" [disabled]="generatingLink()">
                {{ generatingLink() ? 'Generating…' : 'Generate link' }}
              </button>
            </div>
          }
        </section>
      }

      @if (actionError()) { <p class="error action-error">{{ actionError() }}</p> }
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 680px; margin: 0 auto; }
    .page-header { margin-bottom: 24px; }
    .back-link { display: flex; align-items: center; gap: 4px; color: var(--tui-text-secondary, #6b7280); text-decoration: none; font-size: 0.875rem; margin-bottom: 8px; }
    h1 { font-size: 1.5rem; font-weight: 700; margin: 0; }
    h2 { font-size: 1rem; font-weight: 600; margin: 0 0 14px; }

    .tabs { display: flex; gap: 2px; border-bottom: 1px solid var(--tui-border-normal, #e5e7eb); margin-bottom: 20px; }
    .tab { padding: 8px 16px; border: none; background: none; cursor: pointer; font-size: 0.875rem; color: var(--tui-text-secondary, #6b7280); border-bottom: 2px solid transparent; margin-bottom: -1px; display: flex; align-items: center; gap: 6px; }
    .tab--active { color: var(--tui-background-accent-1, #246fe0); border-bottom-color: var(--tui-background-accent-1, #246fe0); font-weight: 500; }
    .tab-badge { background: #ef4444; color: #fff; border-radius: 10px; padding: 0 6px; font-size: 0.7rem; font-weight: 600; }

    .section { margin-bottom: 20px; padding: 20px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 8px; }

    .invite-row { display: flex; gap: 8px; align-items: center; }
    .invite-row .input--grow { flex: 1; min-width: 0; }
    .input { padding: 8px 12px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; font-size: 0.875rem; outline: none; box-sizing: border-box; }
    .input:focus { border-color: var(--tui-background-accent-1, #246fe0); }
    .input--grow { flex: 1; min-width: 0; }
    .input--short { width: 120px; }
    .input--mono { font-family: monospace; font-size: 0.8rem; }
    .select { padding: 8px 10px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; font-size: 0.875rem; background: #fff; }

    .add-by-id-toggle { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--tui-border-normal, #e5e7eb); }
    .btn-text { background: none; border: none; cursor: pointer; display: flex; align-items: center; gap: 4px; font-size: 0.8rem; color: var(--tui-text-secondary, #6b7280); padding: 2px 0; }
    .btn-text:hover { color: var(--tui-text-primary, #111827); }
    .add-id-form { display: flex; gap: 8px; margin-top: 10px; }

    .btn-primary { padding: 8px 16px; background: var(--tui-background-accent-1, #246fe0); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.875rem; white-space: nowrap; flex-shrink: 0; }
    .btn-primary:disabled { opacity: 0.5; cursor: default; }
    .btn-secondary { padding: 8px 14px; background: transparent; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; cursor: pointer; font-size: 0.875rem; white-space: nowrap; flex-shrink: 0; }
    .btn-secondary:disabled { opacity: 0.5; cursor: default; }
    .btn-danger-outline { padding: 6px 12px; background: transparent; color: #ef4444; border: 1px solid #ef4444; border-radius: 6px; cursor: pointer; font-size: 0.875rem; white-space: nowrap; }
    .btn-danger-outline:disabled { opacity: 0.5; cursor: default; }
    .btn-sm { font-size: 0.8rem; padding: 4px 10px; }
    .btn-icon-danger { padding: 6px; background: none; border: none; cursor: pointer; color: var(--tui-status-negative, #ef4444); border-radius: 4px; }
    .btn-icon-danger:hover:not(:disabled) { background: #fef2f2; }
    .btn-icon-danger:disabled { opacity: 0.4; cursor: default; }

    .member-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
    .member-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; gap: 12px; }
    .member-info { display: flex; align-items: center; gap: 10px; min-width: 0; }
    .avatar { width: 32px; height: 32px; border-radius: 50%; background: var(--tui-background-accent-1, #246fe0); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.875rem; flex-shrink: 0; }
    .email { display: block; font-size: 0.78rem; color: var(--tui-text-secondary, #6b7280); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .member-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
    .role-select { padding: 4px 8px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 4px; font-size: 0.8rem; background: #fff; }

    .role-badge { font-size: 0.72rem; font-weight: 600; border-radius: 4px; padding: 2px 7px; text-transform: uppercase; letter-spacing: 0.03em; }
    .role-badge--owner { background: #ede9fe; color: #5b21b6; }
    .role-badge--admin { background: #d1fae5; color: #065f46; }
    .role-badge--member { background: #f3f4f6; color: #374151; }

    .invite-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px; }
    .invite-item { display: flex; align-items: center; justify-content: space-between; padding: 12px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 6px; gap: 12px; }
    .invite-details { min-width: 0; flex: 1; }
    .invite-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 4px; }

    .link-active { display: flex; flex-direction: column; gap: 12px; }
    .link-info { display: flex; align-items: center; gap: 8px; }
    .link-note { margin: 0; }
    .token-row { display: flex; gap: 8px; }
    .generate-form { display: flex; flex-direction: column; gap: 14px; }
    .field-row { display: flex; flex-direction: column; gap: 4px; }
    .field-label { font-size: 0.875rem; font-weight: 500; }
    .hint { font-size: 0.78rem; font-weight: 400; color: var(--tui-text-secondary, #6b7280); }

    .muted { color: var(--tui-text-secondary, #6b7280); font-size: 0.875rem; margin: 0; }
    .error { color: #ef4444; font-size: 0.875rem; margin-top: 8px; }
    .success { color: #16a34a; font-size: 0.875rem; margin-top: 8px; }
    .action-error { margin-top: 16px; }
  `],
})
export class WorkspaceMembersComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly wsService = inject(WorkspaceService);
  private readonly userService = inject(UserService);
  private readonly confirm = inject(ConfirmDialogService);
  private readonly fb = inject(FormBuilder);

  readonly slug = signal('');
  readonly members = signal<WorkspaceMember[]>([]);
  readonly invitations = signal<WorkspaceInvitation[]>([]);
  readonly isLoading = signal(true);
  readonly acting = signal(false);
  readonly actionError = signal('');
  readonly activeTab = signal<Tab>('members');

  // Email invite
  inviteEmail = '';
  inviteRole = 'MEMBER';
  readonly inviting = signal(false);
  readonly inviteError = signal('');
  readonly inviteSuccess = signal('');

  // Add by user ID
  readonly showAddById = signal(false);
  readonly addForm = this.fb.nonNullable.group({ userId: ['', Validators.required] });
  readonly adding = signal(false);
  readonly addError = signal('');

  // Invite link
  linkRole = 'MEMBER';
  linkMaxUses: number | null = null;
  linkExpiresAt = '';
  readonly generatingLink = signal(false);
  readonly generatedToken = signal('');
  readonly linkError = signal('');
  readonly copied = signal(false);

  readonly currentUserId = computed(() => this.userService.currentUser()?.id ?? '');

  readonly myRole = computed(() => {
    const uid = this.currentUserId();
    return this.members().find(m => m.user.id === uid)?.role ?? null;
  });

  readonly canManage = computed(() => {
    const r = this.myRole();
    return r === 'OWNER' || r === 'ADMIN';
  });

  readonly pendingEmailInvites = computed(() =>
    this.invitations().filter(i => i.kind === 'email'),
  );

  readonly activeLinkInvite = computed(() =>
    this.invitations().find(i => i.kind === 'link') ?? null,
  );

  readonly inviteUrl = computed(() =>
    `${window.location.origin}/invites/${this.generatedToken()}`,
  );

  ngOnInit(): void {
    this.slug.set(this.route.snapshot.paramMap.get('slug') ?? '');
    this.loadMembers();
    this.loadInvitations();
  }

  private loadMembers(): void {
    this.isLoading.set(true);
    this.wsService.listMembers(this.slug()).subscribe({
      next: m => { this.members.set(m); this.isLoading.set(false); },
      error: () => this.isLoading.set(false),
    });
  }

  private loadInvitations(): void {
    this.wsService.listInvitations(this.slug()).subscribe({
      next: inv => this.invitations.set(inv),
      error: () => {},
    });
  }

  sendEmailInvite(): void {
    const email = this.inviteEmail.trim();
    if (!email || this.inviting()) return;
    this.inviting.set(true);
    this.inviteError.set('');
    this.inviteSuccess.set('');
    this.wsService.createEmailInvite(this.slug(), email, this.inviteRole).subscribe({
      next: () => {
        this.inviting.set(false);
        this.inviteSuccess.set(`Invitation sent to ${email}`);
        this.inviteEmail = '';
        this.loadInvitations();
      },
      error: (err) => {
        this.inviting.set(false);
        this.inviteError.set(err?.error?.detail ?? 'Failed to send invite.');
      },
    });
  }

  addMemberById(): void {
    if (this.addForm.invalid || this.adding()) return;
    this.adding.set(true);
    this.addError.set('');
    this.wsService.addMember(this.slug(), this.addForm.getRawValue().userId).subscribe({
      next: () => {
        this.adding.set(false);
        this.addForm.reset();
        this.loadMembers();
      },
      error: (err) => {
        this.adding.set(false);
        this.addError.set(err?.error?.detail ?? 'Failed to add member.');
      },
    });
  }

  changeRole(member: WorkspaceMember, newRole: 'ADMIN' | 'MEMBER'): void {
    this.wsService.updateMemberRole(this.slug(), member.user.id, newRole).subscribe({
      next: updated => this.members.update(list => list.map(m => m.id === updated.id ? updated : m)),
      error: (err) => this.actionError.set(err?.error?.detail ?? 'Failed to update role.'),
    });
  }

  removeMember(member: WorkspaceMember): void {
    this.confirm.confirm(`Remove ${member.user.display_name} from this workspace?`).subscribe(ok => {
      if (!ok) return;
      this.acting.set(true);
      this.wsService.removeMember(this.slug(), member.user.id).subscribe({
        next: () => { this.acting.set(false); this.loadMembers(); },
        error: (err) => { this.acting.set(false); this.actionError.set(err?.error?.detail ?? 'Failed to remove member.'); },
      });
    });
  }

  revokeInvitation(inv: WorkspaceInvitation): void {
    this.acting.set(true);
    this.wsService.revokeInvitation(this.slug(), inv.id).subscribe({
      next: () => { this.acting.set(false); this.generatedToken.set(''); this.loadInvitations(); },
      error: (err) => { this.acting.set(false); this.actionError.set(err?.error?.detail ?? 'Failed to revoke.'); },
    });
  }

  generateLink(): void {
    if (this.generatingLink()) return;
    this.generatingLink.set(true);
    this.linkError.set('');
    const maxUses = this.linkMaxUses ?? undefined;
    const expiresAt = this.linkExpiresAt.trim() || undefined;
    this.wsService.createInviteLink(this.slug(), this.linkRole, maxUses, expiresAt).subscribe({
      next: res => {
        this.generatingLink.set(false);
        this.generatedToken.set(res.token);
        this.loadInvitations();
      },
      error: (err) => {
        this.generatingLink.set(false);
        this.linkError.set(err?.error?.detail ?? 'Failed to generate link.');
      },
    });
  }

  copyLink(): void {
    navigator.clipboard.writeText(this.inviteUrl()).then(() => {
      this.copied.set(true);
      setTimeout(() => this.copied.set(false), 2000);
    });
  }
}
