import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { SlicePipe } from '@angular/common';
import { TuiIcon } from '@taiga-ui/core';
import { ProjectsService, Project, ProjectMember } from '../../services/projects.service';
import { SprintsService, Sprint, SprintCreatePayload } from '../../services/sprints.service';
import { LabelsService, Label } from '../../services/labels.service';
import { CustomFieldsService, CustomField } from '../../services/custom-fields.service';
import { UserService } from '../../services/user.service';
import { switchMap, EMPTY } from 'rxjs';

type Tab = 'overview' | 'sprints' | 'members' | 'labels' | 'custom-fields' | 'settings';

const FIELD_TYPES = ['text', 'number', 'date', 'boolean', 'select'] as const;

@Component({
  selector: 'app-project-detail',
  standalone: true,
  imports: [TuiIcon, ReactiveFormsModule, RouterLink, SlicePipe],
  templateUrl: './project-detail.component.html',
  styleUrl: './project-detail.component.scss',
})
export class ProjectDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly fb = inject(FormBuilder);
  private readonly projectsService = inject(ProjectsService);
  private readonly sprintsService = inject(SprintsService);
  private readonly labelsService = inject(LabelsService);
  private readonly customFieldsService = inject(CustomFieldsService);
  readonly userService = inject(UserService);

  readonly projectId = signal('');
  readonly project = signal<Project | null>(null);
  readonly members = signal<ProjectMember[]>([]);
  readonly sprints = signal<Sprint[]>([]);
  readonly labels = signal<Label[]>([]);
  readonly customFields = signal<CustomField[]>([]);
  readonly isLoading = signal(true);
  readonly activeTab = signal<Tab>('overview');

  // Sprint dialog
  readonly showSprintDialog = signal(false);
  readonly sprintSaving = signal(false);
  readonly sprintError = signal('');

  // Sprint complete dialog
  readonly completingSprint = signal<Sprint | null>(null);
  readonly incompleteAction = signal<'backlog' | 'next_sprint'>('backlog');
  readonly nextSprintId = signal('');
  readonly completeError = signal('');
  readonly completeSaving = signal(false);

  // Member invite dialog
  readonly showMemberDialog = signal(false);
  readonly memberSaving = signal(false);
  readonly memberError = signal('');

  // Label dialog
  readonly showLabelDialog = signal(false);
  readonly editingLabel = signal<Label | null>(null);
  readonly labelSaving = signal(false);
  readonly labelError = signal('');

  // Custom field dialog
  readonly showFieldDialog = signal(false);
  readonly fieldSaving = signal(false);
  readonly fieldError = signal('');

  // Settings save state
  readonly settingsSaving = signal(false);
  readonly settingsSaved = signal(false);
  readonly settingsError = signal('');

  readonly fieldTypes = FIELD_TYPES;

  readonly plannedSprints = computed(() => this.sprints().filter(s => s.status === 'planned'));
  readonly activeSprints = computed(() => this.sprints().filter(s => s.status === 'active'));
  readonly completedSprints = computed(() => this.sprints().filter(s => s.status === 'completed'));

  readonly sprintForm = this.fb.nonNullable.group({
    name:       ['', Validators.required],
    goal:       [''],
    start_date: [''],
    end_date:   [''],
  });

  readonly memberForm = this.fb.nonNullable.group({
    user_id: ['', Validators.required],
    role:    ['DEV'],
  });

  readonly labelForm = this.fb.nonNullable.group({
    name:  ['', Validators.required],
    color: ['#6b7280'],
  });

  readonly fieldForm = this.fb.nonNullable.group({
    name:        ['', Validators.required],
    field_type:  ['text'],
    is_required: [false],
  });

  readonly settingsForm = this.fb.nonNullable.group({
    name:        ['', Validators.required],
    description: [''],
    color:       [''],
    is_private:  [false],
  });

  readonly labelColors = [
    '#ef4444','#f97316','#eab308','#22c55e',
    '#06b6d4','#3b82f6','#8b5cf6','#ec4899','#6b7280',
  ];

  readonly projectRoles = ['PO', 'PM', 'DEV', 'VIEWER', 'GUEST'];

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.projectId.set(id);
    this.loadAll(id);
  }

  private loadAll(id: string): void {
    this.projectsService.get(id).subscribe({
      next: p => {
        this.project.set(p);
        this.settingsForm.patchValue({
          name:        p.name,
          description: p.description,
          color:       p.color,
          is_private:  p.is_private,
        });
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
    this.projectsService.getMembers(id).subscribe({ next: m => this.members.set(m), error: console.error });
    this.sprintsService.list(id).subscribe({ next: s => this.sprints.set(s), error: console.error });
    this.customFieldsService.listFields(id).subscribe({ next: f => this.customFields.set(f), error: console.error });

    const ws = this.userService.currentWorkspace();
    const slug$ = ws
      ? [ws.slug]
      : null;
    if (slug$) {
      this.labelsService.list(slug$[0]).subscribe({ next: l => this.labels.set(l), error: console.error });
    } else {
      this.userService.loadWorkspaces().pipe(
        switchMap(workspaces => {
          const w = workspaces.find(x => x.is_personal) ?? workspaces[0];
          return w ? this.labelsService.list(w.slug) : EMPTY;
        }),
      ).subscribe({ next: l => this.labels.set(l), error: console.error });
    }
  }

  setTab(tab: Tab): void { this.activeTab.set(tab); }

  // ── Sprints ─────────────────────────────────────────────────────────────────

  openSprintDialog(): void {
    this.sprintForm.reset({ name: '', goal: '', start_date: '', end_date: '' });
    this.sprintError.set('');
    this.showSprintDialog.set(true);
  }

  closeSprintDialog(): void { this.showSprintDialog.set(false); }

  submitSprint(): void {
    if (this.sprintForm.invalid || this.sprintSaving()) return;
    this.sprintSaving.set(true);
    this.sprintError.set('');
    const raw = this.sprintForm.getRawValue();
    const payload: SprintCreatePayload = {
      name: raw.name,
      goal: raw.goal || undefined,
      start_date: raw.start_date || null,
      end_date: raw.end_date || null,
    };
    this.sprintsService.create(this.projectId(), payload).subscribe({
      next: s => {
        this.sprints.update(list => [...list, s]);
        this.sprintSaving.set(false);
        this.showSprintDialog.set(false);
      },
      error: err => {
        this.sprintError.set(err?.error?.detail ?? 'Failed to create sprint.');
        this.sprintSaving.set(false);
      },
    });
  }

  startSprint(sprint: Sprint): void {
    this.sprintsService.start(sprint.id).subscribe({
      next: updated => this.sprints.update(list => list.map(s => s.id === updated.id ? updated : s)),
      error: err => alert(err?.error?.detail ?? 'Failed to start sprint.'),
    });
  }

  openCompleteDialog(sprint: Sprint): void {
    this.completingSprint.set(sprint);
    this.incompleteAction.set('backlog');
    this.nextSprintId.set('');
    this.completeError.set('');
  }

  closeCompleteDialog(): void { this.completingSprint.set(null); }

  submitComplete(): void {
    const sprint = this.completingSprint();
    if (!sprint || this.completeSaving()) return;
    this.completeSaving.set(true);
    this.completeError.set('');
    const action = this.incompleteAction();
    this.sprintsService.complete(sprint.id, {
      incomplete_tasks_action: action,
      next_sprint_id: action === 'next_sprint' ? this.nextSprintId() : null,
    }).subscribe({
      next: updated => {
        this.sprints.update(list => list.map(s => s.id === updated.id ? updated : s));
        this.completeSaving.set(false);
        this.completingSprint.set(null);
      },
      error: err => {
        this.completeError.set(err?.error?.detail ?? 'Failed to complete sprint.');
        this.completeSaving.set(false);
      },
    });
  }

  // ── Members ──────────────────────────────────────────────────────────────────

  openMemberDialog(): void {
    this.memberForm.reset({ user_id: '', role: 'DEV' });
    this.memberError.set('');
    this.showMemberDialog.set(true);
  }

  closeMemberDialog(): void { this.showMemberDialog.set(false); }

  submitMember(): void {
    if (this.memberForm.invalid || this.memberSaving()) return;
    this.memberSaving.set(true);
    this.memberError.set('');
    const { user_id, role } = this.memberForm.getRawValue();
    this.projectsService.addMember(this.projectId(), user_id, role).subscribe({
      next: m => {
        this.members.update(list => [...list, m]);
        this.memberSaving.set(false);
        this.showMemberDialog.set(false);
      },
      error: err => {
        this.memberError.set(err?.error?.detail ?? 'Failed to add member.');
        this.memberSaving.set(false);
      },
    });
  }

  changeRole(member: ProjectMember, role: string): void {
    this.projectsService.updateMemberRole(this.projectId(), member.user.id, role).subscribe({
      next: updated => this.members.update(list => list.map(m => m.id === updated.id ? updated : m)),
      error: err => alert(err?.error?.detail ?? 'Failed to update role.'),
    });
  }

  removeMember(member: ProjectMember): void {
    if (!confirm(`Remove ${member.user.display_name} from this project?`)) return;
    this.projectsService.removeMember(this.projectId(), member.user.id).subscribe({
      next: () => this.members.update(list => list.filter(m => m.id !== member.id)),
      error: err => alert(err?.error?.detail ?? 'Failed to remove member.'),
    });
  }

  // ── Labels ───────────────────────────────────────────────────────────────────

  openLabelDialog(label?: Label): void {
    this.editingLabel.set(label ?? null);
    this.labelForm.patchValue(label ? { name: label.name, color: label.color } : { name: '', color: '#6b7280' });
    this.labelError.set('');
    this.showLabelDialog.set(true);
  }

  closeLabelDialog(): void { this.showLabelDialog.set(false); }

  selectLabelColor(color: string): void { this.labelForm.patchValue({ color }); }

  submitLabel(): void {
    if (this.labelForm.invalid || this.labelSaving()) return;
    const ws = this.userService.currentWorkspace();
    if (!ws) return;
    this.labelSaving.set(true);
    this.labelError.set('');
    const { name, color } = this.labelForm.getRawValue();
    const existing = this.editingLabel();
    const req$ = existing
      ? this.labelsService.update(ws.slug, existing.id, { name, color })
      : this.labelsService.create(ws.slug, { name, color });
    req$.subscribe({
      next: l => {
        this.labels.update(list =>
          existing ? list.map(x => x.id === l.id ? l : x) : [...list, l],
        );
        this.labelSaving.set(false);
        this.showLabelDialog.set(false);
      },
      error: err => {
        this.labelError.set(err?.error?.detail ?? 'Failed to save label.');
        this.labelSaving.set(false);
      },
    });
  }

  deleteLabel(label: Label): void {
    const ws = this.userService.currentWorkspace();
    if (!ws || !confirm(`Delete label "${label.name}"?`)) return;
    this.labelsService.delete(ws.slug, label.id).subscribe({
      next: () => this.labels.update(list => list.filter(l => l.id !== label.id)),
      error: err => alert(err?.error?.detail ?? 'Failed to delete label.'),
    });
  }

  // ── Custom Fields ─────────────────────────────────────────────────────────────

  openFieldDialog(): void {
    this.fieldForm.reset({ name: '', field_type: 'text', is_required: false });
    this.fieldError.set('');
    this.showFieldDialog.set(true);
  }

  closeFieldDialog(): void { this.showFieldDialog.set(false); }

  submitField(): void {
    if (this.fieldForm.invalid || this.fieldSaving()) return;
    this.fieldSaving.set(true);
    this.fieldError.set('');
    const raw = this.fieldForm.getRawValue();
    this.customFieldsService.createField(this.projectId(), {
      name:        raw.name,
      field_type:  raw.field_type,
      is_required: raw.is_required,
      position:    this.customFields().length,
    }).subscribe({
      next: f => {
        this.customFields.update(list => [...list, f]);
        this.fieldSaving.set(false);
        this.showFieldDialog.set(false);
      },
      error: err => {
        this.fieldError.set(err?.error?.detail ?? 'Failed to create field.');
        this.fieldSaving.set(false);
      },
    });
  }

  deleteField(field: CustomField): void {
    if (!confirm(`Delete field "${field.name}"? This removes all values.`)) return;
    this.customFieldsService.deleteField(this.projectId(), field.id).subscribe({
      next: () => this.customFields.update(list => list.filter(f => f.id !== field.id)),
      error: err => alert(err?.error?.detail ?? 'Failed to delete field.'),
    });
  }

  // ── Settings ──────────────────────────────────────────────────────────────────

  saveSettings(): void {
    if (this.settingsForm.invalid || this.settingsSaving()) return;
    this.settingsSaving.set(true);
    this.settingsError.set('');
    this.settingsSaved.set(false);
    const raw = this.settingsForm.getRawValue();
    this.projectsService.update(this.projectId(), raw).subscribe({
      next: p => {
        this.project.set(p);
        this.settingsSaving.set(false);
        this.settingsSaved.set(true);
        setTimeout(() => this.settingsSaved.set(false), 2500);
      },
      error: err => {
        this.settingsError.set(err?.error?.detail ?? 'Failed to save settings.');
        this.settingsSaving.set(false);
      },
    });
  }

  archiveProject(): void {
    const p = this.project();
    if (!p || !confirm(`Archive project "${p.name}"?`)) return;
    const req$ = p.archived_at
      ? this.projectsService.unarchive(p.id)
      : this.projectsService.archive(p.id);
    req$.subscribe({
      next: updated => this.project.set(updated),
      error: err => alert(err?.error?.detail ?? 'Failed to change archive status.'),
    });
  }

  sprintStatusLabel(status: string): string {
    return { planned: 'Planned', active: 'Active', completed: 'Completed' }[status] ?? status;
  }

  roleLabel(role: string): string {
    return { PO: 'Product Owner', PM: 'Project Manager', DEV: 'Developer', VIEWER: 'Viewer', GUEST: 'Guest' }[role] ?? role;
  }
}
