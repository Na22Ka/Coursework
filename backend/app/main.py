"""
main.py — точка входа FastAPI-приложения.

Здесь мы:
1. Создаём приложение FastAPI
2. Подключаем все роутеры
3. Настраиваем CORS (разрешаем фронтенду обращаться к нашему API)
4. Настраиваем раздачу статических файлов (изображения)
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine

# Импортируем все роутеры
from app.routers import auth, products, cart, orders, reviews, users, admin, ai

# ── Создаём приложение ────────────────────────────────────────────────────────
app = FastAPI(
    title="🧸 ToyShop API",
    description="""
## API интернет-магазина игрушек

### Как пользоваться:
1. Нажми кнопку **Authorize** и введи JWT-токен (получи его через POST /api/auth/login)
2. Формат токена: `Bearer eyJhbGci...`

### Роли пользователей:
- **guest** — неавторизованный: может смотреть каталог
- **customer** — покупатель: корзина, заказы, отзывы  
- **operator** — оператор: управление товарами и заказами
- **manager** — менеджер: просмотр отчётов и AI-прогнозов
- **admin** — администратор: полный доступ
    """,
    version="1.0.0",
    docs_url="/docs",      # Swagger UI: http://localhost:8000/docs
    redoc_url="/redoc",    # ReDoc UI:   http://localhost:8000/redoc
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Браузер блокирует запросы с одного домена на другой.
# Нам нужно разрешить фронтенду (порт 3000/5173/8080) обращаться к API (порт 8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # React (Create React App)
        "http://localhost:5173",   # React (Vite)
        "http://localhost:8080",   # Vue.js
        "http://localhost:4200",   # Angular
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PATCH, DELETE, OPTIONS
    allow_headers=["*"],   # Authorization, Content-Type, ...
)

# ── Папка для загруженных файлов ──────────────────────────────────────────────
# Создаём папки при старте если их нет
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "products"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "categories"), exist_ok=True)

# Раздаём загруженные файлы как статику: /uploads/products/product_1.jpg
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# ── Подключаем роутеры ────────────────────────────────────────────────────────
# prefix="/api" — все URL будут начинаться с /api
# Итоговые пути: /api/auth/login, /api/products, /api/cart, ...
API_PREFIX = "/api"

app.include_router(auth.router,     prefix=API_PREFIX)
app.include_router(users.router,    prefix=API_PREFIX)
app.include_router(products.router, prefix=API_PREFIX)
app.include_router(cart.router,     prefix=API_PREFIX)
app.include_router(orders.router,   prefix=API_PREFIX)
app.include_router(reviews.router,  prefix=API_PREFIX)
app.include_router(admin.router,    prefix=API_PREFIX)
app.include_router(ai.router,       prefix=API_PREFIX)


# ── Стартовый эндпоинт ────────────────────────────────────────────────────────
@app.get("/", tags=["🏠 Главная"])
def root():
    """Проверка работоспособности сервера."""
    return {
        "message": "🧸 ToyShop API работает!",
        "docs":    "http://localhost:8000/docs",
        "version": "1.0.0",
    }


@app.get("/health", tags=["🏠 Главная"])
def health_check():
    """Health-check endpoint для Docker/мониторинга."""
    return {"status": "ok"}
