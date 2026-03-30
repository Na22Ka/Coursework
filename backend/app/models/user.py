"""
models/user.py — модели пользователей.

SQLAlchemy-модели описывают таблицы в базе данных.
Каждый атрибут класса = колонка в таблице.

Таблицы:
  users — пользователи системы
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    """
    Роли пользователей в системе.
    
    guest    — гость (не авторизован, не хранится в БД)
    customer — обычный покупатель
    operator — оператор (может управлять заказами и товарами)
    manager  — менеджер (может смотреть отчёты)
    admin    — администратор (полный доступ)
    """
    customer = "customer"
    operator = "operator"
    manager  = "manager"
    admin    = "admin"


class User(Base):
    """
    Таблица users — пользователи магазина.
    
    Атрибуты соответствуют колонкам в PostgreSQL:
      id       → SERIAL PRIMARY KEY
      email    → VARCHAR(255) UNIQUE NOT NULL
      ...
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Уникальный email — используется как логин
    email = Column(String(255), unique=True, index=True, nullable=False)

    # Номер телефона (необязательный, тоже может быть логином)
    phone = Column(String(20), unique=True, nullable=True)

    # Имя и фамилия
    first_name = Column(String(100), nullable=True)
    last_name  = Column(String(100), nullable=True)

    # Хэш пароля — никогда не храним пароль в открытом виде!
    # passlib превратит "password123" в "$2b$12$..." (bcrypt-хэш)
    hashed_password = Column(String(255), nullable=False)

    # Роль пользователя (из enum UserRole выше)
    role = Column(Enum(UserRole), default=UserRole.customer, nullable=False)

    # Адрес доставки по умолчанию
    address = Column(Text, nullable=True)

    # Активен ли аккаунт (False = заблокирован)
    is_active = Column(Boolean, default=True)

    # Дата и время регистрации
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи с другими таблицами (ORM делает JOIN автоматически)
    # "orders" — список заказов этого пользователя
    orders  = relationship("Order",  back_populates="user",  lazy="dynamic")
    reviews = relationship("Review", back_populates="user",  lazy="dynamic")
    cart    = relationship("Cart",   back_populates="user",  uselist=False)

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"

    @property
    def full_name(self):
        """Полное имя пользователя."""
        parts = filter(None, [self.first_name, self.last_name])
        return " ".join(parts) or self.email

    def is_admin(self):
        return self.role == UserRole.admin

    def is_staff(self):
        """Сотрудник — может управлять товарами и заказами."""
        return self.role in (UserRole.admin, UserRole.operator)

    def can_view_reports(self):
        return self.role in (UserRole.admin, UserRole.manager)
