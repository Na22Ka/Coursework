"""
routers/cart.py — корзина покупателя.

Все эндпоинты требуют авторизации (JWT-токен).

Эндпоинты:
  GET    /api/cart             — просмотр корзины
  POST   /api/cart/items       — добавить товар
  PATCH  /api/cart/items/{id}  — изменить количество
  DELETE /api/cart/items/{id}  — удалить позицию
  DELETE /api/cart             — очистить корзину
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_active_user
from app.crud import order as order_crud
from app.database import get_db
from app.models.user import User
from app.schemas.order import AddToCartRequest, CartResponse, UpdateCartItemRequest

router = APIRouter(prefix="/cart", tags=["🛒 Корзина"])


@router.get(
    "",
    response_model=CartResponse,
    summary="Просмотр корзины",
)
def get_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Возвращает текущую корзину авторизованного пользователя."""
    cart = order_crud.get_or_create_cart(db, current_user.id)
    return cart


@router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить товар в корзину",
)
def add_to_cart(
    data: AddToCartRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Добавить товар в корзину.
    
    Если товар уже в корзине — увеличивает количество.
    """
    try:
        cart = order_crud.add_item_to_cart(db, current_user.id, data)
        return cart
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/items/{item_id}",
    response_model=CartResponse,
    summary="Изменить количество товара",
)
def update_cart_item(
    item_id: int,
    data: UpdateCartItemRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Изменить количество товара в корзине.
    quantity = 0 → удалить товар из корзины.
    """
    try:
        cart = order_crud.update_cart_item(db, current_user.id, item_id, data.quantity)
        return cart
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/items/{item_id}",
    response_model=CartResponse,
    summary="Удалить позицию из корзины",
)
def remove_from_cart(
    item_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Удалить один товар из корзины."""
    cart = order_crud.remove_cart_item(db, current_user.id, item_id)
    return cart


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Очистить корзину",
)
def clear_cart(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Удалить все товары из корзины."""
    order_crud.clear_cart(db, current_user.id)
