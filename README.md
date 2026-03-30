# 🧸 ToyShop Backend — Полная инструкция для студентов

## Содержание
1. [Структура проекта](#структура-проекта)
2. [Установка Python](#1-установка-python)
3. [Установка PostgreSQL](#2-установка-postgresql)
4. [Создание базы данных](#3-создание-базы-данных)
5. [Открытие в PyCharm](#4-открытие-в-pycharm)
6. [Установка зависимостей](#5-установка-зависимостей)
7. [Настройка .env файла](#6-настройка-env-файла)
8. [Миграции Alembic](#7-запуск-миграций-alembic)
9. [Заполнение тестовыми данными](#8-заполнение-тестовыми-данными)
10. [Запуск сервера](#9-запуск-сервера)
11. [Проверка в Swagger](#10-проверка-api-через-swagger)
12. [Что делает каждый файл](#что-делает-каждый-файл)
13. [ER-диаграмма базы данных](#er-диаграмма)

---

## Структура проекта

```
backend/
│
├── app/                     ← Основной код приложения
│   ├── __init__.py
│   ├── main.py              ← Точка входа (создаёт FastAPI-приложение)
│   ├── config.py            ← Настройки (читает .env файл)
│   ├── database.py          ← Подключение к PostgreSQL
│   │
│   ├── models/              ← SQLAlchemy-модели (= таблицы в БД)
│   │   ├── user.py          ← Таблица users
│   │   ├── product.py       ← Таблицы categories, products, product_characteristics
│   │   ├── order.py         ← Таблицы carts, orders, pickup_points
│   │   └── review.py        ← Таблица reviews
│   │
│   ├── schemas/             ← Pydantic-схемы (= формат данных в API)
│   │   ├── user.py          ← Схемы для пользователей
│   │   ├── product.py       ← Схемы для товаров
│   │   ├── order.py         ← Схемы для корзины и заказов
│   │   └── review.py        ← Схемы для отзывов
│   │
│   ├── crud/                ← CRUD-операции (работа с базой данных)
│   │   ├── user.py          ← Создать/найти/обновить пользователя
│   │   ├── product.py       ← Создать/найти/обновить товар
│   │   ├── order.py         ← Работа с корзиной и заказами
│   │   └── review.py        ← Работа с отзывами
│   │
│   ├── routers/             ← API-эндпоинты (маршруты)
│   │   ├── auth.py          ← POST /api/auth/register, /api/auth/login
│   │   ├── users.py         ← GET/PATCH /api/users/me
│   │   ├── products.py      ← GET /api/products, /api/categories
│   │   ├── cart.py          ← GET/POST/PATCH/DELETE /api/cart
│   │   ├── orders.py        ← GET/POST /api/orders
│   │   ├── reviews.py       ← GET/POST /api/reviews
│   │   ├── admin.py         ← Все /api/admin/* (только для сотрудников)
│   │   └── ai.py            ← GET /api/ai/recommendations, /api/ai/demand-forecast
│   │
│   ├── auth/
│   │   └── jwt.py           ← JWT-токены, хэширование паролей, Dependencies
│   │
│   └── ai/
│       ├── recommendations.py  ← Алгоритм рекомендаций (косинусное сходство)
│       └── demand_forecast.py  ← Прогноз спроса (взвешенное среднее)
│
├── alembic/                 ← Миграции базы данных
│   ├── env.py               ← Настройки Alembic
│   └── versions/            ← Файлы миграций (генерируются автоматически)
│
├── alembic.ini              ← Конфигурация Alembic
├── requirements.txt         ← Зависимости Python
├── seed_data.py             ← Скрипт заполнения БД тестовыми данными
├── docker-compose.yml       ← Docker (PostgreSQL + Backend)
├── Dockerfile               ← Сборка Docker-образа
└── .env.example             ← Пример файла настроек
```

---

## 1. Установка Python

### Windows:
1. Открой сайт https://www.python.org/downloads/
2. Нажми **Download Python 3.11.x** (или новее)
3. Запусти установщик
4. ⚠️ ВАЖНО: поставь галочку **"Add Python to PATH"** перед установкой
5. Нажми **Install Now**
6. Проверь установку — открой командную строку (Win+R → cmd) и введи:
   ```
   python --version
   ```
   Должно показать: `Python 3.11.x`

### macOS:
```bash
brew install python@3.11
```

---

## 2. Установка PostgreSQL

### Windows:
1. Открой https://www.postgresql.org/download/windows/
2. Скачай установщик (нажми **Download the installer**)
3. Запусти, во время установки:
   - **Port**: оставь `5432`
   - **Password** для superuser (пользователь `postgres`): придумай и **запомни!**
   - Всё остальное — по умолчанию
4. После установки PostgreSQL запустится автоматически

### macOS:
```bash
brew install postgresql@16
brew services start postgresql@16
```

---

## 3. Создание базы данных

### Способ 1: Через pgAdmin (графический интерфейс — рекомендуется для новичков)

1. После установки PostgreSQL найди в меню программ **pgAdmin 4** и открой его
2. В браузере откроется интерфейс pgAdmin
3. В левом дереве: нажми на **Servers → PostgreSQL → Databases**
4. Правый клик на **Databases → Create → Database...**
5. В поле **Database**: введи `toyshop_db`
6. Нажми **Save**

Теперь создадим пользователя для нашего приложения:
1. В левом дереве: **PostgreSQL → Login/Group Roles**
2. Правый клик → **Create → Login/Group Role...**
3. Вкладка **General**: Name = `toyshop_user`
4. Вкладка **Definition**: Password = `toyshop_pass`
5. Вкладка **Privileges**: включи **Can login**, **Superuser** (для простоты)
6. Нажми **Save**

### Способ 2: Через командную строку

Открой командную строку (или PowerShell на Windows, Terminal на macOS):

```bash
# Подключаемся к PostgreSQL от имени суперпользователя
psql -U postgres

# Внутри psql выполняем:
CREATE USER toyshop_user WITH PASSWORD 'toyshop_pass';
CREATE DATABASE toyshop_db OWNER toyshop_user;
GRANT ALL PRIVILEGES ON DATABASE toyshop_db TO toyshop_user;

# Выход из psql
\q
```

---

## 4. Открытие в PyCharm

1. Скачай **PyCharm Community Edition** (бесплатная): https://www.jetbrains.com/pycharm/download/
2. Запусти PyCharm → **Open**
3. Выбери папку `backend` (нашего проекта)
4. PyCharm предложит создать виртуальное окружение — соглашайся!

### Создать виртуальное окружение вручную:
```bash
# Перейди в папку backend
cd backend

# Создай виртуальное окружение
python -m venv venv

# Активируй его:
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Должна появиться надпись (venv) в начале строки
```

В PyCharm: **File → Settings → Project → Python Interpreter → Add Interpreter → Existing → выбери `venv/bin/python`**

---

## 5. Установка зависимостей

В терминале (с активированным venv):

```bash
pip install -r requirements.txt
```

Это установит:
- **fastapi** — веб-фреймворк
- **uvicorn** — ASGI-сервер (запускает FastAPI)
- **sqlalchemy** — ORM для работы с PostgreSQL
- **alembic** — миграции базы данных
- **pydantic** — валидация данных
- **python-jose** — JWT-токены
- **passlib** — хэширование паролей
- **scikit-learn, numpy, pandas** — AI-модуль
- И другие...

---

## 6. Настройка .env файла

1. Скопируй файл `.env.example` и переименуй копию в `.env`:
   ```bash
   # Windows:
   copy .env.example .env
   # macOS/Linux:
   cp .env.example .env
   ```

2. Открой `.env` в редакторе и проверь настройки:
   ```env
   DATABASE_URL=postgresql://toyshop_user:toyshop_pass@localhost:5432/toyshop_db
   SECRET_KEY=your-super-secret-key-change-this-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=60
   UPLOAD_DIR=uploads
   DEBUG=True
   ```

   Если ты использовал другой пароль при создании пользователя — измени `toyshop_pass` на свой.

---

## 7. Запуск миграций Alembic

Миграции — это способ создать таблицы в базе данных.

```bash
# Находясь в папке backend с активным venv:

# Шаг 1: Создать первую миграцию (Alembic сам посмотрит на модели)
alembic revision --autogenerate -m "initial_tables"

# Шаг 2: Применить миграцию (создать таблицы в БД)
alembic upgrade head
```

После этого в базе данных `toyshop_db` появятся все таблицы!

Проверить в pgAdmin: **toyshop_db → Schemas → public → Tables**

---

## 8. Заполнение тестовыми данными

```bash
python seed_data.py
```

Это создаст:
- 5 тестовых пользователей
- 8 категорий и 15 подкатегорий
- 13 товаров
- 5 ПВЗ

### Тестовые аккаунты:
| Email | Пароль | Роль |
|---|---|---|
| admin@toyshop.ru | admin123 | Администратор |
| operator@toyshop.ru | operator123 | Оператор |
| manager@toyshop.ru | manager123 | Менеджер |
| user@example.com | user123 | Покупатель |
| test@example.com | test123 | Покупатель |

---

## 9. Запуск сервера

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- `app.main:app` — путь к объекту FastAPI (файл `app/main.py`, переменная `app`)
- `--reload` — автоматически перезапускать при изменении кода (только для разработки)
- `--port 8000` — порт сервера

В терминале появится:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Application startup complete.
```

🎉 Сервер запущен! Открой браузер: **http://localhost:8000**

---

## 10. Проверка API через Swagger

Swagger — это автоматическая документация и тест-среда для API.

1. Открой: **http://localhost:8000/docs**
2. Ты увидишь список всех эндпоинтов

### Как протестировать:

#### Шаг 1: Регистрация
1. Найди `POST /api/auth/register` → нажми **Try it out**
2. Введи в поле:
   ```json
   {
     "email": "mytest@mail.ru",
     "password": "mypassword123",
     "first_name": "Иван"
   }
   ```
3. Нажми **Execute**
4. Должен ответить `201 Created` с данными пользователя

#### Шаг 2: Логин (получить токен)
1. Найди `POST /api/auth/login`
2. Введи:
   ```json
   {
     "email": "admin@toyshop.ru",
     "password": "admin123"
   }
   ```
3. В ответе получишь токен: `{"access_token": "eyJhbGci..."}`

#### Шаг 3: Авторизация в Swagger
1. Нажми кнопку **Authorize** 🔐 (вверху страницы)
2. Введи токен в формате: `Bearer eyJhbGci...`
3. Нажми **Authorize**

Теперь все запросы будут авторизованы!

#### Шаг 4: Просмотр каталога
- `GET /api/products` → список товаров
- `GET /api/products?q=кукла` → поиск
- `GET /api/products?category_slug=kukly` → фильтр по категории
- `GET /api/products/featured` → товары для главной страницы

#### Шаг 5: Корзина
- `POST /api/cart/items` с `{"product_id": 1, "quantity": 2}`
- `GET /api/cart` → просмотр корзины
- `POST /api/orders` → оформить заказ

---

## ER-диаграмма

```
users
├── id (PK)
├── email (UNIQUE)
├── phone (UNIQUE, nullable)
├── first_name, last_name
├── hashed_password
├── role (customer/operator/manager/admin)
├── address
├── is_active
└── created_at, updated_at

categories
├── id (PK)
├── name, slug (UNIQUE)
├── description, image
├── parent_id (FK → categories.id, nullable — для подкатегорий)
└── is_active, created_at

products
├── id (PK)
├── name, description
├── category_id (FK → categories.id)
├── price (Decimal)
├── stock
├── image
├── status (active/inactive/out_of_stock)
├── age_from, age_to
├── brand
├── is_bestseller
├── discount_percent
└── created_at, updated_at

product_characteristics (ONE-TO-ONE с products)
├── id (PK)
├── product_id (FK → products.id, UNIQUE)
├── sku, color, material
├── height, length, width, weight
└── country

pickup_points
├── id (PK)
├── name, address, city
├── working_hours, phone
└── is_active, created_at

carts (ONE-TO-ONE с users)
├── id (PK)
├── user_id (FK → users.id, UNIQUE)
└── created_at, updated_at

cart_items
├── id (PK)
├── cart_id (FK → carts.id)
├── product_id (FK → products.id)
├── quantity
└── added_at

orders
├── id (PK)
├── user_id (FK → users.id)
├── status (new/processing/shipped/delivered/cancelled)
├── payment_method (cash/card/online)
├── pickup_point_id (FK → pickup_points.id, nullable)
├── delivery_address (nullable)
├── comment, operator_note
├── total_price
└── created_at, updated_at

order_items
├── id (PK)
├── order_id (FK → orders.id)
├── product_id (FK → products.id, nullable — товар могли удалить)
├── product_name (сохраняем на момент заказа!)
├── quantity
└── price (сохраняем на момент заказа!)

reviews
├── id (PK)
├── user_id (FK → users.id)
├── product_id (FK → products.id)
├── order_id (FK → orders.id, nullable)
├── rating (1-5)
├── pros, cons, text
├── status (pending/approved/rejected)
└── moderator_comment, created_at
```

---

## Частые ошибки и их решение

### ❌ `ModuleNotFoundError: No module named 'fastapi'`
**Причина**: зависимости не установлены или venv не активирован.
```bash
# Активируй venv:
venv\Scripts\activate    # Windows
source venv/bin/activate # macOS/Linux

# Установи зависимости:
pip install -r requirements.txt
```

### ❌ `sqlalchemy.exc.OperationalError: could not connect to server`
**Причина**: PostgreSQL не запущен или неверные данные подключения.
- Проверь что PostgreSQL запущен (Services на Windows или `brew services` на Mac)
- Проверь `.env` файл: правильный ли пароль, имя БД

### ❌ `alembic: command not found`
**Причина**: alembic не установлен или venv не активирован.
```bash
pip install alembic
```

### ❌ `ModuleNotFoundError` при запуске alembic
**Причина**: alembic запускается не из папки backend.
```bash
# Убедись что ты в папке backend:
cd backend
alembic upgrade head
```

### ❌ `422 Unprocessable Entity` в Swagger
**Причина**: неверный формат данных в запросе.
- Посмотри на схему запроса в Swagger (секция **Request body**)
- Проверь что все обязательные поля заполнены

---

## Запуск через Docker (альтернативный способ)

Если установлен Docker Desktop:

```bash
# В папке backend:
docker-compose up -d

# Посмотреть логи:
docker-compose logs -f backend

# Остановить:
docker-compose down
```

Docker сам:
- Запустит PostgreSQL
- Создаст таблицы (alembic upgrade head)
- Заполнит тестовыми данными (seed_data.py)
- Запустит сервер

Документация: http://localhost:8000/docs
