"""
schemas/review.py — Pydantic-схемы для отзывов.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.review import ReviewStatus


class ReviewCreate(BaseModel):
    """Создание нового отзыва."""
    product_id: int
    order_id:   Optional[int] = None
    rating:     int           = Field(..., ge=1, le=5, description="Оценка от 1 до 5")
    pros:       Optional[str] = Field(None, description="Достоинства")
    cons:       Optional[str] = Field(None, description="Недостатки")
    text:       Optional[str] = Field(None, description="Текст отзыва")


class ReviewModerationRequest(BaseModel):
    """Модерация отзыва (для администратора)."""
    status:            ReviewStatus
    moderator_comment: Optional[str] = None


class ReviewResponse(BaseModel):
    """Отзыв в ответе API."""
    id:                int
    user_id:           int
    product_id:        int
    order_id:          Optional[int]
    rating:            int
    pros:              Optional[str]
    cons:              Optional[str]
    text:              Optional[str]
    status:            ReviewStatus
    moderator_comment: Optional[str]
    created_at:        datetime
    author_name:       Optional[str] = None  # Имя автора (заполняется в роутере)

    class Config:
        from_attributes = True
