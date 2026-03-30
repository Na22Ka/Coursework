"""
auth/jwt.py — всё что связано с JWT-токенами и авторизацией.

JWT (JSON Web Token) — это зашифрованный токен, который содержит
информацию о пользователе. Сервер выдаёт его при логине, клиент
хранит его и отправляет в каждом запросе в заголовке Authorization.

Как это работает:
  1. Клиент → POST /auth/login с email+password
  2. Сервер проверяет пароль, создаёт JWT-токен, отправляет клиенту
  3. Клиент сохраняет токен (localStorage или cookies)
  4. Клиент → GET /orders (с заголовком: Authorization: Bearer <токен>)
  5. Сервер декодирует токен, находит пользователя, выполняет запрос

Структура JWT:
  header.payload.signature
  - header: алгоритм шифрования
  - payload: данные (user_id, роль, срок действия)
  - signature: подпись (никто не может подделать без секретного ключа)
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User, UserRole

# ── Хэширование паролей ───────────────────────────────────────────────────────
# CryptContext умеет хэшировать и проверять пароли
# bcrypt — надёжный алгоритм хэширования (медленный специально, чтобы брутфорс был сложнее)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── OAuth2 схема ─────────────────────────────────────────────────────────────
# Указываем путь к эндпоинту логина
# FastAPI автоматически добавит кнопку "Authorize" в Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    """
    Превращает открытый пароль в bcrypt-хэш.
    
    Пример:
        hash_password("mypassword123")
        → "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"
    
    Хэш никогда нельзя "расшифровать" обратно в пароль.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли открытый пароль хэшу.
    
    Пример:
        verify_password("mypassword123", "$2b$12$...") → True
        verify_password("wrongpassword", "$2b$12$...") → False
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создаёт JWT-токен с данными пользователя.
    
    Параметры:
        data: словарь с данными для вставки в токен (обычно {"sub": str(user_id)})
        expires_delta: через сколько токен устаревает
    
    Возвращает: строку вида "eyJhbGci..."
    """
    to_encode = data.copy()

    # Устанавливаем срок действия токена
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    # Шифруем данные с помощью секретного ключа
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """
    Декодирует JWT-токен и возвращает данные из него.
    Возвращает None если токен невалидный или просрочен.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


# ── FastAPI Dependencies (зависимости) ────────────────────────────────────────
# Dependency — это функция, которую FastAPI вызывает автоматически перед роутером.
# Пишешь: async def get_me(current_user = Depends(get_current_user))
# FastAPI сам извлечёт токен, проверит его, найдёт пользователя и передаст.

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Зависимость: извлекает текущего пользователя из JWT-токена.
    
    Использование в роутере:
        @router.get("/me")
        def get_me(user: User = Depends(get_current_user)):
            return user
    
    Если токен невалидный — автоматически вернёт 401 Unauthorized.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Неверный токен авторизации",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Декодируем токен
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    # Извлекаем user_id из поля "sub" (subject)
    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    # Ищем пользователя в базе данных
    user = db.query(User).filter(User.id == int(user_id_str)).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Зависимость: проверяет, что пользователь не заблокирован.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт заблокирован"
        )
    return current_user


def get_current_admin(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Зависимость: проверяет, что пользователь — администратор.
    Используй для защиты admin-эндпоинтов.
    
    Пример:
        @router.delete("/products/{id}")
        def delete_product(admin: User = Depends(get_current_admin)):
            ...
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user


def get_current_staff(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Зависимость: проверяет, что пользователь — сотрудник (admin или operator).
    """
    if not current_user.is_staff():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права сотрудника"
        )
    return current_user


def get_optional_user(
    token: Optional[str] = Depends(OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Зависимость: возвращает пользователя если токен есть, None если нет.
    Используется для эндпоинтов, доступных и гостям тоже.
    """
    if token is None:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    user_id_str = payload.get("sub")
    if not user_id_str:
        return None
    return db.query(User).filter(User.id == int(user_id_str)).first()
