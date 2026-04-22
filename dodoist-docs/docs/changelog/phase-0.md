---
sidebar_position: 1
title: Phase 0 — Стабилизация
---

# Phase 0 — Стабилизация и базовые улучшения

Первый этап финального плана разработки. Цель — устранить критические несоответствия в бизнес-логике, подключить инструменты для управления данными и улучшить UX формы создания задачи, не добавляя новых функций поверх нестабильного основания.

---

## Бэкенд

### 1. Ограничение WIP на колонке доски

**Файлы:** `tasks/services.py`, `tasks/views.py`, `tasks/tests.py`

#### Проблема

Модель `BoardColumn` содержит поле `wip_limit` (Work In Progress limit) — максимальное количество задач, которые могут одновременно находиться в колонке. Однако метод `TaskService.move_to_column` никак не проверял это ограничение: задачи можно было перемещать в переполненные колонки без каких-либо ошибок.

#### Решение

В метод `TaskService.move_to_column` добавлена проверка перед перемещением задачи:

```python
if column.wip_limit is not None:
    current_count = Task.objects.filter(
        board_column=column, deleted_at__isnull=True
    ).exclude(pk=task.pk).count()
    if current_count >= column.wip_limit:
        raise ValueError(
            f"WIP limit of {column.wip_limit} reached for column '{column.name}'."
        )
```

Логика исключает саму перемещаемую задачу (`exclude(pk=task.pk)`) — это корректно обрабатывает случай, когда задача перемещается внутри той же колонки (например, при смене позиции).

Представление `TaskMoveColumnView` обновлено: теперь ошибка, содержащая текст `"WIP limit"`, возвращает HTTP `409 Conflict` вместо `400 Bad Request`, что соответствует семантике спецификации (`409` — конфликт с текущим состоянием ресурса):

```python
status_code = 409 if "WIP limit" in msg else 400
return Response({"detail": msg}, status=status_code)
```

#### Поведение

| Ситуация | Результат |
|---|---|
| `wip_limit = null` | Перемещение разрешено всегда |
| Задач в колонке < `wip_limit` | Перемещение разрешено |
| Задач в колонке = `wip_limit` | `ValueError` → HTTP `409 Conflict` |
| Перемещение задачи, уже находящейся в этой колонке | Не считается как новая задача |

---

### 2. Django Admin

**Файлы:** `dodoist/settings.py`, `dodoist/urls.py`, `users/admin.py`, `projects/admin.py`, `tasks/admin.py`

#### Проблема

В проекте не был подключён стандартный административный интерфейс Django. Это затрудняет инспекцию данных в базе во время разработки и тестирования.

#### Решение

**`dodoist/settings.py`** — добавлены необходимые приложения и middleware:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # ... остальные приложения
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
```

Также добавлены конфигурации `TEMPLATES` (необходимы для рендеринга страниц admin) и `STATIC_URL`.

**`dodoist/urls.py`** — подключён URL администратора:

```python
from django.contrib import admin

urlpatterns = [
    path("admin/", admin.site.urls),
    # ... остальные URL
]
```

**Зарегистрированные модели по приложениям:**

| Приложение | Модели |
|---|---|
| `users` | `User`, `UserSession`, `UserPreferences`, `Notification` |
| `projects` | `Workspace`, `WorkspaceMember`, `Project`, `ProjectMember`, `Label`, `Sprint`, `Board`, `BoardColumn` |
| `tasks` | `Task`, `TaskAssignment`, `TaskLabel`, `TaskDependency`, `TaskGuestAccess`, `CustomField`, `TaskCustomFieldValue`, `Comment`, `Reaction`, `TimeLog`, `ActivityLog` |

Для каждой модели настроены `list_display`, `list_filter`, `search_fields` и `ordering`.

**Миграции** — применены новые таблицы для `django.contrib.admin` и `django.contrib.sessions`:

```
Applying admin.0001_initial... OK
Applying admin.0002_logentry_remove_auto_add... OK
Applying admin.0003_logentry_add_action_flag_choices... OK
Applying sessions.0001_initial... OK
```

Административный интерфейс доступен по адресу: `http://localhost:8000/admin/`

---

## Фронтенд

### 3. Поиск родительской задачи с подсказками (typeahead)

**Файлы:** `task-create.component.ts`, `task-create.component.html`, `task-create.component.scss`, `task.service.ts`

#### Проблема

Поле «Родительская задача» в форме создания задачи было реализовано как обычный текстовый `<input>` с placeholder «Search tasks…». Пользователь должен был вручную вводить UUID задачи, что практически нереализуемо в обычном use case.

#### Решение

Реализован полноценный typeahead-компонент. При выборе проекта задачи этого проекта загружаются в память. Во время ввода список фильтруется на клиенте, и пользователю предлагается выпадающий список результатов.

**`TaskService`** — добавлен новый метод:

```typescript
getProjectTasks(projectId: string): Observable<Task[]> {
  return this.http.get<Task[]>(
    `${environment.apiBase}/api/projects/${projectId}/tasks/`
  );
}
```

**`TaskCreateComponent`** — новые сигналы и методы:

```typescript
readonly parentTaskSearch = signal('');
readonly parentTaskResults = signal<Task[]>([]);
readonly parentTaskSelected = signal<Task | null>(null);
readonly showParentDropdown = signal(false);
private allProjectTasks: Task[] = [];

onParentSearchInput(event: Event): void { ... }
selectParentTask(task: Task): void { ... }
clearParentTask(): void { ... }
```

При смене проекта задачи автоматически загружаются и кэшируются в `allProjectTasks`. Поиск работает по подстроке в заголовке задачи (регистронезависимо), возвращает не более 8 результатов.

**Шаблон** — вместо простого `<input>` появился составной блок:
- Если задача ещё не выбрана: текстовое поле для ввода запроса + выпадающий список результатов (по `mousedown`, чтобы не теряться при `blur`)
- Если задача выбрана: «чип» с заголовком задачи и кнопкой очистки `✕`
- Поле заблокировано (`disabled`), пока не выбран проект

#### Поведение

| Ситуация | Результат |
|---|---|
| Проект не выбран | Поле заблокировано |
| Проект выбран | Задачи проекта загружаются в фоне |
| Пользователь вводит текст | Отображается список совпадений (макс. 8) |
| Пользователь выбирает задачу | Поле заменяется «чипом» с заголовком; в форму записывается UUID |
| Пользователь нажимает `✕` | Выбор сбрасывается, поле очищается |
| Пользователь меняет проект | Выбор родительской задачи сбрасывается |

---

## Тесты

### Новый класс `TestWipLimit` в `tasks/tests.py`

Добавлено 4 теста для проверки ограничения WIP:

| Тест | Что проверяет |
|---|---|
| `test_move_to_column_respects_wip_limit` | При превышении лимита `TaskService.move_to_column` бросает `ValueError` с текстом `"WIP limit"` |
| `test_move_to_column_allows_within_limit` | Перемещение задач в количестве, не превышающем лимит, проходит успешно |
| `test_move_to_column_no_limit` | При `wip_limit = None` ограничений нет — 10 задач перемещаются без ошибок |
| `test_move_column_endpoint_returns_409_when_wip_exceeded` | HTTP-эндпоинт `POST /api/tasks/{pk}/move-column/` возвращает `409` при превышении лимита |

**Итог:** было 258 тестов → стало **262 теста**, все зелёные.

---

## Сводка изменённых файлов

### Бэкенд (`dodoist-backend/`)

| Файл | Тип изменения |
|---|---|
| `tasks/services.py` | Добавлена проверка `wip_limit` в `move_to_column` |
| `tasks/views.py` | `TaskMoveColumnView` возвращает `409` при WIP-конфликте |
| `tasks/tests.py` | Добавлен класс `TestWipLimit` (4 теста) |
| `tasks/admin.py` | Регистрация всех моделей приложения `tasks` |
| `projects/admin.py` | Регистрация всех моделей приложения `projects` |
| `users/admin.py` | Регистрация всех моделей приложения `users` |
| `dodoist/settings.py` | Добавлены `INSTALLED_APPS`, `MIDDLEWARE`, `TEMPLATES`, `STATIC_URL` для admin |
| `dodoist/urls.py` | Подключён `admin.site.urls` |

### Фронтенд (`dodoist-app/`)

| Файл | Тип изменения |
|---|---|
| `src/app/services/task.service.ts` | Добавлен метод `getProjectTasks(projectId)` |
| `src/app/pages/task-create/task-create.component.ts` | Typeahead-логика для поля «Родительская задача» |
| `src/app/pages/task-create/task-create.component.html` | Заменён `<input>` на typeahead-блок с выпадающим списком |
| `src/app/pages/task-create/task-create.component.scss` | Стили для `.typeahead-dropdown`, `.typeahead-option`, `.typeahead-selected` |
