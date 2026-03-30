"""
models/review.py — модель отзывов о товарах.

Отзыв привязан к заказу (только купившие могут оставлять отзывы).
Перед публикацией проходит модерацию.
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class ReviewStatus(str, enum.Enum):
    """Статус отзыва."""
    pending  = "pending"   # Ожидает модерации
    approved = "approved"  # Опубликован
    rejected = "rejected"  # Отклонён модератором


class Review(Base):
    """
    Таблица reviews — отзывы покупателей о товарах.
    
    Правила:
    - Отзыв можно оставить только на купленный товар
    - Один отзыв на один заказ
    - Новые отзывы имеют статус "pending" (ожидают модерации)
    - Только после одобрения администратором отзыв виден всем
    """
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)

    # Автор отзыва
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Товар, на который написан отзыв
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)

    # Заказ, к которому привязан отзыв
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)

    # Оценка от 1 до 5 звёзд
    rating = Column(SmallInteger, nullable=False)  # 1-5

    # Достоинства (необязательно)
    pros = Column(Text, nullable=True)

    # Недостатки (необязательно)
    cons = Column(Text, nullable=True)

    # Основной текст отзыва
    text = Column(Text, nullable=True)

    # Статус модерации
    status = Column(Enum(ReviewStatus), default=ReviewStatus.pending, nullable=False)

    # Комментарий модератора при отклонении
    moderator_comment = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    user    = relationship("User",    back_populates="reviews")
    product = relationship("Product", back_populates="reviews")
    order   = relationship("Order",   back_populates="reviews")

    def __repr__(self):
        return f"<Review id={self.id} product_id={self.product_id} rating={self.rating}>"
