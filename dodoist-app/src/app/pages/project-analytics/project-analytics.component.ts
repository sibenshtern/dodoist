import { Component, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DecimalPipe } from '@angular/common';
import { TuiIcon } from '@taiga-ui/core';
import { forkJoin } from 'rxjs';
import { ProjectsService, Project } from '../../services/projects.service';
import { AnalyticsService, ProjectSummary } from '../../services/analytics.service';

@Component({
  selector: 'app-project-analytics',
  standalone: true,
  imports: [RouterLink, TuiIcon, DecimalPipe],
  template: `
    <div class="page">
      <header class="page-header">
        <a [routerLink]="['/projects', projectId()]" class="back-link">
          <tui-icon icon="@tui.arrow-left" /> {{ project()?.name ?? 'Project' }}
        </a>
        <h1>Analytics</h1>
      </header>

      @if (isLoading()) {
        <p class="loading">Loading…</p>
      } @else if (summary()) {
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ summary()!.total_tasks }}</span>
            <span class="stat-label">Total tasks</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ summary()!.open_tasks }}</span>
            <span class="stat-label">Open</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ summary()!.completed_tasks }}</span>
            <span class="stat-label">Completed</span>
          </div>
          <div class="stat-card warn">
            <span class="stat-value">{{ summary()!.overdue_tasks }}</span>
            <span class="stat-label">Overdue</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ summary()!.progress | number:'1.0-0' }}%</span>
            <span class="stat-label">Progress</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ summary()!.velocity }}</span>
            <span class="stat-label">Velocity (avg SP)</span>
          </div>
        </div>

        <div class="progress-bar-wrap">
          <div class="progress-bar" [style.width.%]="summary()!.progress"></div>
        </div>

        @if (summary()!.active_sprint) {
          <div class="active-sprint">
            <tui-icon icon="@tui.zap" class="icon-sprint" />
            <span>Active sprint running</span>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .page { padding: 24px; max-width: 720px; margin: 0 auto; }
    .page-header { margin-bottom: 24px; }
    .back-link { display: flex; align-items: center; gap: 4px; color: var(--tui-text-secondary, #6b7280); text-decoration: none; font-size: 0.875rem; margin-bottom: 8px; }
    h1 { font-size: 1.5rem; font-weight: 700; }
    .stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .stat-card { padding: 20px; border: 1px solid var(--tui-border-normal, #e5e7eb); border-radius: 8px; display: flex; flex-direction: column; align-items: center; gap: 4px; }
    .stat-card.warn { border-color: #fca5a5; }
    .stat-value { font-size: 2rem; font-weight: 700; line-height: 1; }
    .stat-label { font-size: 0.78rem; color: var(--tui-text-secondary, #6b7280); }
    .progress-bar-wrap { height: 8px; background: var(--tui-background-neutral-2, #e5e7eb); border-radius: 4px; overflow: hidden; margin-bottom: 20px; }
    .progress-bar { height: 100%; background: var(--tui-background-accent-1, #246fe0); border-radius: 4px; transition: width 0.4s; }
    .active-sprint { display: flex; align-items: center; gap: 8px; font-size: 0.875rem; }
    .icon-sprint { color: #f59e0b; }
    .loading { color: var(--tui-text-secondary, #6b7280); }
  `],
})
export class ProjectAnalyticsComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly projectsService = inject(ProjectsService);
  private readonly analyticsService = inject(AnalyticsService);

  readonly projectId = signal('');
  readonly project = signal<Project | null>(null);
  readonly summary = signal<ProjectSummary | null>(null);
  readonly isLoading = signal(true);

  ngOnInit(): void {
    this.projectId.set(this.route.snapshot.paramMap.get('id') ?? '');
    forkJoin({
      project: this.projectsService.get(this.projectId()),
      summary: this.analyticsService.getSummary(this.projectId()),
    }).subscribe({
      next: ({ project, summary }) => {
        this.project.set(project);
        this.summary.set(summary);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }
}
