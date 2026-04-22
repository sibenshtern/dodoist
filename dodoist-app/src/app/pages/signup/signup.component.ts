import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { TuiButton } from '@taiga-ui/core';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-signup',
  imports: [ReactiveFormsModule, RouterLink, TuiButton],
  templateUrl: './signup.component.html',
  styleUrl: './signup.component.scss',
})
export class SignupComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly showPassword = signal(false);
  readonly isLoading = signal(false);
  readonly serverError = signal<string | null>(null);
  readonly timezones = Intl.supportedValuesOf('timeZone');

  readonly form = this.fb.nonNullable.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    timezone: [Intl.DateTimeFormat().resolvedOptions().timeZone, Validators.required],
  });

  get nameInvalid(): boolean {
    const c = this.form.controls.name;
    return c.invalid && c.touched;
  }

  get emailInvalid(): boolean {
    const c = this.form.controls.email;
    return c.invalid && c.touched;
  }

  get passwordInvalid(): boolean {
    const c = this.form.controls.password;
    return c.invalid && c.touched;
  }

  submit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) return;

    const { name, email, password, timezone } = this.form.getRawValue();
    const inviteToken = this.route.snapshot.queryParamMap.get('invite') ?? undefined;
    this.isLoading.set(true);
    this.serverError.set(null);

    this.authService.register(email, password, name, timezone, inviteToken).subscribe({
      next: () => {
        this.router.navigate(['/verify-email']);
      },
      error: (err) => {
        const message = err.error?.detail ?? 'Registration failed. Please try again.';
        this.serverError.set(message);
        this.isLoading.set(false);
      },
    });
  }
}
