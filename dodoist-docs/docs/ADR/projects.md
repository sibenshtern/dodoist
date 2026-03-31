---
title: API для проектов
sidebar_index: 0
---

## Проекты

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
