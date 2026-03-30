"""
routers/auth.py — регистрация и логин.

Эндпоинты:
  POST /api/auth/register  — зарегистрироваться
  POST /api/auth/login     — войти, получить JWT-токен
  GET  /api/auth/me        — получить данные текущего пользователя
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import (
    create_access_token,
    get_current_active_user,
    verify_password,
)
from app.config import settings
from app.crud import user as user_crud
from app.database import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, Token, UserCreate, UserResponse

# APIRouter — это мини-приложение с группой маршрутов.
# prefix="/auth" — все пути будут начинаться с /auth
# tags=["Auth"] — группировка в документации Swagger
router = APIRouter(prefix="/auth", tags=["🔐 Авторизация"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.
    
    Принимает:
    - email (обязательно, уникальный)
    - password (минимум 6 символов)
    - first_name, last_name, phone (необязательно)
    
    Возвращает: созданного пользователя (без пароля).
    """
    # Проверяем, что email не занят
    existing = user_crud.get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )

    # Проверяем уникальность телефона (если указан)
    if user_data.phone:
        existing_phone = user_crud.get_user_by_phone(db, user_data.phone)
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Этот номер телефона уже зарегистрирован",
            )

    # Создаём пользователя
    user = user_crud.create_user(db, user_data)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Вход в систему",
)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Вход в систему.
    
    Принимает: email + password
    
    Возвращает JWT-токен. Его нужно добавлять в заголовок каждого запроса:
      Authorization: Bearer <токен>
    
    Токен действителен 60 минут (настраивается в .env).
    """
    # Ищем пользователя по email
    user = user_crud.get_user_by_email(db, login_data.email)

    # Проверяем пароль
    # Намеренно одно сообщение об ошибке — не даём угадать, что именно неверно
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверяем, активен ли аккаунт
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован. Обратитесь в поддержку.",
        )

    # Создаём JWT-токен
    # В токене записываем user_id ("sub" = subject — стандартное поле JWT)
    token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return {"access_token": token, "token_type": "bearer"}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Данные текущего пользователя",
)
def get_me(current_user: User = Depends(get_current_active_user)):
    """
    Возвращает данные авторизованного пользователя.
    
    Требует заголовок: Authorization: Bearer <токен>
    """
    return current_user
