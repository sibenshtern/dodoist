# REST API — Task Tracker v1.0

> Гибридный трекер задач: личные задачи в стиле Todoist + проектное управление в стиле Jira.

---

## Содержание

1. [Общие сведения](#1-общие-сведения)
2. [Аутентификация](#2-аутентификация)
3. [Модель прав доступа](#3-модель-прав-доступа)
4. [Пагинация и фильтрация](#4-пагинация-и-фильтрация)
5. [Формат ошибок](#5-формат-ошибок)
6. [Пользователи](#6-пользователи)
7. [Рабочие пространства](#7-рабочие-пространства)
8. [Проекты](#8-проекты)
9. [Метки](#9-метки)
10. [Задачи](#10-задачи)
11. [Настраиваемые поля](#11-настраиваемые-поля)
12. [Комментарии и реакции](#12-комментарии-и-реакции)
13. [Вложения](#13-вложения)
14. [Уведомления](#14-уведомления)
15. [Журнал активности](#15-журнал-активности)
16. [Спринты](#16-спринты)
17. [Доски и колонки](#17-доски-и-колонки)
18. [Учёт рабочего времени](#18-учёт-рабочего-времени)
19. [Аналитика](#19-аналитика)
20. [Лимиты и ограничения](#20-лимиты-и-ограничения)

---

## 1. Общие сведения

**Base URL:** `https://api.tasktracker.io/v1`

Все запросы и ответы используют формат **JSON** (`Content-Type: application/json`), за исключением загрузки файлов (`multipart/form-data`).

Временны́е метки передаются в формате **ISO 8601**: `"2024-04-15T10:30:00Z"`.  
Идентификаторы — **UUID v4**: `"550e8400-e29b-41d4-a716-446655440000"`.

---

## 2. Аутентификация

API использует **JWT Bearer-токены**. Все эндпоинты требуют аутентификации, кроме `/auth/register` и `/auth/login`.

```http
Authorization: Bearer <access_token>
```

| Параметр | Описание |
|---|---|
| `access_token` | Краткосрочный JWT, действует **15 минут** |
| `refresh_token` | Долгосрочный токен, действует **30 дней** |

### Почему пароли не передаются в теле запроса

Тела HTTP-запросов часто попадают в логи приложений, трейсы ошибок и кэши прокси-серверов. Чтобы пароль никогда не оказался в логах, он передаётся **в заголовках**, а не в теле:

| Операция | Способ передачи |
|---|---|
| Вход (`/auth/login`) | Стандартный HTTP Basic Auth: `Authorization: Basic base64(email:password)` |
| Регистрация (`/auth/register`) | Заголовок `X-Password` |
| Смена пароля (`PATCH /users/{id}`) | Заголовки `X-Current-Password` и `X-New-Password` |

Всё взаимодействие должно происходить **только по HTTPS/TLS**.

---

### Регистрация нового пользователя

```http
POST /auth/register
X-Password: s3cur3pass!
```

**Тело запроса:**

```json
{
  "email": "alice@example.com",
  "display_name": "Alice Smith",
  "timezone": "Europe/Moscow"
}
```

**Ответ `201`:**

```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "alice@example.com",
    "display_name": "Alice Smith",
    "global_role": "member",
    "created_at": "2024-04-15T10:00:00Z"
  },
  "access_token": "eyJhbGci...",
  "refresh_token": "dGhpcyBp..."
}
```

После регистрации автоматически создаётся личное рабочее пространство (`is_personal=true`).

### Вход

Используется **HTTP Basic Authentication**. Учётные данные кодируются в base64 и передаются в заголовке — пароль не попадает в тело запроса.

```http
POST /auth/login
Authorization: Basic YWxpY2VAZXhhbXBsZS5jb206czNjdXIzcGFzcyE=
```

> `YWxpY2VA...` = `base64("alice@example.com:s3cur3pass!")`

Тело запроса отсутствует.

### Выход

```http
POST /auth/logout
```

Аннулирует текущую сессию. Ответ: `204 No Content`.

Для немедленного отзыва refresh-токена передайте его в теле запроса:

```json
{
  "refresh_token": "dGhpcyBp..."
}
```

> Если `refresh_token` не передан, инвалидируется только access-токен. Передача refresh-токена гарантирует, что он не может быть использован повторно после выхода (важно при компрометации токена).

### Обновление токена

```http
POST /auth/refresh
```

```json
{
  "refresh_token": "dGhpcyBp..."
}
```

---

## 3. Модель прав доступа

Система использует **двухуровневую** модель ролей.

### Глобальные роли

Хранятся в поле `users.global_role`. Применяются ко всей системе.

| Роль | Код | Описание |
|---|---|---|
| System Administrator | `SA` | Полный доступ без ограничений. Обходит все проверки на уровне проектов |
| Global Admin | `GA` | Создаёт и настраивает проекты, управляет ролями. Не может удалять проекты |
| Пользователь | `member` | Права определяются ролью в каждом проекте |

### Проектные роли

Хранятся в `project_members.role`. Один пользователь может иметь **разные роли в разных проектах**.

| Роль | Код | Описание |
|---|---|---|
| Владелец проекта | `PO` | Полный контроль над проектом: настройки, участники, задачи |
| Менеджер проекта | `PM` | Управление рабочим процессом, спринтами, любыми задачами |
| Разработчик | `DEV` | Создание задач, редактирование **только своих** задач |
| Наблюдатель | `VW` | Просмотр + комментарии. Без права создавать или изменять задачи |
| Гость | `GU` | Просмотр только явно разрешённых задач (`task_guest_access`) |

### Сводная таблица разрешений

| Действие | SA | GA | PO | PM | DEV | VW | GU |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **ПРОЕКТ** |  |  |  |  |  |  |  |
| Создать проект | ✓ | ✓ | — | — | — | — | — |
| Удалить проект | ✓ | — | ✓ | — | — | — | — |
| Настройки проекта | ✓ | ✓ | ✓ | ✓ | — | — | — |
| Управление участниками | ✓ | ✓ | ✓ | — | — | — | — |
| Архивировать | ✓ | — | ✓ | — | — | — | — |
| Просмотр | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓* |
| Управление досками | ✓ | — | ✓ | ✓ | — | — | — |
| **ЗАДАЧИ** |  |  |  |  |  |  |  |
| Создать задачу | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| Редактировать любую | ✓ | ✓ | ✓ | ✓ | — | — | — |
| Редактировать свою | ✓ | — | — | — | ✓ | — | — |
| Удалить задачу | ✓ | — | ✓ | ✓ | — | — | — |
| Назначить исполнителя | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| Сменить статус | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| Комментировать | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| Просмотр задачи | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓* |
| Логировать время | ✓ | — | ✓ | ✓ | ✓ | — | — |
| Управление подзадачами | ✓ | — | ✓ | ✓ | ✓ | — | — |

*\* Только явно разрешённый контент*

---

## 4. Пагинация и фильтрация

Все списковые эндпоинты поддерживают **курсорную пагинацию**.

### Параметры запроса

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `limit` | int | 20 | Количество элементов на странице (макс. 100) |
| `cursor` | string | — | Непрозрачный курсор из поля `meta.next_cursor` |

### Формат ответа

```json
{
  "data": [ ... ],
  "meta": {
    "total": 142,
    "limit": 20,
    "next_cursor": "eyJpZCI6IjEyMyJ9"
  }
}
```

Если `next_cursor` равен `null` — это последняя страница.

**Пример:**
```http
GET /projects/proj_789/tasks?limit=10&cursor=eyJpZCI6IjEyMyJ9&status=in_progress&sort_by=due_date&sort_dir=asc
```

---

## 5. Формат ошибок

Все ошибки возвращают единый формат:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request body validation failed",
    "details": {
      "fields": {
        "email": "Must be a valid email address"
      }
    }
  }
}
```

| HTTP-код | Код ошибки | Описание |
|---|---|---|
| `400` | `BAD_REQUEST` | Неверный формат запроса |
| `401` | `UNAUTHORIZED` | Токен отсутствует или истёк |
| `403` | `FORBIDDEN` | Недостаточно прав |
| `404` | `NOT_FOUND` | Ресурс не найден |
| `409` | `CONFLICT` | Конфликт (дубликат, уже активен и т.д.) |
| `422` | `VALIDATION_ERROR` | Ошибка валидации полей |
| `429` | `RATE_LIMITED` | Превышен лимит запросов — см. заголовок `Retry-After` |
| `500` | `INTERNAL_ERROR` | Внутренняя ошибка сервера |

---

## 6. Пользователи

### GET /users

Список всех пользователей. Только для **SA / GA**.

**Параметры запроса:** `limit`, `cursor`, `search` (фильтр по имени/email), `is_active`.

```http
GET /users?search=alice&is_active=true
```

---

### GET /users/me

Профиль текущего пользователя с настройками.

```http
GET /users/me
```

**Ответ:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "alice@example.com",
  "display_name": "Alice Smith",
  "timezone": "Europe/Moscow",
  "global_role": "member",
  "preferences": {
    "theme": "dark",
    "language": "ru",
    "notification_channels": ["email", "in_app"],
    "digest_frequency": "daily",
    "default_view": "board"
  }
}
```

---

### GET /users/{userId}

Профиль пользователя по ID.

```http
GET /users/550e8400-e29b-41d4-a716-446655440000
```

---

### PATCH /users/{userId}

Обновление профиля. Пользователь обновляет свой профиль; SA — любой.

```json
{
  "display_name": "Alice Johnson",
  "timezone": "Asia/Yekaterinburg"
}
```

Для смены пароля используйте заголовки — **не тело запроса**:

```http
PATCH /users/550e8400-e29b-41d4-a716-446655440000
X-Current-Password: old_pass
X-New-Password: new_pass123
```

| Заголовок | Описание |
|---|---|
| `X-Current-Password` | Текущий пароль (обязателен при смене, кроме случаев SA) |
| `X-New-Password` | Новый пароль, минимум 8 символов |

> Поле `avatar_url` принимает только **HTTPS**-ссылки. Ссылки по протоколам `http://`, `file://` и другим отклоняются с `422 VALIDATION_ERROR`.

---

### DELETE /users/{userId}

Деактивация аккаунта (soft-delete, устанавливает `is_active=false`). Только **SA**.

---

### GET /users/{userId}/preferences

### PUT /users/{userId}/preferences

Полная замена настроек. Неуказанные поля сбрасываются до значений по умолчанию.

```json
{
  "theme": "dark",
  "language": "ru",
  "notification_channels": ["email", "in_app"],
  "digest_frequency": "daily",
  "default_view": "board"
}
```

| Поле | Значения |
|---|---|
| `theme` | `light` \| `dark` \| `system` |
| `language` | Код языка ISO 639-1, напр. `ru`, `en` |
| `notification_channels` | Массив: `email`, `push`, `in_app` |
| `digest_frequency` | `realtime` \| `daily` \| `weekly` |
| `default_view` | `list` \| `board` \| `calendar` |

---

## 7. Рабочие пространства

### GET /workspaces

Список рабочих пространств текущего пользователя.

```http
GET /workspaces?is_personal=false
```

---

### POST /workspaces

Создание нового рабочего пространства. Создатель становится владельцем.

```json
{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "description": "Главное пространство для команды",
  "plan": "pro"
}
```

> Поле `slug` — уникальный URL-идентификатор. Разрешены строчные буквы, цифры и дефис.

---

### GET /workspaces/{workspaceId}

### PATCH /workspaces/{workspaceId}

Обновление метаданных. Только владелец или **SA**.

---

### DELETE /workspaces/{workspaceId}

Удаление пространства со всем содержимым. Только **SA**.

---

### Управление участниками

| Метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/workspaces/{id}/members` | Список участников |
| `POST` | `/workspaces/{id}/members` | Добавить участника |
| `DELETE` | `/workspaces/{id}/members/{userId}` | Удалить участника |

**Добавление участника:**
```json
{
  "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
}
```

> Участник должен быть существующим пользователем системы. Удаление из пространства автоматически убирает пользователя из всех проектов.

---

## 8. Проекты

### GET /workspaces/{workspaceId}/projects

Список проектов в рабочем пространстве.

**Фильтры:** `status`, `type`, `search`, `limit`, `cursor`.

```http
GET /workspaces/wsp_123/projects?status=active&type=scrum
```

---

### POST /workspaces/{workspaceId}/projects

Создание проекта. Создатель автоматически получает роль **PO**.

```json
{
  "name": "Backend API",
  "key": "BAPI",
  "type": "scrum",
  "description": "Разработка RESTful API",
  "color": "#4A90E2",
  "is_private": false
}
```

| Поле | Требуется | Описание |
|---|---|---|
| `name` | Да | Название проекта |
| `key` | Да | Короткий код (2-10 символов, только `A-Z0-9`), уникален в пространстве |
| `type` | Да | `scrum` \| `kanban` \| `personal` |
| `color` | Нет | HEX-цвет, напр. `#4A90E2` |
| `is_private` | Нет | Приватный проект (по умолчанию `false`) |

---

### GET /projects/{projectId}

Детали проекта: информация об активном спринте, количество участников, роль текущего пользователя.

---

### PATCH /projects/{projectId}

Обновление настроек. Роли: **PO, PM, SA, GA**.

> Поле `icon_url` принимает только **HTTPS**-ссылки. Ссылки по протоколам `http://`, `file://` и другим отклоняются с `422 VALIDATION_ERROR`.

---

### DELETE /projects/{projectId}

Удаление проекта (устанавливает `status=deleted`). Роли: **PO, SA**.

---

### POST /projects/{projectId}/archive

Архивирование проекта. Роли: **PO, SA**.

---

### POST /projects/{projectId}/unarchive

Восстановление архивного проекта.

---

### Управление участниками проекта

| Метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/projects/{id}/members` | Список участников с ролями |
| `POST` | `/projects/{id}/members` | Добавить участника |
| `PATCH` | `/projects/{id}/members/{userId}` | Изменить роль |
| `DELETE` | `/projects/{id}/members/{userId}` | Удалить участника |

**Добавление участника:**
```json
{
  "user_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "role": "DEV"
}
```

> Пользователь должен быть членом рабочего пространства. Нельзя назначить роль выше своей.

---

## 9. Метки

Метки создаются на уровне **рабочего пространства** и применяются к задачам в любом проекте.

| Метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/workspaces/{id}/labels` | Список меток |
| `POST` | `/workspaces/{id}/labels` | Создать метку |
| `PATCH` | `/workspaces/{id}/labels/{labelId}` | Обновить метку |
| `DELETE` | `/workspaces/{id}/labels/{labelId}` | Удалить метку |

**Создание метки:**
```json
{
  "name": "срочно",
  "color": "#FF5733"
}
```

---

## 10. Задачи

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

---

## 11. Настраиваемые поля

### Определения полей

| Метод | Эндпоинт | Роли |
|---|---|---|
| `GET` | `/projects/{id}/custom-fields` | Все участники |
| `POST` | `/projects/{id}/custom-fields` | PO, PM, SA, GA |
| `PATCH` | `/projects/{id}/custom-fields/{fieldId}` | PO, PM, SA, GA |
| `DELETE` | `/projects/{id}/custom-fields/{fieldId}` | PO, SA |

**Создание поля:**
```json
{
  "name": "Среда",
  "field_type": "select",
  "options": ["production", "staging", "development"],
  "is_required": false,
  "position": 1
}
```

**Типы полей:** `text`, `number`, `date`, `select`, `multi_select`, `user`, `url`.

---

### Значения полей на задаче

| Метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/tasks/{id}/custom-field-values` | Все значения для задачи |
| `PUT` | `/tasks/{id}/custom-field-values/{fieldId}` | Установить значение |

```json
{ "value": "production" }
```

> Для `multi_select` передайте JSON-массив как строку: `"[\"opt1\",\"opt2\"]"`.

---

## 12. Комментарии и реакции

### GET /tasks/{taskId}/comments

Список комментариев в потоковом виде. Для вложенных ответов используйте параметр `parent_comment_id`.

---

### POST /tasks/{taskId}/comments

Публикация комментария. Минимальная роль: **VW**.  
Тело комментария — документ в формате **ProseMirror JSON**.

```json
{
  "body": {
    "type": "doc",
    "content": [{
      "type": "paragraph",
      "content": [{ "type": "text", "text": "Выглядит хорошо, можно мержить!" }]
    }]
  },
  "parent_comment_id": null
}
```

---

### PATCH /comments/{commentId}

Редактирование комментария. Только автор (в течение 24 ч после публикации) или **SA**.  
Флаг `is_edited` автоматически устанавливается в `true`.

---

### DELETE /comments/{commentId}

Мягкое удаление. Роли: автор, **PM, PO, SA**.

---

### Реакции на комментарии

| Метод | Эндпоинт | Описание |
|---|---|---|
| `POST` | `/comments/{id}/reactions` | Добавить реакцию |
| `DELETE` | `/comments/{id}/reactions/{emoji}` | Удалить реакцию |

```json
{ "emoji": "👍" }
```

---

## 13. Вложения

| Метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/tasks/{id}/attachments` | Список файлов с URL загрузки |
| `POST` | `/tasks/{id}/attachments` | Загрузить файл |
| `DELETE` | `/attachments/{attachmentId}` | Удалить файл |

**Загрузка файла** (multipart/form-data):
```
POST /tasks/tsk_001/attachments
Content-Type: multipart/form-data

file=<binary>
comment_id=<uuid> (опционально)
```

- Максимальный размер файла: **50 МБ**
- Ссылки на скачивание (`download_url`) — предподписанные URL с временем жизни **1 час**
- Минимальная роль для загрузки: **DEV**

---

## 14. Уведомления

### GET /notifications

Список уведомлений текущего пользователя.

```http
GET /notifications?is_read=false&type=assigned
```

**Типы уведомлений:** `assigned`, `mentioned`, `commented`, `status_changed`, `due_soon`, `overdue`, `invited`, `role_changed`.

---

### PATCH /notifications/{notificationId}

```json
{ "is_read": true }
```

---

### POST /notifications/read-all

Отмечает все уведомления как прочитанные.

**Ответ:**
```json
{ "marked_count": 14 }
```

---

### DELETE /notifications/{notificationId}

Удаление уведомления (только получатель).

---

## 15. Журнал активности

Неизменяемый аудит-трейл всех значимых изменений.

### GET /projects/{projectId}/activity

История изменений проекта.

**Фильтры:** `entity_type`, `actor_id`, `action`, `since`, `until`.

```http
GET /projects/proj_789/activity?entity_type=task&action=status_changed&since=2024-04-01T00:00:00Z
```

**Пример записи:**
```json
{
  "id": "...",
  "entity_type": "task",
  "entity_id": "a1b2c3d4-...",
  "actor": { "id": "...", "display_name": "Alice Smith" },
  "action": "status_changed",
  "old_value": { "status": "in_progress" },
  "new_value": { "status": "in_review" },
  "created_at": "2024-04-10T15:42:00Z"
}
```

---

### GET /tasks/{taskId}/activity

История конкретной задачи.

---

## 16. Спринты

### GET /projects/{projectId}/sprints

```http
GET /projects/proj_789/sprints?status=active
```

---

### POST /projects/{projectId}/sprints

Роли: **PM, PO, SA**.

```json
{
  "name": "Спринт 5",
  "goal": "Завершить модуль аутентификации",
  "start_date": "2024-04-01",
  "end_date": "2024-04-14"
}
```

| Поле | Ограничения |
|---|---|
| `name` | Обязательное, максимум **200 символов** |
| `goal` | Опциональное, максимум **1000 символов** |

---

### GET /sprints/{sprintId}

Детали спринта со статистикой задач:

```json
{
  "id": "9a5e6f1c-...",
  "name": "Спринт 5",
  "status": "active",
  "task_stats": {
    "total": 18,
    "completed": 11,
    "in_progress": 5,
    "total_story_points": 55,
    "completed_story_points": 34
  }
}
```

---

### POST /sprints/{sprintId}/start

Запуск спринта (`status → active`). Одновременно может быть активен только один спринт в проекте. Возвращает `409`, если уже есть активный.

---

### POST /sprints/{sprintId}/complete

Завершение спринта.

```json
{
  "incomplete_tasks_action": "next_sprint",
  "next_sprint_id": "d7e8f9a0-..."
}
```

| Поле | Значения | Описание |
|---|---|---|
| `incomplete_tasks_action` | `backlog` / `next_sprint` | Что делать с незавершёнными задачами |
| `next_sprint_id` | uuid | Обязательно при `next_sprint` |

---

### Задачи в спринте

| Метод | Эндпоинт | Описание |
|---|---|---|
| `POST` | `/sprints/{id}/tasks` | Добавить задачу в спринт |
| `DELETE` | `/sprints/{id}/tasks/{taskId}` | Убрать задачу из спринта |

---

## 17. Доски и колонки

### Доски

| Метод | Эндпоинт | Роли |
|---|---|---|
| `GET` | `/projects/{id}/boards` | Все участники |
| `POST` | `/projects/{id}/boards` | PM, PO, SA |
| `GET` | `/boards/{id}` | Все участники |
| `PATCH` | `/boards/{id}` | PM, PO, SA |
| `DELETE` | `/boards/{id}` | PM, PO, SA |

**Создание доски:**
```json
{
  "name": "Основная доска",
  "type": "kanban",
  "is_default": true
}
```

---

### Колонки доски

| Метод | Эндпоинт | Описание |
|---|---|---|
| `GET` | `/boards/{id}/columns` | Список колонок |
| `POST` | `/boards/{id}/columns` | Создать колонку |
| `PATCH` | `/boards/{id}/columns/{columnId}` | Обновить колонку |
| `DELETE` | `/boards/{id}/columns/{columnId}` | Удалить колонку |

**Создание колонки:**
```json
{
  "name": "На ревью",
  "status_mapping": "in_review",
  "position": 3,
  "wip_limit": 5
}
```

| Поле | Описание |
|---|---|
| `status_mapping` | Привязка к статусу задачи: `backlog`, `todo`, `in_progress`, `in_review`, `done`, `cancelled` |
| `wip_limit` | Максимум задач в колонке; `null` — без ограничения |

---

## 18. Учёт рабочего времени

### GET /tasks/{taskId}/time-logs

Список записей с суммарным временем (`meta.total_minutes`).

```http
GET /tasks/tsk_001/time-logs?since=2024-04-01&until=2024-04-30
```

---

### POST /tasks/{taskId}/time-logs

Минимальная роль: **DEV**.

```json
{
  "logged_minutes": 90,
  "logged_date": "2024-04-10",
  "description": "Реализовал валидацию токенов и механизм обновления"
}
```

> Поле `logged_minutes`: минимум `1`, максимум `1440` (24 часа) на одну запись. Значение `422 VALIDATION_ERROR` при превышении диапазона.

---

### PATCH /time-logs/{logId}

### DELETE /time-logs/{logId}

Изменение и удаление: только владелец записи или **SA**.

---

## 19. Аналитика

### GET /projects/{projectId}/snapshots

Исторические снимки метрик для **burndown**- и **velocity**-диаграмм.

```http
GET /projects/proj_789/snapshots?sprint_id=spr_101&since=2024-04-01&until=2024-04-14
```

**Пример записи снимка:**
```json
{
  "snapshot_date": "2024-04-07",
  "total_tasks": 42,
  "completed_tasks": 18,
  "in_progress_tasks": 10,
  "overdue_tasks": 3,
  "total_story_points": 144,
  "completed_story_points": 61
}
```

---

### GET /projects/{projectId}/metrics/users

Агрегированные метрики участников за период. Роли: **PM, PO, SA, GA**.

```http
GET /projects/proj_789/metrics/users?since=2024-04-01&until=2024-04-30&user_id=usr_456
```

---

### GET /projects/{projectId}/metrics/summary

Сводка состояния проекта в реальном времени для дашборда.

**Ответ:**
```json
{
  "total_tasks": 87,
  "open_tasks": 42,
  "completed_tasks": 38,
  "overdue_tasks": 7,
  "total_story_points": 210,
  "completed_story_points": 130,
  "velocity": 34.5,
  "active_sprint": {
    "id": "9a5e6f1c-...",
    "name": "Спринт 5",
    "end_date": "2024-04-14"
  }
}
```

`velocity` — среднее количество завершённых story points за последние 3 спринта.

---

### GET /users/{userId}/metrics

Индивидуальные метрики пользователя. Владелец метрик, SA/GA, или PM/PO в общем проекте.

```http
GET /users/usr_456/metrics?since=2024-01-01&until=2024-03-31&project_id=proj_789
```

**Ответ (пример одной записи):**
```json
{
  "user": { "id": "...", "display_name": "Alice Smith" },
  "project_id": "proj_789",
  "tasks_created": 12,
  "tasks_completed": 9,
  "tasks_assigned": 15,
  "comments_posted": 34,
  "logged_minutes": 5400
}
```

---

## 20. Лимиты и ограничения

### Rate Limits

| Категория | Лимит |
|---|---|
| Стандартные запросы | 1 000 запросов / минуту |
| Загрузка файлов | 100 загрузок / час |
| Регистрация пользователей | 10 в час с одного IP |

Заголовки ответа при rate limiting:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1712500000
```

При превышении лимита возвращается `HTTP 429 Too Many Requests`.

### Ограничения файлов

| Параметр | Значение |
|---|---|
| Максимальный размер файла | 50 МБ |
| Время жизни pre-signed URL | 1 час |

### Прочие ограничения

| Параметр | Значение |
|---|---|
| Максимум элементов на странице | 100 |
| Максимальный уровень вложенности подзадач | 5 |
| Одновременно активных спринтов на проект | 1 |

---

## Webhook-события (справочно)

Система генерирует следующие события, которые можно использовать для интеграций:

| Событие | Описание |
|---|---|
| `task.created` | Создана задача |
| `task.updated` | Задача обновлена |
| `task.deleted` | Задача удалена |
| `task.status_changed` | Изменён статус задачи |
| `task.assigned` | Назначен исполнитель |
| `comment.created` | Добавлен комментарий |
| `comment.deleted` | Комментарий удалён |
| `sprint.started` | Спринт запущен |
| `sprint.completed` | Спринт завершён |
| `project.created` | Создан проект |
| `project.archived` | Проект архивирован |
| `project.deleted` | Проект удалён |
| `member.added` | Участник добавлен |
| `member.removed` | Участник удалён |
| `member.role_changed` | Роль участника изменена |

---

*Task Tracker API v1.0 — документация актуальна на момент последнего обновления.*

---

## 21. Мои задачи (My Tasks Board)

### GET /api/tasks/my/

Возвращает все задачи, назначенные на текущего пользователя, **по всем проектам** в которых он участвует.
Исключает задачи со статусом `cancelled` и удалённые задачи (`deleted_at IS NOT NULL`).

**Аутентификация:** Bearer token (обязательно)

**Query параметры:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `status` | string, comma-separated | Фильтр по статусу(ам): `backlog`, `todo`, `in_progress`, `in_review`, `done` |

**Пример запроса:**
```http
GET /api/tasks/my/?status=backlog,todo,in_progress
Authorization: Bearer <token>
```

**Ответ `200 OK`:** массив объектов `Task` (тот же формат, что у `/api/projects/<id>/tasks/`).

---

### Поле `labels` в объекте Task

Начиная с текущей версии, все ответы содержащие объект `Task` включают поле `labels`:

```json
{
  "id": "uuid",
  "title": "...",
  "labels": [
    { "id": "uuid", "name": "Security", "color": "#7c3aed" }
  ],
  "..."
}
```

Если у задачи нет меток — возвращается пустой массив `[]`.
