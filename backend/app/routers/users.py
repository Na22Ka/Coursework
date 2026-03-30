"""
routers/users.py — управление профилем пользователя.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_active_user
from app.crud import user as user_crud
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["👤 Пользователь"])


@router.get("/me", response_model=UserResponse, summary="Мой профиль")
def get_profile(current_user: User = Depends(get_current_active_user)):
    """Данные текущего пользователя."""
    return current_user


@router.patch("/me", response_model=UserResponse, summary="Обновить профиль")
def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Обновить данные профиля.
    Можно обновить: имя, фамилию, телефон, адрес, пароль.
    """
    updated = user_crud.update_user(db, current_user, update_data)
    return updated
