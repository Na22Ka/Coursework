"""
routers/admin.py — административные эндпоинты.

Все эндпоинты требуют роль admin или operator (get_current_staff).

Эндпоинты:
  PRODUCTS:
    POST   /api/admin/products           — создать товар
    PATCH  /api/admin/products/{id}      — редактировать
    DELETE /api/admin/products/{id}      — удалить
    POST   /api/admin/products/{id}/image — загрузить изображение

  CATEGORIES:
    POST   /api/admin/categories         — создать категорию
    PATCH  /api/admin/categories/{id}    — редактировать

  ORDERS:
    GET    /api/admin/orders             — все заказы
    PATCH  /api/admin/orders/{id}/status — изменить статус

  REVIEWS:
    GET    /api/admin/reviews            — все отзывы (для модерации)
    PATCH  /api/admin/reviews/{id}/moderate — одобрить/отклонить

  USERS:
    GET    /api/admin/users              — список пользователей
    PATCH  /api/admin/users/{id}         — редактировать пользователя
"""
import os
import shutil
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_staff, get_current_admin
from app.config import settings
from app.crud import order as order_crud
from app.crud import product as product_crud
from app.crud import review as review_crud
from app.crud import user as user_crud
from app.database import get_db
from app.models.order import OrderStatus
from app.models.review import ReviewStatus
from app.models.user import User, UserRole
from app.schemas.order import OrderResponse, OrderStatusUpdate
from app.schemas.product import (
    CategoryCreate, CategoryResponse, CategoryUpdate,
    ProductCreate, ProductResponse, ProductUpdate,
)
from app.schemas.review import ReviewModerationRequest, ReviewResponse
from app.schemas.user import UserAdminUpdate, UserResponse

router = APIRouter(prefix="/admin", tags=["⚙️ Администрирование"])


# ── Товары ────────────────────────────────────────────────────────────────────

@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Создать товар",
)
def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """Создать новый товар. Требует роль admin или operator."""
    return product_crud.create_product(db, data)


@router.patch(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="[Admin] Редактировать товар",
)
def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """Обновить данные товара."""
    product = product_crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product_crud.update_product(db, product, data)


@router.delete(
    "/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Admin] Удалить товар",
)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """Удалить товар из каталога."""
    product = product_crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    product_crud.delete_product(db, product)


@router.post(
    "/products/{product_id}/image",
    response_model=ProductResponse,
    summary="[Admin] Загрузить изображение товара",
)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """
    Загрузить изображение для товара.
    
    Принимает файл формата: jpg, jpeg, png, gif, webp
    Максимальный размер: 5 МБ
    """
    product = product_crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    # Проверяем тип файла
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Допустимые форматы: jpg, png, gif, webp")

    # Создаём папку для загрузок
    upload_dir = os.path.join(settings.UPLOAD_DIR, "products")
    os.makedirs(upload_dir, exist_ok=True)

    # Генерируем имя файла
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"product_{product_id}.{ext}"
    filepath = os.path.join(upload_dir, filename)

    # Сохраняем файл
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Обновляем путь в БД
    from app.schemas.product import ProductUpdate
    product = product_crud.update_product(db, product, ProductUpdate(), image_path=filepath)
    return product


# ── Категории ─────────────────────────────────────────────────────────────────

@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Создать категорию",
)
def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    # Проверяем уникальность slug
    existing = product_crud.get_category_by_slug(db, data.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Категория с таким slug уже существует")
    return product_crud.create_category(db, data)


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    summary="[Admin] Редактировать категорию",
)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    category = product_crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return product_crud.update_category(db, category, data)


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Admin] Удалить категорию",
)
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_admin),  # Только admin!
    db: Session = Depends(get_db),
):
    category = product_crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    product_crud.delete_category(db, category)


# ── Заказы (панель оператора) ─────────────────────────────────────────────────

@router.get(
    "/orders",
    response_model=List[OrderResponse],
    summary="[Admin] Все заказы",
)
def get_all_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """
    Список всех заказов для панели оператора.
    Можно фильтровать по статусу: new|processing|shipped|delivered|cancelled
    """
    order_status = None
    if status_filter:
        try:
            order_status = OrderStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Неверный статус: {status_filter}")

    return order_crud.get_all_orders(db, status=order_status, skip=skip, limit=limit)


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderResponse,
    summary="[Admin] Изменить статус заказа",
)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """Изменить статус заказа (оператор)."""
    order = order_crud.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order_crud.update_order_status(db, order, data)


# ── Отзывы (модерация) ────────────────────────────────────────────────────────

@router.get(
    "/reviews",
    response_model=List[ReviewResponse],
    summary="[Admin] Все отзывы (для модерации)",
)
def get_all_reviews(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0),
    limit: int = Query(50),
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """Список всех отзывов с фильтром по статусу: pending|approved|rejected."""
    review_status = None
    if status_filter:
        try:
            review_status = ReviewStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Неверный статус: {status_filter}")
    return review_crud.get_all_reviews(db, status=review_status, skip=skip, limit=limit)


@router.patch(
    "/reviews/{review_id}/moderate",
    response_model=ReviewResponse,
    summary="[Admin] Одобрить/отклонить отзыв",
)
def moderate_review(
    review_id: int,
    data: ReviewModerationRequest,
    current_user: User = Depends(get_current_staff),
    db: Session = Depends(get_db),
):
    """
    Модерация отзыва.
    status = 'approved' → отзыв появится на сайте
    status = 'rejected' → отзыв скрыт (можно указать причину в moderator_comment)
    """
    review = review_crud.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    return review_crud.moderate_review(db, review, data)


# ── Пользователи ──────────────────────────────────────────────────────────────

@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="[Admin] Список пользователей",
)
def get_users(
    role_filter: Optional[str] = Query(None, alias="role"),
    skip: int = Query(0),
    limit: int = Query(100),
    current_user: User = Depends(get_current_admin),  # Только admin!
    db: Session = Depends(get_db),
):
    """Список всех пользователей. Только для администраторов."""
    user_role = None
    if role_filter:
        try:
            user_role = UserRole(role_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Неверная роль: {role_filter}")
    return user_crud.get_users(db, skip=skip, limit=limit, role=user_role)


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="[Admin] Редактировать пользователя",
)
def update_user(
    user_id: int,
    data: UserAdminUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Обновить данные пользователя (включая роль и блокировку)."""
    user = user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return user_crud.update_user_by_admin(db, user, data)
