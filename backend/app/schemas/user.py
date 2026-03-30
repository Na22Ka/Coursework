"""
schemas/user.py — Pydantic-схемы для пользователей.

Чем отличаются схемы от моделей?

  SQLAlchemy-модель (models/user.py) — описывает ТАБЛИЦУ в базе данных.
  Pydantic-схема  (schemas/user.py) — описывает ДАННЫЕ в запросах/ответах API.

Например:
  - При регистрации клиент отправляет: {"email": "...", "password": "..."}
    → это описывает схема UserCreate
  - Сервер отвечает: {"id": 1, "email": "...", "role": "customer"}
    → это описывает схема UserResponse
  
  Пароль есть в UserCreate (приходит от клиента),
  но НЕТ в UserResponse (не отправляем пароль обратно!).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


# ── Базовые схемы ─────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    """Общие поля для всех схем пользователя."""
    email:      EmailStr       = Field(..., description="Электронная почта")
    first_name: Optional[str]  = Field(None, max_length=100, description="Имя")
    last_name:  Optional[str]  = Field(None, max_length=100, description="Фамилия")
    phone:      Optional[str]  = Field(None, max_length=20,  description="Телефон")
    address:    Optional[str]  = Field(None, description="Адрес доставки")


# ── Схемы запросов (то, что приходит от клиента) ──────────────────────────────

class UserCreate(UserBase):
    """
    Данные для регистрации нового пользователя.
    POST /auth/register → принимает эту схему.
    """
    password: str = Field(..., min_length=6, description="Пароль (минимум 6 символов)")


class UserUpdate(BaseModel):
    """
    Данные для обновления профиля.
    PATCH /users/me → принимает эту схему.
    Все поля необязательны (Optional) — обновляем только то, что прислали.
    """
    first_name: Optional[str] = Field(None, max_length=100)
    last_name:  Optional[str] = Field(None, max_length=100)
    phone:      Optional[str] = Field(None, max_length=20)
    address:    Optional[str] = None
    password:   Optional[str] = Field(None, min_length=6)


class UserAdminUpdate(UserUpdate):
    """Обновление пользователя администратором (можно менять роль)."""
    role:      Optional[UserRole] = None
    is_active: Optional[bool]     = None


# ── Схемы ответов (то, что сервер возвращает клиенту) ─────────────────────────

class UserResponse(UserBase):
    """
    Данные пользователя в ответе API.
    Заметь: здесь НЕТ поля password — никогда не отправляем пароль!
    """
    id:         int
    role:       UserRole
    is_active:  bool
    created_at: datetime

    class Config:
        # from_orm=True позволяет создавать схему из SQLAlchemy-объекта:
        # UserResponse.from_orm(user_from_db)
        from_attributes = True


class UserShort(BaseModel):
    """Краткая информация о пользователе (для отображения в заказах и т.д.)."""
    id:    int
    email: str
    full_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Схемы для JWT-токена ───────────────────────────────────────────────────────

class Token(BaseModel):
    """Ответ на успешный логин — JWT-токен."""
    access_token: str
    token_type:   str = "bearer"


class TokenData(BaseModel):
    """Данные, закодированные внутри JWT-токена."""
    user_id: Optional[int] = None


# ── Схема для логина ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Данные для входа в систему."""
    email:    EmailStr
    password: str
