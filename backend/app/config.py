"""
config.py — настройки приложения.

Pydantic-Settings автоматически читает переменные из файла .env
и превращает их в удобные Python-объекты.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # URL подключения к базе данных
    DATABASE_URL: str = "postgresql://toyshop_user:toyshop_pass@localhost:5432/toyshop_db"

    # Секретный ключ для JWT-токенов (должен быть длинным и случайным!)
    SECRET_KEY: str = "change-this-secret-key-in-production"

    # Алгоритм шифрования JWT
    ALGORITHM: str = "HS256"

    # Время жизни токена (в минутах)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Папка для хранения загруженных изображений
    UPLOAD_DIR: str = "uploads"

    # Режим отладки
    DEBUG: bool = True

    class Config:
        # Читаем настройки из файла .env
        env_file = ".env"
        env_file_encoding = "utf-8"


# Создаём единственный экземпляр настроек — будем импортировать его везде
settings = Settings()
