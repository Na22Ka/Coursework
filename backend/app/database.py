"""
database.py — подключение к базе данных PostgreSQL через SQLAlchemy.

SQLAlchemy — это ORM (Object-Relational Mapping).
ORM позволяет работать с таблицами базы данных как с обычными Python-классами,
без написания SQL-запросов вручную.

Схема работы:
  1. engine — "движок", знает как подключиться к PostgreSQL
  2. SessionLocal — фабрика сессий (сессия = одно соединение с БД)
  3. Base — базовый класс для всех наших моделей (таблиц)
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Создаём "движок" — он управляет пулом соединений с БД
# pool_pre_ping=True — проверяет, живо ли соединение перед использованием
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,  # echo=True выводит SQL-запросы в консоль (удобно при разработке)
)

# SessionLocal — это фабрика сессий.
# Каждый раз, когда нам нужно обратиться к БД, мы создаём новую сессию.
# autocommit=False — изменения не сохраняются автоматически (нужно явно вызвать commit)
# autoflush=False — данные не отправляются в БД до commit
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base — родительский класс для всех моделей (таблиц).
# Каждый класс, который наследует Base, становится таблицей в БД.
Base = declarative_base()


def get_db():
    """
    Генератор сессий базы данных.
    
    Используется как зависимость (Dependency) в FastAPI.
    FastAPI автоматически вызывает эту функцию перед каждым запросом
    и передаёт сессию в роутер.
    
    Конструкция try/finally гарантирует, что сессия будет закрыта
    даже если произошла ошибка.
    
    Пример использования в роутере:
        @router.get("/products")
        def get_products(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
