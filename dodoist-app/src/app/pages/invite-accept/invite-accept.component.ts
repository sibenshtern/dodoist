import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { WorkspaceService } from '../../services/workspace.service';
import { UserService } from '../../services/user.service';

@Component({
  selector: 'app-invite-accept',
  standalone: true,
  imports: [],
  template: `
    <div class="accept-page">
      @if (error()) {
        <div class="card">
          <h1>Invitation error</h1>
          <p class="error-msg">{{ error() }}</p>
          <a href="/workspaces" class="btn-primary">Go to workspaces</a>
        </div>
      } @else {
        <div class="card">
          <div class="spinner"></div>
          <p class="status">{{ status() }}</p>
        </div>
      }
    </div>
  `,
  styles: [`
    .accept-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: var(--tui-background-base, #f9fafb); }
    .card { background: #fff; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 12px; padding: 40px 32px; text-align: center; max-width: 360px; width: 100%; display: flex; flex-direction: column; align-items: center; gap: 16px; }
    h1 { font-size: 1.25rem; font-weight: 700; margin: 0; }
    .status { color: var(--tui-text-secondary, #6b7280); margin: 0; }
    .error-msg { color: #ef4444; font-size: 0.9rem; margin: 0; }
    .btn-primary { padding: 10px 24px; background: var(--tui-background-accent-1, #246fe0); color: #fff; border-radius: 6px; text-decoration: none; font-size: 0.875rem; font-weight: 500; }
    .spinner { width: 32px; height: 32px; border: 3px solid var(--tui-border-normal, #e5e7eb); border-top-color: var(--tui-background-accent-1, #246fe0); border-radius: 50%; animation: spin 0.8s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  `],
})
export class InviteAcceptComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly authService = inject(AuthService);
  private readonly wsService = inject(WorkspaceService);
  private readonly userService = inject(UserService);

  readonly status = signal('Accepting invitation…');
  readonly error = signal('');

  ngOnInit(): void {
    const token = this.route.snapshot.paramMap.get('token') ?? '';
    if (!token) {
      this.error.set('Invalid invitation link.');
      return;
    }

    if (!this.authService.isAuthenticated()) {
      this.router.navigate(['/signup'], { queryParams: { invite: token } });
      return;
    }

    this.wsService.acceptInvitation(token).subscribe({
      next: ws => {
        this.status.set(`Joined "${ws.name}"! Redirecting…`);
        this.userService.switchWorkspace({
          id: ws.id, slug: ws.slug, name: ws.name, plan: ws.plan, is_personal: ws.is_personal,
        }).subscribe({
          next: () => this.router.navigate(['/home']),
          error: () => this.router.navigate(['/home']),
        });
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'This invitation is invalid or has expired.');
      },
    });
  }
}
