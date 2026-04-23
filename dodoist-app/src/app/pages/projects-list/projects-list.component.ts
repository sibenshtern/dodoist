import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TuiIcon } from '@taiga-ui/core';
import { ProjectsService, Project, ProjectCreatePayload } from '../../services/projects.service';
import { UserService } from '../../services/user.service';
import { switchMap, EMPTY } from 'rxjs';

const TYPE_LABELS: Record<string, string> = {
  kanban: 'Kanban',
  scrum: 'Scrum',
  personal: 'Personal',
};

const PROJECT_COLORS = [
  '#db4035', '#e88c30', '#fad000', '#4a90d9',
  '#884dff', '#2ecc71', '#1abc9c', '#e91e63',
];

@Component({
  selector: 'app-projects-list',
  standalone: true,
  imports: [TuiIcon, RouterLink, ReactiveFormsModule],
  templateUrl: './projects-list.component.html',
  styleUrl: './projects-list.component.scss',
})
export class ProjectsListComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly projectsService = inject(ProjectsService);
  private readonly userService = inject(UserService);

  readonly projects = signal<Project[]>([]);
  readonly isLoading = signal(true);
  readonly showDialog = signal(false);
  readonly isSaving = signal(false);
  readonly saveError = signal('');

  private workspaceSlug = '';

  readonly form = this.fb.nonNullable.group({
    name:        ['', Validators.required],
    key:         ['', [Validators.required, Validators.pattern(/^[A-Z0-9]{2,10}$/i)]],
    type:        ['kanban', Validators.required],
    color:       [PROJECT_COLORS[0]],
    description: [''],
    is_private:  [false],
  });

  readonly colors = PROJECT_COLORS;
  readonly typeLabel = (t: string) => TYPE_LABELS[t] ?? t;

  readonly filteredProjects = computed(() => this.projects());

  ngOnInit(): void {
    const ws = this.userService.currentWorkspace();
    const load$ = ws
      ? this.projectsService.list(ws.slug)
      : this.userService.loadWorkspaces().pipe(
          switchMap(workspaces => {
            const w = workspaces.find(x => x.is_personal) ?? workspaces[0];
            return w ? this.projectsService.list(w.slug) : EMPTY;
          }),
        );

    load$.subscribe({
      next: projects => {
        this.projects.set(projects);
        this.isLoading.set(false);
        this.workspaceSlug = this.userService.currentWorkspace()?.slug ?? '';
      },
      error: () => this.isLoading.set(false),
    });
  }

  openDialog(): void {
    this.form.reset({ name: '', key: '', type: 'kanban', color: PROJECT_COLORS[0], description: '', is_private: false });
    this.saveError.set('');
    this.showDialog.set(true);
  }

  closeDialog(): void {
    this.showDialog.set(false);
  }

  autoKey(): void {
    const name = this.form.controls.name.value;
    const key = name
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, '')
      .slice(0, 6);
    this.form.controls.key.setValue(key);
  }

  selectColor(color: string): void {
    this.form.controls.color.setValue(color);
  }

  submit(): void {
    if (this.form.invalid || this.isSaving()) return;
    this.isSaving.set(true);
    this.saveError.set('');
    const raw = this.form.getRawValue();
    const payload: ProjectCreatePayload = {
      name:        raw.name,
      key:         raw.key.toUpperCase(),
      type:        raw.type,
      color:       raw.color,
      description: raw.description,
      is_private:  raw.is_private,
    };
    this.projectsService.create(this.workspaceSlug, payload).subscribe({
      next: project => {
        this.projects.update(list => [project, ...list]);
        this.isSaving.set(false);
        this.showDialog.set(false);
      },
      error: err => {
        this.saveError.set(err?.error?.detail ?? 'Failed to create project.');
        this.isSaving.set(false);
      },
    });
  }
}
