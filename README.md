# 🎮 Spiratis Bot — Telegram бот для мониторинга раздач игр

## [![Start Bot](https://img.shields.io/badge/Telegram-Запустить%20бота-green?logo=telegram)](https://t.me/SpiratisBot)

---

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Aiogram](https://img.shields.io/badge/Aiogram-3.x-green)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue?logo=postgresql)
![Alembic](https://img.shields.io/badge/Alembic-Migrations-orange)
![Docker](https://img.shields.io/badge/Docker-Containerization-blue?logo=docker)

---
## 📌 О проекте

**Spiratis Bot** — это персональный агрегатор игровых раздач, который помогает пользователям собирать библиотеку игр, не тратя ни рубля. Бот автоматически отслеживает актуальные предложения на популярных площадках и присылает персонализированные уведомления.

### Основной функционал:
- 🔍 **Ручной поиск:** Мгновенная проверка актуальных раздач по кнопке.
- 🔔 **Авто-уведомления:** Ежедневная рассылка свежих предложений в 12:00.
- ⚙️ **Гибкие фильтры:**
    - **Устройства:** PC, PlayStation, Xbox, Android, iOS, Nintendo Switch.
    - **Платформы:** Steam, Epic Games Store и др.
    - **Типы контента:** Полные игры, DLC, Ранний доступ.
- 🕒 **Локализация времени:** Установка часового пояса для корректного отображения дедлайнов раздач.
- 🧹 **Авто-очистка:** Автоматическое удаление устаревших записей из базы данных.
- 🛡 **Защита от дублей:** Интеллектуальная система проверки отправленных игр.

---

## ⚙️ Стек технологий

- **Python 3.11**
- **Aiogram 3** — асинхронный фреймворк для Telegram Bot API.
- **SQLAlchemy 2 (async)** — работа с базой данных через ORM.
- **PostgreSQL** — надежное хранилище данных пользователей и истории раздач.
- **Alembic** — управление миграциями базы данных.
- **APScheduler** — планировщик для ежедневных рассылок и очистки БД.
- **HTTPX** — асинхронные запросы к API GamerPower.
- **Docker & Docker Compose** — быстрая развертка и контейнеризация.

---

## 🚀 Быстрый старт

### 1. Клонировать проект

```bash
git clone https://github.com/your-username/spiratis-bot.git
cd spiratis-bot
```
### 2. Создать .env файл
Создайте файл .env в корневой папке и заполните его:
```env
BOT_TOKEN=your_telegram_bot_token
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/spiratis_db
DB_USER=user
DB_PASSWORD=password
DB_NAME=spiratis_db
DB_CONTANER_NAME=spiratis_db
DB_RESTART_POLICY=always
DB_PORT_INTERNAL=5432
DB_PORT_EXTERNAL=5432
```
### 3. Запуск через Docker
Проект полностью готов к работе в контейнерах:
```bash
docker-compose up -d --build
```
### 4. Применить миграции
```bash
docker exec spiratis_bot alembic upgrade head
```
### 👤 Авторы
KarpX – ведущий разработчик:
[![Telegram](https://img.shields.io/badge/Contact-KarpX-blue?logo=telegram)](https://t.me/KarpXer)
### ⭐️ Поддержка
Если бот помог тебе забрать крутую игру — поставь ⭐️ на GitHub!
