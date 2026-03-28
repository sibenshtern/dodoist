---
sidebar_position: 4
---

# Технологии

Краткий обзор стека. Ничего экзотического — всё выбиралось по принципу «минимум удивлений».

---

## Фронтенд

Angular 21 со standalone-компонентами, Signals и TypeScript 5. Библиотека компонентов — TaigaUI v4: кнопки, диалоги, Toast-уведомления. Форм-контролы из TaigaUI используются выборочно — там, где нативный HTML неудобен. Реактивные потоки через RxJS: HTTP-запросы, управление состоянием.

---

## Бэкенд

Python 3.12 + Django 5. REST API через Django REST Framework — сериализаторы, ViewSet-ы. Аутентификация через JWT: access-токен живёт 15 минут, refresh — 30 дней. Библиотека Simple JWT.

---

## База данных

PostgreSQL 16 — единственная база данных в проекте. UUID-первичные ключи, JSONB для описаний задач (ProseMirror), float8 для порядка при drag-and-drop.

---

## Инфраструктура

Nginx как реверс-прокси перед Django и раздача статики Angular SPA. Локальная разработка через Docker Compose — один `docker-compose.yml` поднимает Angular dev-сервер, Django и PostgreSQL. Деплой документации автоматизирован через GitHub Actions при пуше в `main`.

---

## Документация

Docusaurus 3, Markdown + MDX. Диаграммы архитектуры через LikeC4 в формате C4 — модель описывается в `.c4`-файлах и рендерится в браузере через сгенерированный React-модуль.

---

## Инструменты разработки

ESLint и Prettier для TypeScript, Ruff для Python. База данных локально — pgAdmin или DBeaver.
