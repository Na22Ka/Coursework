"""
crud/review.py — операции с отзывами.
"""
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.review import Review, ReviewStatus
from app.schemas.review import ReviewCreate, ReviewModerationRequest


def get_reviews_for_product(
    db: Session,
    product_id: int,
    approved_only: bool = True
) -> List[Review]:
    """Отзывы для конкретного товара."""
    query = db.query(Review).filter(Review.product_id == product_id)
    if approved_only:
        query = query.filter(Review.status == ReviewStatus.approved)
    return query.order_by(Review.created_at.desc()).all()


def get_all_reviews(
    db: Session,
    status: Optional[ReviewStatus] = None,
    skip: int = 0,
    limit: int = 50
) -> List[Review]:
    """Все отзывы (для администратора)."""
    query = db.query(Review)
    if status:
        query = query.filter(Review.status == status)
    return query.order_by(Review.created_at.desc()).offset(skip).limit(limit).all()


def get_review_by_id(db: Session, review_id: int) -> Optional[Review]:
    return db.query(Review).filter(Review.id == review_id).first()


def create_review(db: Session, user_id: int, data: ReviewCreate) -> Review:
    """Создать новый отзыв (статус: pending — ожидает модерации)."""
    review = Review(
        user_id=user_id,
        product_id=data.product_id,
        order_id=data.order_id,
        rating=data.rating,
        pros=data.pros,
        cons=data.cons,
        text=data.text,
        status=ReviewStatus.pending,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def moderate_review(db: Session, review: Review, data: ReviewModerationRequest) -> Review:
    """Одобрить или отклонить отзыв."""
    review.status = data.status
    review.moderator_comment = data.moderator_comment
    db.commit()
    db.refresh(review)
    return review
