"""
crud/user.py — операции с пользователями в базе данных.

CRUD = Create, Read, Update, Delete (Создать, Прочитать, Обновить, Удалить).
Здесь мы НЕ пишем SQL вручную — SQLAlchemy делает это за нас.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.auth.jwt import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserAdminUpdate


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Найти пользователя по ID."""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Найти пользователя по email."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_phone(db: Session, phone: str) -> Optional[User]:
    """Найти пользователя по телефону."""
    return db.query(User).filter(User.phone == phone).first()


def get_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None
) -> List[User]:
    """Список пользователей (для админ-панели)."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.offset(skip).limit(limit).all()


def create_user(db: Session, user_data: UserCreate) -> User:
    """
    Создать нового пользователя.
    
    Важно: хэшируем пароль ПЕРЕД сохранением в БД.
    Никогда не храним пароли в открытом виде!
    """
    db_user = User(
        email=user_data.email,
        phone=user_data.phone,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        address=user_data.address,
        hashed_password=hash_password(user_data.password),
        role=UserRole.customer,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # Обновляем объект, чтобы получить id из БД
    return db_user


def update_user(db: Session, user: User, update_data: UserUpdate) -> User:
    """Обновить профиль пользователя."""
    # exclude_unset=True — обновляем только те поля, которые были переданы
    update_dict = update_data.model_dump(exclude_unset=True)

    # Если передан новый пароль — хэшируем его
    if "password" in update_dict:
        update_dict["hashed_password"] = hash_password(update_dict.pop("password"))

    for field, value in update_dict.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def update_user_by_admin(db: Session, user: User, update_data: UserAdminUpdate) -> User:
    """Обновить пользователя с правами администратора (можно менять роль)."""
    update_dict = update_data.model_dump(exclude_unset=True)

    if "password" in update_dict:
        update_dict["hashed_password"] = hash_password(update_dict.pop("password"))

    for field, value in update_dict.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    """Удалить пользователя."""
    db.delete(user)
    db.commit()
