"""
schemas/order.py — Pydantic-схемы для корзины и заказов.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.order import OrderStatus, PaymentMethod
from app.schemas.product import ProductShort


# ── ПВЗ ───────────────────────────────────────────────────────────────────────

class PickupPointBase(BaseModel):
    name:          str
    address:       str
    city:          str
    working_hours: Optional[str] = None
    phone:         Optional[str] = None
    is_active:     bool          = True


class PickupPointCreate(PickupPointBase):
    pass


class PickupPointResponse(PickupPointBase):
    id:         int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Корзина ───────────────────────────────────────────────────────────────────

class CartItemResponse(BaseModel):
    """Одна позиция в корзине."""
    id:          int
    product:     ProductShort
    quantity:    int
    total_price: float

    class Config:
        from_attributes = True


class CartResponse(BaseModel):
    """Полная корзина пользователя."""
    id:          int
    items:       List[CartItemResponse]
    total_price: float
    total_items: int

    class Config:
        from_attributes = True


class AddToCartRequest(BaseModel):
    """Запрос на добавление товара в корзину."""
    product_id: int  = Field(..., description="ID товара")
    quantity:   int  = Field(1, ge=1, description="Количество")


class UpdateCartItemRequest(BaseModel):
    """Запрос на изменение количества в корзине."""
    quantity: int = Field(..., ge=0, description="Новое количество (0 = удалить)")


# ── Заказы ────────────────────────────────────────────────────────────────────

class OrderItemResponse(BaseModel):
    """Одна позиция в заказе."""
    id:           int
    product_id:   Optional[int]
    product_name: str
    quantity:     int
    price:        float
    total_price:  float
    product:      Optional[ProductShort] = None

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    """Данные для оформления заказа."""
    payment_method:   PaymentMethod = PaymentMethod.card
    pickup_point_id:  Optional[int] = Field(None, description="ID пункта выдачи")
    delivery_address: Optional[str] = Field(None, description="Адрес доставки (если нет ПВЗ)")
    comment:          Optional[str] = None


class OrderStatusUpdate(BaseModel):
    """Обновление статуса заказа (для операторов)."""
    status:         OrderStatus
    operator_note:  Optional[str] = None


class OrderResponse(BaseModel):
    """Полная информация о заказе."""
    id:               int
    user_id:          int
    status:           OrderStatus
    payment_method:   PaymentMethod
    pickup_point_id:  Optional[int]
    delivery_address: Optional[str]
    comment:          Optional[str]
    total_price:      float
    operator_note:    Optional[str]
    created_at:       datetime
    updated_at:       datetime
    items:            List[OrderItemResponse]
    pickup_point:     Optional[PickupPointResponse] = None
    can_be_cancelled: bool                          = False

    class Config:
        from_attributes = True


class OrderShort(BaseModel):
    """Краткая информация о заказе (для списка заказов)."""
    id:          int
    status:      OrderStatus
    total_price: float
    created_at:  datetime
    items_count: int = 0

    class Config:
        from_attributes = True
