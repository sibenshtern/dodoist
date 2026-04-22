import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, forkJoin, map, of, switchMap } from 'rxjs';
import { environment } from '../../environments/environment';
import { hexToRgba } from '../utils/color.util';

export interface DashboardStats {
  openTasks: number;
  openTasksDelta: number;
  doneThisWeek: number;
  doneThisWeekDeltaPct: number;
  storyPoints: number;
  storyPointsTotal: number;
  overdue: number;
}

export interface TodayTask {
  id: string;
  title: string;
  label: string;
  labelColor: string;
  labelBg: string;
  dueLabel: string;
  dueDate: string | null;
  done: boolean;
}

export interface ProjectSummary {
  id: string;
  name: string;
  color: string;
  progress: number;
  openTasks: number;
}

export interface ActivityItem {
  id: string;
  actorName: string;
  action: string;
  target: string;
  timeAgo: string;
  taskId?: string;
}

export interface SprintProgress {
  name: string;
  storyPointsDone: number;
  storyPointsTotal: number;
  done: number;
  inProgress: number;
  blocked: number;
  daysLeft: number;
}

interface ApiStats {
  open_tasks: number;
  open_tasks_delta: number;
  done_this_week: number;
  done_this_week_delta_pct: number;
  story_points: number;
  story_points_total: number;
  overdue: number;
}

interface ApiTodayTask {
  id: string;
  title: string;
  label_name: string;
  label_color: string;
  due_label: string;
  due_date: string | null;
  done: boolean;
}

interface ApiProject {
  id: string;
  name: string;
  color: string;
  active_sprint: { id: string; name: string; status: string } | null;
}

interface ApiActivityItem {
  id: string;
  actor_name: string;
  action: string;
  target: string;
  time_ago: string;
  entity_type: string;
  entity_id: string;
}

interface ApiSprint {
  id: string;
  name: string;
  end_date: string | null;
  task_stats: {
    total: number;
    completed: number;
    in_progress: number;
    total_story_points: number;
    completed_story_points: number;
  };
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);

  getStats(): Observable<DashboardStats> {
    return this.http.get<ApiStats>(`${environment.apiBase}/api/dashboard/stats/`).pipe(
      map(r => ({
        openTasks: r.open_tasks,
        openTasksDelta: r.open_tasks_delta,
        doneThisWeek: r.done_this_week,
        doneThisWeekDeltaPct: r.done_this_week_delta_pct,
        storyPoints: r.story_points,
        storyPointsTotal: r.story_points_total,
        overdue: r.overdue,
      })),
    );
  }

  getTodayTasks(): Observable<TodayTask[]> {
    return this.http.get<ApiTodayTask[]>(`${environment.apiBase}/api/tasks/today/`).pipe(
      map(tasks =>
        tasks.map(t => ({
          id: t.id,
          title: t.title,
          label: t.label_name,
          labelColor: t.label_color || '#6b7280',
          labelBg: hexToRgba(t.label_color || '#6b7280', 0.12),
          dueLabel: t.due_label,
          dueDate: t.due_date,
          done: t.done,
        })),
      ),
    );
  }

  getProjectsForActiveWorkspace(workspaceSlug: string): Observable<ProjectSummary[]> {
    return this.getProjects(workspaceSlug);
  }

  getProjects(workspaceSlug: string): Observable<ProjectSummary[]> {
    return this.http
      .get<ApiProject[]>(`${environment.apiBase}/api/workspaces/${workspaceSlug}/projects/`)
      .pipe(
        switchMap(projects => {
          if (projects.length === 0) return of([]);
          return forkJoin(
            projects.map(p =>
              this.http
                .get<{ progress: number; open_tasks: number }>(
                  `${environment.apiBase}/api/projects/${p.id}/metrics/summary/`,
                )
                .pipe(
                  map(s => ({
                    id: p.id,
                    name: p.name,
                    color: p.color || '#6b7280',
                    progress: s.progress,
                    openTasks: s.open_tasks,
                  })),
                  catchError(() =>
                    of({ id: p.id, name: p.name, color: p.color || '#6b7280', progress: 0, openTasks: 0 }),
                  ),
                ),
            ),
          );
        }),
      );
  }

  getActivity(): Observable<ActivityItem[]> {
    return this.http.get<ApiActivityItem[]>(`${environment.apiBase}/api/activity/`).pipe(
      map(items =>
        items.map(a => ({
          id: a.id,
          actorName: a.actor_name,
          action: a.action,
          target: a.target,
          timeAgo: a.time_ago,
          taskId: a.entity_type === 'task' ? a.entity_id : undefined,
        })),
      ),
    );
  }

  getActiveSprint(projectId: string): Observable<SprintProgress | null> {
    return this.http
      .get<ApiSprint[]>(`${environment.apiBase}/api/projects/${projectId}/sprints/?status=active`)
      .pipe(
        map(sprints => {
          const sprint = sprints[0];
          if (!sprint) return null;
          const stats = sprint.task_stats;
          const daysLeft = sprint.end_date
            ? Math.max(0, Math.ceil((new Date(sprint.end_date).getTime() - Date.now()) / 86400000))
            : 0;
          return {
            name: sprint.name,
            storyPointsDone: stats.completed_story_points,
            storyPointsTotal: stats.total_story_points,
            done: stats.completed,
            inProgress: stats.in_progress,
            blocked: 0,
            daysLeft,
          };
        }),
      );
  }
}

