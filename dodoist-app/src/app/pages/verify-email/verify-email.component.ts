import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

type State = 'verifying' | 'success' | 'error' | 'waiting';

@Component({
  selector: 'app-verify-email',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './verify-email.component.html',
  styleUrl: './verify-email.component.scss',
})
export class VerifyEmailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);

  readonly state = signal<State>('verifying');
  readonly message = signal('');
  readonly resending = signal(false);
  readonly resendDone = signal(false);

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token');
    if (!token) {
      this.state.set('waiting');
      return;
    }
    this.authService.verifyEmail(token).subscribe({
      next: res => {
        this.message.set(res.detail);
        this.state.set('success');
      },
      error: err => {
        this.message.set(err?.error?.detail ?? 'Verification failed. The link may have expired.');
        this.state.set('error');
      },
    });
  }

  resend(): void {
    if (this.resending()) return;
    this.resending.set(true);
    this.authService.resendVerification().subscribe({
      next: () => {
        this.resending.set(false);
        this.resendDone.set(true);
      },
      error: () => this.resending.set(false),
    });
  }
}
