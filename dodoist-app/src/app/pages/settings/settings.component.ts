import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TuiIcon } from '@taiga-ui/core';
import { UserService, UserPreferences } from '../../services/user.service';

type Tab = 'profile' | 'preferences' | 'security';

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [TuiIcon, ReactiveFormsModule],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
})
export class SettingsComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  readonly userService = inject(UserService);

  readonly activeTab = signal<Tab>('profile');

  readonly profileSaving = signal(false);
  readonly profileSaved = signal(false);
  readonly profileError = signal('');

  readonly prefSaving = signal(false);
  readonly prefSaved = signal(false);
  readonly prefError = signal('');

  readonly pwSaving = signal(false);
  readonly pwSaved = signal(false);
  readonly pwError = signal('');

  readonly profileForm = this.fb.nonNullable.group({
    display_name: ['', Validators.required],
    timezone:     ['UTC'],
  });

  readonly prefForm = this.fb.nonNullable.group({
    theme:             ['system'],
    language:          ['en'],
    email_notif:       [true],
    push_notif:        [false],
    in_app_notif:      [true],
    digest_frequency:  ['realtime'],
    default_view:      ['list'],
  });

  readonly pwForm = this.fb.nonNullable.group({
    current_password: ['', Validators.required],
    new_password:     ['', [Validators.required, Validators.minLength(8)]],
  });

  ngOnInit(): void {
    const user = this.userService.currentUser();
    if (user) {
      this.profileForm.patchValue({ display_name: user.display_name, timezone: user.timezone });
      this.loadPreferences(user.id);
    } else {
      this.userService.loadCurrentUser().subscribe(u => {
        this.profileForm.patchValue({ display_name: u.display_name, timezone: u.timezone });
        this.loadPreferences(u.id);
      });
    }
  }

  private loadPreferences(userId: string): void {
    this.userService.getPreferences(userId).subscribe({
      next: (prefs: UserPreferences) => {
        this.prefForm.patchValue({
          theme:            prefs.theme,
          language:         prefs.language,
          email_notif:      prefs.notification_channels?.email ?? true,
          push_notif:       prefs.notification_channels?.push ?? false,
          in_app_notif:     prefs.notification_channels?.in_app ?? true,
          digest_frequency: prefs.digest_frequency,
          default_view:     prefs.default_view,
        });
      },
      error: console.error,
    });
  }

  setTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  saveProfile(): void {
    const user = this.userService.currentUser();
    if (!user || this.profileForm.invalid || this.profileSaving()) return;
    this.profileSaving.set(true);
    this.profileError.set('');
    this.profileSaved.set(false);
    const { display_name, timezone } = this.profileForm.getRawValue();
    this.userService.updateProfile(user.id, { display_name, timezone }).subscribe({
      next: () => {
        this.profileSaving.set(false);
        this.profileSaved.set(true);
        setTimeout(() => this.profileSaved.set(false), 2500);
      },
      error: err => {
        this.profileError.set(err?.error?.detail ?? 'Failed to save profile.');
        this.profileSaving.set(false);
      },
    });
  }

  savePreferences(): void {
    const user = this.userService.currentUser();
    if (!user || this.prefSaving()) return;
    this.prefSaving.set(true);
    this.prefError.set('');
    this.prefSaved.set(false);
    const raw = this.prefForm.getRawValue();
    this.userService.updatePreferences(user.id, {
      theme:            raw.theme,
      language:         raw.language,
      notification_channels: {
        email:  raw.email_notif,
        push:   raw.push_notif,
        in_app: raw.in_app_notif,
      },
      digest_frequency: raw.digest_frequency,
      default_view:     raw.default_view,
    }).subscribe({
      next: () => {
        this.prefSaving.set(false);
        this.prefSaved.set(true);
        setTimeout(() => this.prefSaved.set(false), 2500);
      },
      error: err => {
        this.prefError.set(err?.error?.detail ?? 'Failed to save preferences.');
        this.prefSaving.set(false);
      },
    });
  }

  changePassword(): void {
    const user = this.userService.currentUser();
    if (!user || this.pwForm.invalid || this.pwSaving()) return;
    this.pwSaving.set(true);
    this.pwError.set('');
    this.pwSaved.set(false);
    const { current_password, new_password } = this.pwForm.getRawValue();
    this.userService.changePassword(user.id, current_password, new_password).subscribe({
      next: () => {
        this.pwSaving.set(false);
        this.pwSaved.set(true);
        this.pwForm.reset();
        setTimeout(() => this.pwSaved.set(false), 2500);
      },
      error: err => {
        this.pwError.set(err?.error?.detail ?? 'Failed to change password.');
        this.pwSaving.set(false);
      },
    });
  }
}
