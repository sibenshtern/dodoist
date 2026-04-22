# Описание базы данных — Task Tracker v1.0

Гибридный трекер задач (Todoist + Jira) с аналитикой. Модель данных разделена на шесть логических доменов.

---

## Содержание

1. [Идентификация и доступ](#1-идентификация-и-доступ)
2. [Организация](#2-организация)
3. [Работа с задачами](#3-работа-с-задачами)
4. [Совместная работа](#4-совместная-работа)
5. [Планирование](#5-планирование)
6. [Аналитика](#6-аналитика)
7. [Ключевые решения](#7-ключевые-решения)

---

## 1. Идентификация и доступ

### `users` — Пользователи

Центральная запись пользователя. Глобальные роли SA и GA обходят все проверки прав на уровне проекта.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `email` | varchar UNIQUE | Электронная почта (уникальная) |
| `display_name` | varchar | Отображаемое имя |
| `avatar_url` | varchar | URL аватара |
| `timezone` | varchar | Часовой пояс (по умолчанию `UTC`) |
| `global_role` | enum | Глобальная роль: `SA` \| `GA` \| `member` |
| `password_hash` | varchar | Хэш пароля |
| `is_active` | boolean | Активен ли аккаунт |
| `created_at` | timestamptz | Дата создания |
| `updated_at` | timestamptz | Дата последнего обновления |
| `last_login_at` | timestamptz | Дата последнего входа |

---

### `user_sessions` — Сессии пользователей

Активные токены аутентификации для веб- и мобильных клиентов.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `user_id` | uuid FK → users | Пользователь |
| `token_hash` | varchar | Хэш токена сессии |
| `device_info` | varchar | Информация об устройстве |
| `ip_address` | inet | IP-адрес клиента |
| `expires_at` | timestamptz | Дата и время истечения сессии |
| `created_at` | timestamptz | Дата создания |

---

### `user_preferences` — Настройки пользователей

Персональные настройки интерфейса и уведомлений. Одна запись на пользователя.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `user_id` | uuid FK → users UNIQUE | Пользователь |
| `theme` | enum | Тема интерфейса: `light` \| `dark` \| `system` |
| `language` | varchar | Язык интерфейса (по умолчанию `en`) |
| `notification_channels` | jsonb | Каналы уведомлений: `email` \| `push` \| `in_app` |
| `digest_frequency` | enum | Периодичность дайджеста: `realtime` \| `daily` \| `weekly` |
| `default_view` | enum | Вид по умолчанию: `list` \| `board` \| `calendar` |
| `updated_at` | timestamptz | Дата последнего обновления |

---

## 2. Организация

### `workspaces` — Рабочие пространства

Контейнер верхнего уровня для проектов. Может представлять компанию, команду или личное пространство. Каждый проект принадлежит ровно одному рабочему пространству.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `slug` | varchar UNIQUE | Уникальный URL-идентификатор |
| `name` | varchar | Название |
| `description` | text | Описание |
| `owner_id` | uuid FK → users | Владелец |
| `plan` | enum | Тарифный план: `free` \| `pro` \| `business` |
| `is_personal` | boolean | Личное пространство (автосоздаётся для каждого пользователя) |
| `created_at` | timestamptz | Дата создания |
| `updated_at` | timestamptz | Дата обновления |

---

### `workspace_members` — Участники рабочего пространства

Членство пользователей в рабочем пространстве — обязательное условие для добавления в проект.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `workspace_id` | uuid FK → workspaces | Рабочее пространство |
| `user_id` | uuid FK → users | Пользователь |
| `joined_at` | timestamptz | Дата вступления |

> Уникальность: `(workspace_id, user_id)`

---

### `projects` — Проекты

Основной контейнер задач. Может быть рабочим (Jira-стиль: спринты, доски) или личным (Todoist-стиль: плоский список).

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `workspace_id` | uuid FK → workspaces | Рабочее пространство |
| `name` | varchar | Название проекта |
| `description` | text | Описание |
| `key` | varchar | Короткий код проекта (уникален в пространстве, напр. `PROJ`) |
| `color` | varchar | Цвет для отображения |
| `icon_url` | varchar | URL иконки |
| `status` | enum | Статус: `active` \| `archived` \| `deleted` |
| `type` | enum | Тип: `scrum` \| `kanban` \| `personal` |
| `is_private` | boolean | Приватный проект |
| `created_by` | uuid FK → users | Создатель |
| `created_at` | timestamptz | Дата создания |
| `updated_at` | timestamptz | Дата обновления |
| `archived_at` | timestamptz | Дата архивации |

> Уникальность: `(workspace_id, key)`

---

### `project_members` — Участники проекта

Назначение проектной роли пользователю. Один пользователь может иметь разные роли в разных проектах.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `project_id` | uuid FK → projects | Проект |
| `user_id` | uuid FK → users | Пользователь |
| `role` | enum | Роль: `PO` \| `PM` \| `DEV` \| `VW` \| `GU` |
| `invited_by` | uuid FK → users | Кто пригласил |
| `joined_at` | timestamptz | Дата вступления |
| `updated_at` | timestamptz | Дата последнего изменения роли |

> Уникальность: `(project_id, user_id)`

**Роли:** `PO` — владелец проекта, `PM` — менеджер, `DEV` — разработчик/контрибьютор, `VW` — наблюдатель, `GU` — гость.

---

### `labels` — Метки

Цветные теги в рамках рабочего пространства. Используются для фильтрации и аналитики.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `workspace_id` | uuid FK → workspaces | Рабочее пространство |
| `name` | varchar | Название метки |
| `color` | varchar | Цвет (hex или название) |
| `created_by` | uuid FK → users | Создатель |
| `created_at` | timestamptz | Дата создания |

> Уникальность: `(workspace_id, name)`

---

## 3. Работа с задачами

### `tasks` — Задачи

Ключевая сущность. Единица работы в личном или рабочем контексте. Поддерживает иерархию (подзадачи через `parent_task_id`), доску, спринты, приватность.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `project_id` | uuid FK → projects | Проект |
| `parent_task_id` | uuid FK → tasks | Родительская задача (для подзадач, nullable) |
| `sprint_id` | uuid FK → sprints | Спринт (nullable) |
| `board_column_id` | uuid FK → board_columns | Колонка доски (nullable) |
| `created_by` | uuid FK → users | Создатель |
| `assigned_to` | uuid FK → users | Основной исполнитель (nullable) |
| `title` | varchar | Заголовок |
| `description` | jsonb | Описание в формате rich-text (ProseMirror JSON) |
| `type` | enum | Тип: `task` \| `bug` \| `story` \| `epic` \| `personal` |
| `status` | enum | Статус: `backlog` \| `todo` \| `in_progress` \| `in_review` \| `done` \| `cancelled` |
| `priority` | enum | Приоритет: `critical` \| `high` \| `medium` \| `low` \| `none` |
| `story_points` | int | Story points (nullable) |
| `due_date` | timestamptz | Срок выполнения |
| `start_date` | timestamptz | Дата начала |
| `reminder_at` | timestamptz | Дата напоминания |
| `position` | float8 | Порядковая позиция (для drag-and-drop) |
| `is_private` | boolean | Приватная задача (видна только создателю и исполнителю) |
| `created_at` | timestamptz | Дата создания |
| `updated_at` | timestamptz | Дата обновления |
| `completed_at` | timestamptz | Дата завершения |
| `deleted_at` | timestamptz | Мягкое удаление (soft delete) |

---

### `task_assignments` — Дополнительные исполнители

Поддержка нескольких исполнителей на задачу. Основной исполнитель хранится в `tasks.assigned_to`, остальные — в этой таблице.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `task_id` | uuid FK → tasks | Задача |
| `user_id` | uuid FK → users | Исполнитель |
| `assigned_by` | uuid FK → users | Кто назначил |
| `assigned_at` | timestamptz | Дата назначения |

> Уникальность: `(task_id, user_id)`

---

### `task_labels` — Метки задач

Связь многие-ко-многим между задачами и метками.

| Поле | Тип | Описание |
|---|---|---|
| `task_id` | uuid FK → tasks | Задача |
| `label_id` | uuid FK → labels | Метка |

> Первичный ключ: `(task_id, label_id)`

---

### `task_dependencies` — Зависимости задач

Связи между задачами: блокировки, дубли, связанные задачи.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `task_id` | uuid FK → tasks | Исходная задача |
| `depends_on_task_id` | uuid FK → tasks | Зависимая задача |
| `type` | enum | Тип: `blocks` \| `is_blocked_by` \| `relates_to` \| `duplicates` \| `is_duplicated_by` |
| `created_by` | uuid FK → users | Создатель связи |
| `created_at` | timestamptz | Дата создания |

---

### `task_guest_access` — Доступ гостей к задачам

Явное предоставление доступа к отдельным задачам для пользователей с ролью `GU` (гость).

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `task_id` | uuid FK → tasks | Задача |
| `user_id` | uuid FK → users | Гость |
| `granted_by` | uuid FK → users | Кто предоставил доступ |
| `granted_at` | timestamptz | Дата предоставления |
| `expires_at` | timestamptz | Дата истечения доступа (nullable) |

> Уникальность: `(task_id, user_id)`

---

### `custom_fields` — Настраиваемые поля

Определения кастомных полей на уровне проекта (например, «Среда», «Клиент»).

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `project_id` | uuid FK → projects | Проект |
| `name` | varchar | Название поля |
| `field_type` | enum | Тип: `text` \| `number` \| `date` \| `select` \| `multi_select` \| `user` \| `url` |
| `options` | jsonb | Варианты значений (для типов `select` / `multi_select`) |
| `is_required` | boolean | Обязательное поле |
| `position` | int | Порядок отображения |
| `created_by` | uuid FK → users | Создатель |
| `created_at` | timestamptz | Дата создания |

---

### `task_custom_field_values` — Значения настраиваемых полей

Хранит конкретные значения кастомных полей для каждой задачи.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `task_id` | uuid FK → tasks | Задача |
| `custom_field_id` | uuid FK → custom_fields | Поле |
| `value` | text | Значение поля |
| `updated_at` | timestamptz | Дата обновления |

> Уникальность: `(task_id, custom_field_id)`

---

## 4. Совместная работа

### `comments` — Комментарии

Ветвящиеся комментарии к задачам. Поддерживает ответы через `parent_comment_id`.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `task_id` | uuid FK → tasks | Задача |
| `author_id` | uuid FK → users | Автор |
| `parent_comment_id` | uuid FK → comments | Родительский комментарий (для ответов, nullable) |
| `body` | jsonb | Текст в формате rich-text (ProseMirror JSON) |
| `is_edited` | boolean | Был ли отредактирован |
| `created_at` | timestamptz | Дата создания |
| `updated_at` | timestamptz | Дата обновления |
| `deleted_at` | timestamptz | Мягкое удаление |

---

### `attachments` — Вложения

Файлы, прикреплённые к задачам или комментариям. Файлы хранятся во внешнем объектном хранилище (S3/GCS).

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `task_id` | uuid FK → tasks | Задача (nullable) |
| `comment_id` | uuid FK → comments | Комментарий (nullable) |
| `uploaded_by` | uuid FK → users | Кто загрузил |
| `filename` | varchar | Имя файла |
| `file_size_bytes` | bigint | Размер файла в байтах |
| `mime_type` | varchar | MIME-тип |
| `storage_key` | varchar | Путь к файлу в хранилище |
| `created_at` | timestamptz | Дата загрузки |

> Должно быть заполнено хотя бы одно из полей: `task_id` или `comment_id`.

---

### `reactions` — Реакции

Эмодзи-реакции на комментарии.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `comment_id` | uuid FK → comments | Комментарий |
| `user_id` | uuid FK → users | Пользователь |
| `emoji` | varchar | Эмодзи |
| `created_at` | timestamptz | Дата создания |

> Уникальность: `(comment_id, user_id, emoji)`

---

### `notifications` — Уведомления

Внутренние уведомления о назначениях, упоминаниях, дедлайнах и других событиях.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `recipient_id` | uuid FK → users | Получатель |
| `actor_id` | uuid FK → users | Инициатор действия (nullable) |
| `type` | enum | Тип: `assigned` \| `mentioned` \| `commented` \| `status_changed` \| `due_soon` \| `overdue` \| `invited` \| `role_changed` |
| `task_id` | uuid FK → tasks | Связанная задача (nullable) |
| `project_id` | uuid FK → projects | Связанный проект (nullable) |
| `message` | text | Текст уведомления |
| `is_read` | boolean | Прочитано |
| `created_at` | timestamptz | Дата создания |
| `read_at` | timestamptz | Дата прочтения |

---

### `activity_log` — Журнал активности

Неизменяемый аудит-трейл всех значимых изменений задач и проектов. Источник истины для событийной аналитики.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `entity_type` | enum | Тип сущности: `task` \| `project` \| `sprint` \| `comment` |
| `entity_id` | uuid | ID изменённой сущности |
| `actor_id` | uuid FK → users | Кто произвёл изменение |
| `action` | varchar | Действие (напр. `status_changed`, `assigned`) |
| `old_value` | jsonb | Предыдущее значение |
| `new_value` | jsonb | Новое значение |
| `project_id` | uuid FK → projects | Проект (nullable) |
| `created_at` | timestamptz | Дата события |

---

## 5. Планирование

### `sprints` — Спринты

Ограниченные по времени итерации для Scrum-проектов. В один момент времени у проекта может быть только один активный спринт.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `project_id` | uuid FK → projects | Проект |
| `name` | varchar | Название спринта |
| `goal` | text | Цель спринта |
| `status` | enum | Статус: `planned` \| `active` \| `completed` |
| `start_date` | date | Дата начала |
| `end_date` | date | Дата окончания |
| `created_by` | uuid FK → users | Создатель |
| `created_at` | timestamptz | Дата создания |
| `updated_at` | timestamptz | Дата обновления |
| `completed_at` | timestamptz | Дата завершения |

---

### `boards` — Доски

Kanban или Scrum-доски проекта. Один проект может иметь несколько досок.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `project_id` | uuid FK → projects | Проект |
| `name` | varchar | Название доски |
| `type` | enum | Тип: `kanban` \| `scrum` |
| `is_default` | boolean | Доска по умолчанию |
| `created_by` | uuid FK → users | Создатель |
| `created_at` | timestamptz | Дата создания |
| `updated_at` | timestamptz | Дата обновления |

---

### `board_columns` — Колонки доски

Упорядоченные колонки доски, представляющие этапы рабочего процесса.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `board_id` | uuid FK → boards | Доска |
| `name` | varchar | Название колонки |
| `status_mapping` | enum | Связанный статус задачи: `backlog` \| `todo` \| `in_progress` \| `in_review` \| `done` \| `cancelled` |
| `position` | int | Порядок колонки на доске |
| `wip_limit` | int | Лимит задач в колонке (nullable) |
| `created_at` | timestamptz | Дата создания |
| `updated_at` | timestamptz | Дата обновления |

---

## 6. Аналитика

### `time_logs` — Журнал рабочего времени

Ручная фиксация затраченного времени на задачу.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `task_id` | uuid FK → tasks | Задача |
| `user_id` | uuid FK → users | Пользователь |
| `logged_minutes` | int | Количество залогированных минут |
| `description` | text | Описание работы (nullable) |
| `logged_date` | date | Дата выполнения работы |
| `created_at` | timestamptz | Дата записи |
| `updated_at` | timestamptz | Дата обновления |

---

### `task_snapshots` — Снимки метрик задач

Периодические срезы состояния задач по проекту. Используются для burndown-диаграмм и velocity-трекинга. Формируются автоматически (ночной job или по событию).

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `project_id` | uuid FK → projects | Проект |
| `sprint_id` | uuid FK → sprints | Спринт (nullable) |
| `snapshot_date` | date | Дата среза |
| `total_tasks` | int | Всего задач |
| `completed_tasks` | int | Завершённых задач |
| `in_progress_tasks` | int | Задач в работе |
| `overdue_tasks` | int | Просроченных задач |
| `total_story_points` | int | Всего story points |
| `completed_story_points` | int | Завершённых story points |
| `created_at` | timestamptz | Дата создания записи |

> Уникальность: `(project_id, sprint_id, snapshot_date)`

---

### `user_metrics` — Метрики пользователей

Предагрегированные ежедневные метрики по пользователю и проекту. Основа дашбордов производительности и нагрузки.

| Поле | Тип | Описание |
|---|---|---|
| `id` | uuid PK | Уникальный идентификатор |
| `user_id` | uuid FK → users | Пользователь |
| `project_id` | uuid FK → projects | Проект (nullable — `NULL` означает сводку по всем проектам) |
| `metric_date` | date | Дата метрики |
| `tasks_created` | int | Создано задач |
| `tasks_completed` | int | Завершено задач |
| `tasks_assigned` | int | Назначено задач |
| `comments_posted` | int | Оставлено комментариев |
| `logged_minutes` | int | Залогировано минут |
| `created_at` | timestamptz | Дата создания записи |

> Уникальность: `(user_id, project_id, metric_date)`

---

## 7. Ключевые решения

**Личные и рабочие задачи** живут в одной схеме. Личные задачи хранятся в рабочем пространстве с `is_personal = true` в проекте типа `personal` — это даёт единый поиск, метки и аналитику.

**Права доступа** проверяются на уровне приложения по цепочке: `users.global_role` → `project_members.role` → `tasks.created_by` / `task_assignments` (для DEV) → `task_guest_access` (для GU).

**Мягкое удаление** (`deleted_at`) применяется к `tasks` и `comments` для сохранения истории и поддержки отмены действий.

**Порядок задач** хранится как число с плавающей точкой (`position float8`), что позволяет делать drag-and-drop без перенумерации строк.

**Аналитика** строится на двух уровнях: `activity_log` — источник истины для событийных данных; `task_snapshots` и `user_metrics` — предагрегированные таблицы для быстрых запросов дашбордов.

**Rich text** в `tasks.description` и `comments.body` хранится как сериализованный ProseMirror JSON с поддержкой упоминаний, вставок и форматирования.
