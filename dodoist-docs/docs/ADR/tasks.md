---
title: API для задач
sidebar_index: 1
---

## Задачи

### GET /projects/{projectId}/tasks

Список задач проекта с фильтрацией.

**Параметры запроса:**

| Параметр | Тип | Пример |
|---|---|---|
| `status` | string | `in_progress,in_review` |
| `priority` | string | `critical,high` |
| `type` | string | `bug,story` |
| `assigned_to` | uuid | ID пользователя |
| `sprint_id` | uuid | ID спринта |
| `label_ids` | string | `id1,id2` |
| `due_before` | date | `2024-04-30` |
| `due_after` | date | `2024-04-01` |
| `search` | string | Полнотекстовый поиск |
| `parent_task_id` | uuid / `"null"` | Подзадачи или корневые задачи |
| `sort_by` | string | `created_at`, `due_date`, `priority`, `position` |
| `sort_dir` | string | `asc` \| `desc` |

```http
GET /projects/proj_789/tasks?status=in_progress&assigned_to=usr_456&sort_by=due_date&sort_dir=asc
```

---

### POST /projects/{projectId}/tasks

Создание задачи. Минимальная роль: **DEV**.

```json
{
  "title": "Реализовать OAuth авторизацию",
  "type": "story",
  "priority": "high",
  "assigned_to": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "sprint_id": "9a5e6f1c-2b3d-4e5f-8a9b-0c1d2e3f4a5b",
  "story_points": 5,
  "due_date": "2024-04-14T18:00:00Z",
  "label_ids": ["3f6a9b2c-1d4e-5f6a-7b8c-9d0e1f2a3b4c"]
}
```

| Поле | Тип задачи |
|---|---|
| `task` | Обычная задача |
| `bug` | Баг |
| `story` | Пользовательская история |
| `epic` | Эпик |
| `personal` | Личная задача |

> Для создания **подзадачи** укажите `parent_task_id`.

---

### GET /tasks/{taskId}

Полные детали задачи: все исполнители, метки, количество подзадач, зависимости, значения кастомных полей.

---

### PATCH /tasks/{taskId}

Частичное обновление. **DEV** — только свои задачи; **PM/PO/SA/GA** — любые.

```json
{
  "status": "in_review",
  "story_points": 8,
  "board_column_id": "col_uuid_here"
}
```

---

### DELETE /tasks/{taskId}

Мягкое удаление (soft delete). Роли: **PM, PO, SA**.

---

### GET /tasks/{taskId}/subtasks

Подзадачи. Фильтр по `status`.

---

### Управление исполнителями

| Метод | Эндпоинт | Описание |
|---|---|---|
| `POST` | `/tasks/{id}/assignments` | Добавить исполнителя |
| `DELETE` | `/tasks/{id}/assignments/{userId}` | Удалить исполнителя |

```json
{ "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8" }
```

---

### Метки задачи

| Метод | Эндпоинт | Описание |
|---|---|---|
| `POST` | `/tasks/{id}/labels` | Прикрепить метку |
| `DELETE` | `/tasks/{id}/labels/{labelId}` | Открепить метку |

---

### Зависимости задач

| Метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/tasks/{id}/dependencies` | Список зависимостей |
| `POST` | `/tasks/{id}/dependencies` | Создать зависимость |
| `DELETE` | `/tasks/{id}/dependencies/{dependencyId}` | Удалить зависимость |

**Типы зависимостей:** `blocks`, `is_blocked_by`, `relates_to`, `duplicates`, `is_duplicated_by`.

```json
{
  "depends_on_task_id": "b5f3e7c1-9a2d-4b6e-8f1a-2c3d4e5f6a7b",
  "type": "blocks"
}
```

---

### Доступ гостей к задачам

| Метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/tasks/{id}/guest-access` | Список гостей с доступом |
| `POST` | `/tasks/{id}/guest-access` | Предоставить доступ гостю |
| `DELETE` | `/tasks/{id}/guest-access/{userId}` | Отозвать доступ |

```json
{
  "user_id": "c6d7e8f9-0a1b-2c3d-4e5f-6a7b8c9d0e1f",
  "expires_at": "2024-06-30T23:59:59Z"
}
```
