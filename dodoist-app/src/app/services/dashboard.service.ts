import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';

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

@Injectable({ providedIn: 'root' })
export class DashboardService {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  private readonly http = inject(HttpClient);

  // TODO: Replace with GET /api/dashboard/stats once the backend implements a
  // dashboard aggregation endpoint. It should return open_tasks, done_this_week,
  // story_points (active sprint), and overdue counts for the authenticated user.
  getStats(): Observable<DashboardStats> {
    return of({
      openTasks: 12,
      openTasksDelta: 1,
      doneThisWeek: 28,
      doneThisWeekDeltaPct: 10,
      storyPoints: 47,
      storyPointsTotal: 69,
      overdue: 2,
    });
  }

  // TODO: Replace with GET /api/tasks/?assigned_to=me&due_date__lte=today&status=todo,in_progress,in_review,done
  // once the backend supports filtering tasks by the authenticated user and due date.
  // Currently GET /api/tasks/ requires a project_id query parameter and has no
  // user-scoped or date-range filter support.
  getTodayTasks(): Observable<TodayTask[]> {
    return of([
      {
        id: '1',
        title: 'Implement OAuth login flow',
        label: 'Bug',
        labelColor: '#db4035',
        labelBg: '#fff0ef',
        dueLabel: 'Yesterday',
        done: false,
      },
      {
        id: '2',
        title: 'Review pull request #142',
        label: 'Code Review',
        labelColor: '#246fe0',
        labelBg: '#ebf2fd',
        dueLabel: 'Today',
        done: false,
      },
      {
        id: '3',
        title: 'Write API documentation for /auth endpoints',
        label: 'Done',
        labelColor: '#299438',
        labelBg: '#f0fdf4',
        dueLabel: 'Today',
        done: true,
      },
      {
        id: '4',
        title: 'Set up staging environment',
        label: 'DevOps',
        labelColor: '#c2610c',
        labelBg: '#fff7ed',
        dueLabel: 'Tomorrow',
        done: false,
      },
      {
        id: '5',
        title: 'Update Figma design tokens',
        label: 'Design',
        labelColor: '#7c3aed',
        labelBg: '#f3eeff',
        dueLabel: 'Mar 12',
        done: false,
      },
    ]);
  }

  // TODO: Replace with GET /api/workspaces/{workspaceId}/projects once the backend
  // exposes a projects list endpoint that includes aggregated task progress stats.
  // The Project model exists in projects/models.py but has no REST endpoint yet.
  getProjects(): Observable<ProjectSummary[]> {
    return of([
      { id: '1', name: 'Backend API', color: '#db4035', progress: 68, openTasks: 14 },
      { id: '2', name: 'Mobile App', color: '#246fe0', progress: 41, openTasks: 23 },
      { id: '3', name: 'Design System', color: '#299438', progress: 85, openTasks: 6 },
    ]);
  }

  // TODO: Replace with GET /api/activity/?limit=10 once a backend activity feed
  // endpoint is implemented. The ActivityLog model exists in tasks/models.py
  // (entity_type, entity_id, actor, action, old_value, new_value) but is not
  // yet exposed through the REST API.
  getActivity(): Observable<ActivityItem[]> {
    return of([
      { id: '1', actorName: 'Bob', action: 'commented on', target: 'Update user profile API', timeAgo: '2m ago' },
      { id: '2', actorName: 'Carol', action: 'completed', target: 'Design landing page', timeAgo: '15m ago' },
      { id: '3', actorName: 'Dave', action: 'assigned you to', target: 'Review PR #142', timeAgo: '1h ago' },
      { id: '4', actorName: 'You', action: 'created', target: 'Set up CI/CD pipeline', timeAgo: '2h ago' },
    ]);
  }

  // TODO: Replace with GET /api/projects/{projectId}/sprints/?status=ACTIVE once
  // the backend exposes sprint endpoints. The Sprint model exists in projects/models.py
  // with status choices PLANNED, ACTIVE, COMPLETED.
  getActiveSprint(): Observable<SprintProgress> {
    return of({
      name: 'Sprint 5',
      storyPointsDone: 47,
      storyPointsTotal: 69,
      done: 21,
      inProgress: 8,
      blocked: 2,
      daysLeft: 5,
    });
  }
}
