"""
models/order.py — модели корзины, заказов и ПВЗ (пунктов выдачи заказов).

Таблицы:
  pickup_points — пункты выдачи заказов
  carts         — корзины пользователей (одна корзина = один пользователь)
  cart_items    — позиции в корзине
  orders        — оформленные заказы
  order_items   — позиции в заказе
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, String, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class OrderStatus(str, enum.Enum):
    """Статусы заказа."""
    new        = "new"        # Новый (только оформлен)
    processing = "processing" # В обработке (сборка)
    shipped    = "shipped"    # Отправлен в ПВЗ
    delivered  = "delivered"  # Получен покупателем
    cancelled  = "cancelled"  # Отменён


class PaymentMethod(str, enum.Enum):
    """Способы оплаты."""
    cash   = "cash"    # Наличными при получении
    card   = "card"    # Банковская карта
    online = "online"  # Онлайн-оплата


class PickupPoint(Base):
    """
    Таблица pickup_points — пункты выдачи заказов (ПВЗ).
    """
    __tablename__ = "pickup_points"

    id = Column(Integer, primary_key=True, index=True)

    # Название ПВЗ
    name = Column(String(200), nullable=False)

    # Полный адрес
    address = Column(Text, nullable=False)

    # Город
    city = Column(String(100), nullable=False)

    # Режим работы (например: "Пн-Пт 9:00-20:00")
    working_hours = Column(String(200), nullable=True)

    # Телефон ПВЗ
    phone = Column(String(20), nullable=True)

    # Активен ли ПВЗ
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    orders = relationship("Order", back_populates="pickup_point")

    def __repr__(self):
        return f"<PickupPoint id={self.id} address={self.address}>"


class Cart(Base):
    """
    Таблица carts — корзина пользователя.
    
    У каждого пользователя ОДНА корзина (связь один-к-одному с users).
    В корзине хранятся товары до оформления заказа.
    """
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)

    # Владелец корзины (внешний ключ → users.id)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    user  = relationship("User",     back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items)

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items)


class CartItem(Base):
    """
    Таблица cart_items — одна позиция в корзине.
    
    Например: "Кукла Барби × 2"
    """
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)

    # Корзина, в которой находится эта позиция
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"))

    # Товар
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"))

    # Количество
    quantity = Column(Integer, default=1)

    added_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    cart    = relationship("Cart",    back_populates="items")
    product = relationship("Product", back_populates="cart_items")

    @property
    def total_price(self):
        if self.product:
            return float(self.product.price) * self.quantity
        return 0.0


class Order(Base):
    """
    Таблица orders — оформленные заказы.
    
    Когда покупатель нажимает "Оформить заказ":
    1. Из корзины создаются OrderItem
    2. Создаётся Order с итоговой суммой
    3. Корзина очищается
    """
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # Покупатель
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Статус заказа
    status = Column(Enum(OrderStatus), default=OrderStatus.new, nullable=False)

    # Способ оплаты
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.card)

    # ПВЗ для получения заказа (NULL = доставка на адрес)
    pickup_point_id = Column(Integer, ForeignKey("pickup_points.id"), nullable=True)

    # Адрес доставки (если нет ПВЗ)
    delivery_address = Column(Text, nullable=True)

    # Комментарий покупателя к заказу
    comment = Column(Text, nullable=True)

    # Итоговая сумма
    total_price = Column(Numeric(12, 2), default=0)

    # Заметка оператора (видна только сотрудникам)
    operator_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    user         = relationship("User",        back_populates="orders")
    pickup_point = relationship("PickupPoint", back_populates="orders")
    items        = relationship("OrderItem",   back_populates="order", cascade="all, delete-orphan")
    reviews      = relationship("Review",      back_populates="order")

    def __repr__(self):
        return f"<Order id={self.id} user_id={self.user_id} status={self.status}>"

    @property
    def can_be_cancelled(self):
        """Можно ли отменить заказ (только на ранних этапах)."""
        return self.status in (OrderStatus.new, OrderStatus.processing)


class OrderItem(Base):
    """
    Таблица order_items — позиции в заказе.
    
    Важно! Мы сохраняем название товара и цену НА МОМЕНТ ЗАКАЗА.
    Это нужно, чтобы история заказов не менялась при изменении цен.
    """
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)

    # Заказ
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))

    # Товар (может стать NULL если товар удалят из каталога)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)

    # Название товара на момент заказа (сохраняем отдельно!)
    product_name = Column(String(200), nullable=False)

    # Количество
    quantity = Column(Integer, nullable=False)

    # Цена за единицу на момент заказа
    price = Column(Numeric(10, 2), nullable=False)

    # Связи
    order   = relationship("Order",   back_populates="items")
    product = relationship("Product", back_populates="order_items")

    @property
    def total_price(self):
        return float(self.price) * self.quantity
