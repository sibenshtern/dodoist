import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './reset-password.component.html',
  styleUrl: './reset-password.component.scss',
})
export class ResetPasswordComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);

  private token = '';
  readonly hasToken = signal(false);
  readonly isSubmitting = signal(false);
  readonly success = signal(false);
  readonly error = signal('');

  readonly form = this.fb.nonNullable.group({
    new_password:     ['', [Validators.required, Validators.minLength(8)]],
    confirm_password: ['', Validators.required],
  });

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token') ?? '';
    this.token = token;
    this.hasToken.set(!!token);
  }

  submit(): void {
    if (this.form.invalid || this.isSubmitting()) return;
    const { new_password, confirm_password } = this.form.getRawValue();
    if (new_password !== confirm_password) {
      this.error.set('Passwords do not match.');
      return;
    }
    this.isSubmitting.set(true);
    this.error.set('');
    this.authService.resetPassword(this.token, new_password).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.success.set(true);
        setTimeout(() => this.router.navigate(['/login']), 2500);
      },
      error: err => {
        this.error.set(err?.error?.detail ?? 'Reset failed. The link may have expired.');
        this.isSubmitting.set(false);
      },
    });
  }
}
