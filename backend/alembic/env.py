"""
alembic/env.py — среда выполнения Alembic.

Alembic использует этот файл чтобы:
1. Подключиться к базе данных
2. Найти все модели (таблицы) через Base.metadata
3. Сравнить модели с реальной БД и создать миграции

КАК РАБОТАЮТ МИГРАЦИИ:
- alembic revision --autogenerate -m "init"
  → Alembic смотрит на наши модели, сравнивает с БД, генерирует файл миграции
- alembic upgrade head
  → Alembic выполняет все миграции по порядку (создаёт/изменяет таблицы)
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Подключаем наши настройки и модели
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from app.database import Base

# ВАЖНО: импортируем ВСЕ модели, чтобы Alembic их увидел
from app.models import user, product, order, review  # noqa: F401

# Конфигурация из alembic.ini
config = context.config

# Настройка логирования
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Передаём URL базы данных из нашего settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# target_metadata — метаданные всех наших моделей
# Alembic использует их для автогенерации миграций
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Миграции в "offline" режиме — генерирует SQL без подключения к БД.
    Полезно когда нет прямого доступа к БД.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Миграции в "online" режиме — подключается к БД и выполняет изменения.
    Это обычный режим работы.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
