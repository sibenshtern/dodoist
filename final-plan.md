# Dodoist — Workspace Feature Rewrite

## Context

Workspaces in Dodoist today are barely more than a grouping table: `Workspace` + `WorkspaceMember` with a `joined_at` stamp. Membership grants nothing; there are no workspace-level roles, no invitations, no soft-delete, and no "active workspace" server-side concept — the sidebar switcher (`user.service.ts:59`) just flips a client-only signal, while the dashboard's `DashboardService.getAllProjects(...)` iterates every workspace slug the user belongs to, so the list view mixes projects across organizations regardless of what the switcher shows. The `plan` column exists but drives no logic.

The user decided workspaces should model a real company/organization boundary:

- Each user gets **one auto-created personal workspace** (single-member, undeletable) plus any number of team workspaces they own or join.
- **Projects are permanently workspace-scoped** — cannot move across workspaces.
- **Strict filter**: active workspace scopes projects, My Tasks, Today, Inbox, Search, Dashboard stats, and notifications. No cross-workspace leakage.
- **Active workspace is server-stored** (on `User`), so backend endpoints enforce filtering and the frontend needs no per-call scoping logic.
- **Workspace-level roles** (Owner / Admin / Member) separate from project roles. Workspace membership ≠ project access; members must be explicitly added to each project.
- **Invitations** via four mechanisms: direct user-ID add (existing), email invite to existing user, email invite to new signup, shareable invite link.
- **Soft-delete with 30-day grace**, Owner-only; cascade hard-delete after grace.
- **Leaving** removes all project memberships in that workspace; task assignments remain in DB for history but access is blocked. Sole Owner cannot leave.
- Drop the `plan` field from UI/logic (leave the column until a follow-up migration drops it, to avoid destructive schema change in this rewrite).

Target outcome: a workspace feature that behaves like Notion/Linear's team concept — with personal space as a private default, team spaces as explicitly invited boundaries, and strict isolation between them.

Sources: `projects/models.py:59-88`, `projects/services.py:51-92`, `projects/views.py:29-200`, `users/services.py:113-134`, `users/models.py:16-47`, `users/tasks.py`, `tasks/services.py:293-353` (`AccessControlService`), `tasks/views.py` (global endpoints), `dodoist-app/src/app/services/{user,workspace}.service.ts`, `dodoist-app/src/app/pages/{workspaces,workspace-detail,workspace-members}/`, `dodoist-app/src/app/layouts/dashboard-layout/`.

---

## Phase 1 — Data model (migrations)

Goal: add all schema needed for roles, active workspace, soft-delete, and invitations. One migration file per app (`projects/migrations/0003_workspace_rewrite.py`, `users/migrations/0003_active_workspace.py`). Use `RunPython` for backfills.

### `projects/models.py`

1. **`WorkspaceRole` enum** (`TextChoices`: `OWNER`, `ADMIN`, `MEMBER`). Place near `ProjectRole`.
2. **`WorkspaceMember.role`** — `CharField(choices=WorkspaceRole.choices, default=MEMBER)`. Backfill: for each existing `WorkspaceMember`, set `role=OWNER` if `user_id == workspace.owner_id`, else `MEMBER`.
3. **`WorkspaceMember.invited_by`** — nullable FK to `User`, `on_delete=SET_NULL`. Backfill null.
4. **`Workspace` soft-delete fields**:
   - `deleted_at` — nullable `DateTimeField(db_index=True)`.
   - `deleted_by` — nullable FK to `User`, `SET_NULL`.
   - `delete_scheduled_for` — nullable `DateTimeField` (set to `deleted_at + 30 days` on soft-delete). Indexed; queried by the cleanup task.
5. **`Workspace.Meta.indexes`** — add `(owner, is_personal)`, `(delete_scheduled_for,)`.
6. **`WorkspaceInvitation`** (new model):
   ```
   id (UUID PK), workspace (FK CASCADE), kind (EMAIL|LINK),
   email (CharField, nullable — set for EMAIL only),
   token_hash (64-char SHA-256, unique, db_index=True),
   role_to_grant (WorkspaceRole, default MEMBER),
   invited_by (FK User, SET_NULL), created_at, expires_at (nullable; default +7 days for EMAIL, null for LINK unless caller sets),
   max_uses (PositiveIntegerField, default=1 for EMAIL, nullable for LINK = unlimited),
   use_count (PositiveIntegerField, default=0),
   accepted_at (nullable), accepted_by (nullable FK User, SET_NULL),
   revoked_at (nullable)
   ```
   Indexes: `(workspace, accepted_at, revoked_at)`, `(email,)`. Pattern mirrors `User.verification_token_hash` (`users/models.py:27`).

### `users/models.py`

7. **`User.active_workspace`** — nullable FK to `Workspace`, `on_delete=SET_NULL`. Default null. Backfill: for each user, set to their personal workspace if one exists. Write a post-save signal later to default it on workspace creation.

---

## Phase 2 — Backend service layer

Goal: centralize all workspace logic in services, honoring the new role/soft-delete/active-workspace semantics. Every write is `@transaction.atomic`; every member-role change and deletion writes an `ActivityLog` entry via a thin `_log` helper consistent with `TaskService._log`.

### `projects/services.py`

1. **`WorkspaceService.create_personal_workspace(user)`** — unchanged signature, but now also creates a `WorkspaceMember(role=OWNER)` row and sets `user.active_workspace = ws` if null. Called from `UserService.register` (`users/services.py:131`).
2. **`WorkspaceService.create_team_workspace(owner, name, slug=None, description="")`** — replaces `create_workspace`; drops `plan` param. Creates workspace + `WorkspaceMember(user=owner, role=OWNER)`.
3. **`WorkspaceService.add_member(workspace, user, role=MEMBER, invited_by=None)`** — idempotent; if member exists, updates role to `role`. Refuses role=OWNER via this path (use `transfer_ownership`).
4. **`WorkspaceService.remove_member(workspace, user)`** — block if `user == workspace.owner`. On success:
   - Delete all `ProjectMember` rows where `project.workspace = workspace AND user = user`.
   - Task assignments are not touched (history preserved; access naturally blocked because `AccessControlService` checks `ProjectMember`).
   - Returns number of project memberships removed.
5. **`WorkspaceService.change_role(workspace, user, new_role, actor)`** — requires `actor` to be Owner (for Admin↔Member) or blocks promoting to Owner (use transfer). Admins cannot demote Owner.
6. **`WorkspaceService.transfer_ownership(workspace, new_owner, actor)`** — `actor must == workspace.owner`. Sets `workspace.owner = new_owner`, updates `WorkspaceMember.role`: old owner becomes `ADMIN`, new owner becomes `OWNER`.
7. **`WorkspaceService.soft_delete(workspace, actor)`** — only Owner. Sets `deleted_at=now`, `delete_scheduled_for=now+30d`, `deleted_by=actor`. Reject if `is_personal=True`.
8. **`WorkspaceService.restore(workspace, actor)`** — only Owner, only while `deleted_at IS NOT NULL AND delete_scheduled_for > now`. Clears the three fields.
9. **`WorkspaceService.leave(workspace, user)`** — user removes themselves. Block if `user == workspace.owner` (must transfer first). Delegates to `remove_member`.

### `projects/invitations.py` (new module)

10. **`InvitationService.create_email_invite(workspace, email, role, invited_by)`** — creates `WorkspaceInvitation(kind=EMAIL)` with random 32-byte token, stores SHA-256 hash, 7-day expiry. Dispatches Celery task `send_workspace_invite_email(invite_id, raw_token)` via `transaction.on_commit`.
11. **`InvitationService.create_invite_link(workspace, role, invited_by, max_uses=None, expires_at=None)`** — `kind=LINK`, unlimited uses by default, returns raw token once (never stored plaintext).
12. **`InvitationService.accept(raw_token, user)`** — SHA-256 the input; lookup by `token_hash`, validate not expired / not revoked / `use_count < max_uses` / (email-kind: `email == user.email`). Wrap in `transaction.atomic`:
    - `WorkspaceService.add_member(ws, user, role=invite.role_to_grant, invited_by=invite.invited_by)`
    - For EMAIL: set `accepted_at=now, accepted_by=user, revoked_at=now` (single-use).
    - For LINK: `use_count += 1`.
    - Fire notification of type `INVITED` to the inviter.
13. **`InvitationService.revoke(invite, actor)`** — sets `revoked_at=now`; Owner/Admin only.
14. **`InvitationService.list_pending(workspace)`** — unaccepted, unrevoked, not expired.

### `users/services.py`

15. **`UserService.set_active_workspace(user, workspace)`** — validates user is a member (or owner); sets `user.active_workspace = workspace`; saves. Used by the `PATCH /users/me/active-workspace/` endpoint.
16. **`UserService.register(...)`** — extended with optional `invite_token` param. If provided, after user creation validate and call `InvitationService.accept`. If accept fails, log and continue (don't block signup).

### `tasks/services.py`

17. **`AccessControlService.workspace_member(user, workspace)`** — returns the `WorkspaceMember` row or `None`. Used by every workspace-scoped view.
18. **`AccessControlService.is_workspace_owner(user, workspace)`** — `user == workspace.owner`.
19. **`AccessControlService.is_workspace_admin_or_owner(user, workspace)`** — role in `(OWNER, ADMIN)`. Gates invite/settings/member-role endpoints.
20. No changes to existing project-level checks; `ProjectMember` is still the source of truth for project access.

### `users/tasks.py`

21. **`send_workspace_invite_email(invite_id, raw_token)`** — same Celery pattern as `send_verification_email` (`users/tasks.py:51`). Link: `{FRONTEND_BASE_URL}/invites/{raw_token}`. Body mentions the workspace name, inviter, and role.

### Cleanup cron

22. **`projects/tasks.py`** — new Celery periodic task `purge_expired_workspaces()` that hard-deletes workspaces where `delete_scheduled_for <= now`. Schedule via Celery beat (1×/day). Cascades are DB-level.

---

## Phase 3 — Backend views & routing

Goal: expose the service layer, enforce workspace roles, and — critically — plug **active-workspace filtering** into the global endpoints.

### `projects/views.py`

1. **`WorkspaceDetailView.delete`** — switch from hard delete to `WorkspaceService.soft_delete`. Owner-only (403 otherwise, personal 409).
2. **`WorkspaceRestoreView`** (new, `POST /api/workspaces/<slug>/restore/`) — Owner-only.
3. **`WorkspaceTransferOwnershipView`** (new, `POST /api/workspaces/<slug>/transfer/`) — body `{ new_owner_id }`, Owner-only.
4. **`WorkspaceLeaveView`** (new, `POST /api/workspaces/<slug>/leave/`) — self-remove.
5. **`WorkspaceMemberListView`** — `POST` now accepts `{ user_id, role? }`; Owner/Admin only. `GET` returns `role` on each row. Serializer: `WorkspaceMemberSerializer` now exposes `role`.
6. **`WorkspaceMemberDetailView`** — `PATCH` supports `{ role }` (Owner/Admin only, Owner cannot be demoted via this endpoint). `DELETE` unchanged semantics but blocked for Owner.
7. **`WorkspaceListCreateView.get`** — return only non-deleted workspaces where the user is a member.

### `projects/invitations_views.py` (new)

8. `POST /api/workspaces/<slug>/invitations/` — body `{ email, role? }`, Owner/Admin only.
9. `GET /api/workspaces/<slug>/invitations/` — list pending.
10. `DELETE /api/workspaces/<slug>/invitations/<id>/` — revoke, Owner/Admin.
11. `POST /api/workspaces/<slug>/invite-links/` — body `{ role, max_uses?, expires_at? }`, returns `{ token }` (plaintext returned ONCE).
12. `POST /api/invitations/accept/` (auth required) — body `{ token }`.
13. `GET /api/invitations/me/` — pending email-kind invitations where `email == request.user.email`.

### `users/views.py`

14. `PATCH /api/users/me/active-workspace/` — body `{ workspace_id }` or `{ workspace_slug }`. Calls `UserService.set_active_workspace`.
15. **`SignupView.post`** — reads optional `invite_token` from body; passes through to `UserService.register`.
16. `UserCurrentView.get` — include `active_workspace: { id, slug, name, is_personal }` inline so the frontend can avoid a second fetch.

### Active-workspace filtering (the critical change)

17. **Helper `_active_ws(request)`** in a new `projects/request_helpers.py`: returns `request.user.active_workspace` (401-safe). If null, falls back to the user's personal workspace.
18. Apply to every **global** endpoint:
    - `tasks/views.py` `MyTasksView.get_queryset` — add `.filter(project__workspace=_active_ws(request))`.
    - `TodayTasksView` — same.
    - `InboxView` — scoped to personal workspace only (definitionally); unchanged except assertion.
    - `TaskSearchView` — queryset filter before `[:20]` slice.
    - `DashboardStatsView` — aggregate over projects in active ws only.
    - `NotificationListView` in `users/views.py` — filter `Notification` by `project_id IN (active-ws projects) OR task_id IN (active-ws tasks)`. Requires a subquery on `Project.objects.filter(workspace=...)`.
19. URL-scoped endpoints (`/api/workspaces/<slug>/...`) continue to use the slug as the source of truth — **no double-filtering**, so a user can still view a workspace's projects via its URL even if it's not their active one (used by the workspaces list page links). The frontend simply sets active workspace on click.

### `projects/urls.py` and `dodoist/urls.py`

20. Register the new URLs (restore, transfer, leave, invitations, invite-links, accept, me-invites, active-workspace).

---

## Phase 4 — Frontend: services

Goal: align the service layer with the new API and make the switcher server-backed.

### `dodoist-app/src/app/services/user.service.ts`

1. Extend `UserProfile` with `active_workspace: Workspace | null`.
2. Replace local-only `switchWorkspace(ws)` with:
   ```ts
   switchWorkspace(ws: Workspace): Observable<UserProfile> {
     return this.http.patch<UserProfile>(`${apiBase}/api/users/me/active-workspace/`, { workspace_slug: ws.slug })
       .pipe(tap(u => { this.currentUser.set(u); this.currentWorkspace.set(ws); }));
   }
   ```
3. `loadCurrentUser()` now hydrates `currentWorkspace` from `user.active_workspace` (eliminates the stopgap "first personal" default in `loadWorkspaces`).

### `dodoist-app/src/app/services/workspace.service.ts`

4. Add methods mirroring the new endpoints:
   - `delete(slug)`, `restore(slug)`, `transferOwnership(slug, newOwnerId)`, `leave(slug)`.
   - `updateMemberRole(slug, userId, role)`.
   - `listInvitations(slug)`, `createEmailInvite(slug, email, role)`, `revokeInvitation(slug, id)`, `createInviteLink(slug, role, maxUses?, expiresAt?)`.
   - `acceptInvitation(token)`, `listMyInvitations()`.
5. Extend `WorkspaceMember` type with `role: 'OWNER'|'ADMIN'|'MEMBER'`.

### New `dodoist-app/src/app/services/confirm-dialog.service.ts`

6. Lightweight wrapper around `@taiga-ui/kit` `TuiConfirmService` with `.confirm({ title, body, danger? })` returning `Observable<boolean>`. Reused by delete-workspace and remove-member.

### `dodoist-app/src/app/services/dashboard.service.ts`

7. `getAllProjects(...)` changes signature from multi-slug-iteration to `getProjectsForActiveWorkspace()` — calls `/api/workspaces/<active-slug>/projects/`. Caller in the dashboard layout simplifies accordingly.

---

## Phase 5 — Frontend: pages & UX

### `pages/workspaces/workspaces.component.ts` (list page)

1. Each card gets a role badge (Owner/Admin/Member) and a "Switch to" button that calls `userService.switchWorkspace(ws)` then navigates to `/home`. Click on name/chevron continues to go to detail.
2. Owner-only "Delete" button on each owned workspace; uses `ConfirmDialogService`, shows the 30-day grace message, calls `wsService.delete(slug)`, marks the card as "scheduled for deletion in 30 days" with a "Restore" button.
3. Keep the existing inline "New workspace" form (already shipped).

### `pages/workspace-detail/workspace-detail.component.ts` (settings)

4. Role-gate the edit form: only Owner/Admin can save.
5. Remove `plan` display (keep field untouched on server).
6. Add "Danger zone" section (Owner only): Transfer ownership (user search dropdown of workspace members), Delete workspace.

### `pages/workspace-members/workspace-members.component.ts`

7. Add a tabbed header: **Members** | **Pending invites** | **Invite link**.
8. **Members tab** — list with role dropdown per row (Owner read-only; Owner/Admin can change Admin↔Member). Remove button confirmed via `ConfirmDialogService`. Drop the raw UUID-add form from the default view (keep it under a collapsed "Add by user ID" toggle for power users).
9. New **Invite by email** form at the top: email input + role select (Member/Admin). Submits to `createEmailInvite`.
10. **Pending invites tab** — table of unaccepted invitations with email, role, sent-by, sent-at, expires-at, Revoke button.
11. **Invite link tab** — Owner/Admin can generate a link with role + optional max uses + optional expiry. Token is shown once with a copy button; after reload it's replaced by "Link exists (revoke to reset)".

### New `pages/invite-accept/invite-accept.component.ts`, route `/invites/:token`

12. On mount:
    - If authenticated → call `wsService.acceptInvitation(token)`; on success, `userService.switchWorkspace(newWs)` and navigate to `/home`.
    - If not authenticated → redirect to `/signup?invite=<token>` (retaining the token in the query string so signup can forward it).

### `pages/signup/signup.component.ts`

13. Read `?invite=` from `ActivatedRoute.snapshot.queryParamMap`. Pass it in the signup request body as `invite_token`. After success, call `acceptInvitation` if the server didn't do it as part of signup (the service method in users/services.py handles both paths — frontend just forwards the token).

### `layouts/dashboard-layout/dashboard-layout.component.ts` + `.html`

14. Switcher dropdown — `switchWorkspace` is now async; disable the dropdown while pending, show a spinner on the selected row, toast on error.
15. Sidebar projects list — call `dashboardService.getProjectsForActiveWorkspace()` and refetch whenever `userService.currentWorkspace()` changes (use `toObservable()` + `switchMap`).
16. Notifications list — unchanged client-side (server now filters strictly).

### Cross-cutting

17. All `loadError` UIs get a toast path too, via the existing `auth.interceptor.ts` toast hook (already added).

---

## Phase 6 — Tests

### Backend (`pytest`)

1. `projects/tests/test_workspace_roles.py` — role-gated endpoints: Admin can invite, Member cannot; Owner transfer updates both rows; remove-member cascades ProjectMember deletion; leave blocked for sole Owner.
2. `projects/tests/test_invitations.py` — email invite happy path; expired rejected; revoked rejected; max_uses decremented; email-kind checks recipient email; signup-with-invite auto-joins.
3. `projects/tests/test_workspace_soft_delete.py` — only Owner can delete; personal cannot; restore during grace works; past-grace cleanup task purges and cascades.
4. `tasks/tests/test_active_workspace_filter.py` — MyTasks/Today/Search/Dashboard all return empty when active workspace is another workspace; Notifications excluded similarly.
5. `users/tests/test_set_active_workspace.py` — cannot set to a workspace you're not a member of (400); valid set persists; new user's active_workspace is the personal one.

### Frontend (`vitest`)

6. `workspace.service.vitest.ts` — all new endpoints call the right URL with the right body.
7. `user.service.vitest.ts` — `switchWorkspace` patches then updates signals; rollback on error.
8. `invite-accept.component.vitest.ts` — token handling for authed / unauthed paths.
9. `pages/workspace-members.component.vitest.ts` — role dropdown disabled for Members, enabled for Admin/Owner.

---

## Critical files (quick index)

Backend:
- `dodoist-backend/projects/models.py` — `Workspace`, `WorkspaceMember`, new `WorkspaceRole`, new `WorkspaceInvitation`.
- `dodoist-backend/projects/services.py` — `WorkspaceService` expanded.
- `dodoist-backend/projects/invitations.py` (new) — `InvitationService`.
- `dodoist-backend/projects/views.py` + new `projects/invitations_views.py`.
- `dodoist-backend/projects/request_helpers.py` (new) — `_active_ws(request)`.
- `dodoist-backend/users/models.py` — `User.active_workspace`.
- `dodoist-backend/users/services.py` — `register(invite_token=)`, `set_active_workspace`.
- `dodoist-backend/users/tasks.py` — `send_workspace_invite_email`.
- `dodoist-backend/projects/tasks.py` (new) — `purge_expired_workspaces`.
- `dodoist-backend/tasks/services.py` — `AccessControlService` workspace helpers.
- `dodoist-backend/tasks/views.py` — MyTasks/Today/Search/Dashboard active-ws filter.
- `dodoist-backend/users/views.py` — `/users/me/active-workspace/`, `NotificationListView` filter.
- `dodoist-backend/projects/urls.py`, `dodoist/urls.py` — new routes.

Frontend:
- `dodoist-app/src/app/services/user.service.ts`, `workspace.service.ts`, `dashboard.service.ts`.
- `dodoist-app/src/app/services/confirm-dialog.service.ts` (new).
- `dodoist-app/src/app/pages/{workspaces,workspace-detail,workspace-members}/` — reworked.
- `dodoist-app/src/app/pages/invite-accept/` (new).
- `dodoist-app/src/app/pages/signup/signup.component.ts` — honor `?invite=`.
- `dodoist-app/src/app/layouts/dashboard-layout/dashboard-layout.component.{ts,html}` — server-backed switcher, reactive projects list.
- `dodoist-app/src/app/app.routes.ts` — register `/invites/:token`.

Reuse:
- Email Celery pattern → `users/tasks.py:51` (`send_verification_email`).
- Token hashing pattern → `users/models.py:27` (`verification_token_hash`).
- `transaction.on_commit` pattern → existing use in `NotificationService.create`.
- `ActivityLog` via `TaskService._log` — mirror in `WorkspaceService._log`.
- Toast interceptor — already in `auth.interceptor.ts`.

---

## Verification (end-to-end golden path)

Run locally with a fresh DB after migrations:

1. **Signup** → verify email → land on `/home` with the auto-created personal workspace active. `GET /api/users/me` returns `active_workspace` inline.
2. **Create team workspace** "Acme" from `/workspaces` → sidebar switcher shows "Acme"; click Switch → URL stays at `/home` but project list is empty. `GET /api/tasks/my/` returns `[]`.
3. **Invite by email** a user that exists → they see the pending invite at `/invites/me`; accepting adds them as Member; their active workspace switches to Acme.
4. **Invite by email** a non-existent user → email lands; click link → `/signup?invite=<token>`; sign up; auto-joined to Acme as Member.
5. **Invite link** → generate with role Admin → open link in incognito → signup → auto-joined as Admin.
6. **Direct add by user ID** (existing flow) → still works; grants Member role.
7. **Role change** — Owner promotes Member → Admin; Admin can now invite but cannot delete workspace. Member cannot change roles.
8. **Strict filter** — switch to personal workspace; My Tasks/Today/Search/Dashboard show only personal items; notification from Acme does not appear in the bell.
9. **Leave** — Member leaves Acme → their `ProjectMember` rows in Acme's projects are gone; opening any Acme task URL returns 403; `active_workspace` falls back to personal.
10. **Transfer + delete** — Owner transfers to Admin, old owner is now Admin; new Owner deletes workspace → workspace disappears from sidebar, shows as "Scheduled for deletion" on `/workspaces`; Restore → reappears. After manually advancing `delete_scheduled_for` and running `purge_expired_workspaces`, all projects/tasks cascade-delete.
11. **Personal workspace** — cannot be deleted (409); Invite UI hidden.
12. `pytest dodoist-backend/` and `npm test` in `dodoist-app/` both green. `python manage.py spectacular --file dodoist-docs/docs/openapi.yaml` regenerates the spec with no unexpected diff beyond the new endpoints.
