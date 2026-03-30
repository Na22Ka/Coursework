"""
routers/reviews.py — отзывы о товарах.

Эндпоинты:
  GET  /api/products/{id}/reviews — отзывы о товаре
  POST /api/reviews               — написать отзыв
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt import get_current_active_user
from app.crud import review as review_crud
from app.crud import product as product_crud
from app.database import get_db
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewResponse

router = APIRouter(tags=["⭐ Отзывы"])


@router.get(
    "/products/{product_id}/reviews",
    response_model=List[ReviewResponse],
    summary="Отзывы о товаре",
)
def get_product_reviews(product_id: int, db: Session = Depends(get_db)):
    """Список одобренных отзывов для конкретного товара."""
    product = product_crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    reviews = review_crud.get_reviews_for_product(db, product_id, approved_only=True)
    # Добавляем имя автора
    result = []
    for review in reviews:
        r = ReviewResponse.model_validate(review)
        r.author_name = review.user.full_name if review.user else "Аноним"
        result.append(r)
    return result


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Написать отзыв",
)
def create_review(
    data: ReviewCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Написать отзыв о товаре.
    
    Отзыв попадает на модерацию (статус 'pending').
    После проверки администратором — публикуется.
    
    rating: от 1 до 5 звёзд (обязательно)
    pros, cons, text — необязательны
    """
    # Проверяем, что товар существует
    product = product_crud.get_product_by_id(db, data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    review = review_crud.create_review(db, current_user.id, data)
    r = ReviewResponse.model_validate(review)
    r.author_name = current_user.full_name
    return r
