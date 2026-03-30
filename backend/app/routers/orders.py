"""
routers/orders.py — заказы пользователя.

Эндпоинты:
  GET  /api/orders/my       — мои заказы
  POST /api/orders          — оформить заказ
  GET  /api/orders/{id}     — детали заказа
  POST /api/orders/{id}/cancel — отменить заказ
  GET  /api/pickup-points   — список ПВЗ
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_active_user
from app.crud import order as order_crud
from app.database import get_db
from app.models.user import User
from app.schemas.order import (
    OrderCreate, OrderResponse, OrderShort,
    PickupPointResponse,
)

router = APIRouter(tags=["📦 Заказы"])


@router.get(
    "/pickup-points",
    response_model=List[PickupPointResponse],
    summary="Список пунктов выдачи заказов",
)
def get_pickup_points(db: Session = Depends(get_db)):
    """Список всех активных ПВЗ. Доступно без авторизации."""
    return order_crud.get_pickup_points(db)


@router.get(
    "/orders/my",
    response_model=List[OrderShort],
    summary="Мои заказы",
)
def get_my_orders(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Список всех заказов текущего пользователя."""
    orders = order_crud.get_user_orders(db, current_user.id)
    # Добавляем количество позиций
    result = []
    for order in orders:
        item_count = sum(i.quantity for i in order.items)
        result.append(OrderShort(
            id=order.id,
            status=order.status,
            total_price=float(order.total_price),
            created_at=order.created_at,
            items_count=item_count,
        ))
    return result


@router.post(
    "/orders",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Оформить заказ",
)
def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Оформить заказ из текущей корзины.
    
    Что происходит:
    1. Берём товары из корзины
    2. Создаём заказ
    3. Уменьшаем остаток на складе
    4. Очищаем корзину
    
    Нужно передать:
    - payment_method (card/cash/online)
    - pickup_point_id ИЛИ delivery_address
    - comment (необязательно)
    """
    # Проверяем, что указан хотя бы один способ получения
    if not data.pickup_point_id and not data.delivery_address:
        raise HTTPException(
            status_code=400,
            detail="Укажите пункт выдачи или адрес доставки",
        )

    # Проверяем, что ПВЗ существует (если указан)
    if data.pickup_point_id:
        point = order_crud.get_pickup_point_by_id(db, data.pickup_point_id)
        if not point or not point.is_active:
            raise HTTPException(status_code=400, detail="Пункт выдачи не найден")

    try:
        order = order_crud.create_order(db, current_user.id, data)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
    summary="Детали заказа",
)
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Полная информация о заказе.
    
    Пользователь может смотреть только свои заказы.
    Сотрудники могут смотреть любые.
    """
    order = order_crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    # Проверяем права: обычный пользователь видит только свои заказы
    if order.user_id != current_user.id and not current_user.is_staff():
        raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")

    return order


@router.post(
    "/orders/{order_id}/cancel",
    response_model=OrderResponse,
    summary="Отменить заказ",
)
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Отменить заказ.
    
    Можно отменить только заказы в статусе 'new' или 'processing'.
    После отправки (shipped/delivered) отмена невозможна.
    """
    order = order_crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    if order.user_id != current_user.id and not current_user.is_staff():
        raise HTTPException(status_code=403, detail="Нет доступа к этому заказу")

    try:
        order = order_crud.cancel_order(db, order)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
