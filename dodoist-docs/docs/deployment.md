---
sidebar_position: 6
---

# Деплой документации

Разовая настройка сервера плюс GitHub Actions — и дальше документация деплоится сама при каждом пуше в `main`.

---

## Разовая настройка сервера

Предполагается: сервер с Nginx, SSH-доступ, домен `dodoist.sibenshtern.ru`.

### 1. Установить Node.js на сервере

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### 2. Создать директорию для статики

```bash
sudo mkdir -p /var/www/docs
sudo chown $USER:$USER /var/www/docs
```

### 3. Настроить Nginx

Создать файл `/etc/nginx/sites-available/docs`:

```nginx
server {
    listen 80;
    server_name dodoist.sibenshtern.ru;

    root /var/www/docs;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Включить конфигурацию:

```bash
sudo ln -s /etc/nginx/sites-available/docs /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

Для HTTPS — выпустить сертификат через Certbot:

```bash
sudo certbot --nginx -d dodoist.sibenshtern.ru
```

---

## Ручной деплой

Для первого деплоя или экстренного обновления:

```bash
cd dodoist-docs

# Установить зависимости (если не установлены)
npm ci

# Собрать статику
npm run build

# Скопировать на сервер
rsync -avz --delete build/ user@dodoist.sibenshtern.ru:/var/www/docs/
```

После `rsync` сайт доступен сразу — Nginx отдаёт файлы напрямую.

---

## Автоматический деплой через GitHub Actions

При каждом пуше в `main` GitHub Actions собирает документацию и деплоит на сервер по SSH.

### Добавить секреты в репозиторий

Перейти в `Settings → Secrets and variables → Actions` и добавить:

| Имя | Значение |
|-----|---------|
| `DOCS_SSH_KEY` | Приватный SSH-ключ (без парольной фразы) |
| `DOCS_HOST` | IP или домен сервера |
| `DOCS_USER` | Имя пользователя на сервере |
| `DOCS_PATH` | Путь до директории — `/var/www/docs` |

Публичный ключ добавить на сервер:

```bash
# На локальной машине — сгенерировать пару ключей для CI
ssh-keygen -t ed25519 -C "github-actions-docs" -f ~/.ssh/docs_deploy

# Публичный ключ добавить на сервер
ssh-copy-id -i ~/.ssh/docs_deploy.pub user@dodoist.sibenshtern.ru

# Содержимое приватного ключа (~/.ssh/docs_deploy) скопировать в секрет DOCS_SSH_KEY
```

### Создать workflow

Файл `.github/workflows/deploy-docs.yml`:

```yaml
name: Deploy docs

on:
  push:
    branches: [main]
    paths:
      - 'dodoist-docs/**'

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: dodoist-docs/package-lock.json

      - name: Install dependencies
        working-directory: dodoist-docs
        run: npm ci

      - name: Build
        working-directory: dodoist-docs
        run: npm run build

      - name: Deploy via rsync
        uses: burnett01/rsync-deployments@7.0.1
        with:
          switches: -avz --delete
          path: dodoist-docs/build/
          remote_path: ${{ secrets.DOCS_PATH }}
          remote_host: ${{ secrets.DOCS_HOST }}
          remote_user: ${{ secrets.DOCS_USER }}
          remote_key: ${{ secrets.DOCS_SSH_KEY }}
```

Поле `paths: - 'dodoist-docs/**'` ограничивает запуск: деплой происходит только если изменились файлы внутри `dodoist-docs/`. Пуши в другие части репозитория workflow не запускают.

---

## Обновление диаграмм LikeC4

Диаграммы архитектуры генерируются из `.c4`-файлов в статический React-модуль. После изменения `.c4`-файлов нужно перегенерировать модуль:

```bash
cd dodoist-docs
npx likec4 gen react -o src/generated/likec4.mjs .
```

Закоммитить `src/generated/likec4.mjs` и `src/generated/likec4.d.mts` — GitHub Actions подхватит изменения автоматически.

---

## Проверка деплоя

После пуша открыть вкладку `Actions` в репозитории. Если workflow зелёный — сайт уже обновился, `rsync` быстрый.
