"""
routers/ai.py — AI-эндпоинты.

Эндпоинты:
  GET /api/ai/recommendations/{product_id}  — рекомендации для товара
  GET /api/ai/demand-forecast               — прогноз спроса (только для admin/manager)
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai.demand_forecast import forecast_next_month
from app.ai.recommendations import get_recommendations
from app.auth.jwt import get_current_active_user
from app.crud.product import get_product_by_id
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.product import ProductShort

router = APIRouter(prefix="/ai", tags=["🤖 ИИ-модуль"])


@router.get(
    "/recommendations/{product_id}",
    response_model=List[ProductShort],
    summary="Рекомендации к товару",
)
def product_recommendations(
    product_id: int,
    n: int = 4,
    db: Session = Depends(get_db),
):
    """
    Возвращает список рекомендованных товаров для карточки товара.
    
    Алгоритм:
    - Если есть история заказов: рекомендации на основе совместных покупок
    - Если нет: похожие товары из той же категории
    
    Параметры:
    - product_id — ID товара
    - n — количество рекомендаций (по умолчанию 4)
    
    Доступно без авторизации (гости тоже видят рекомендации).
    """
    product = get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")

    recommendations = get_recommendations(db, product_id, n=n)
    return recommendations


@router.get(
    "/demand-forecast",
    summary="Прогноз спроса по категориям [Admin/Manager]",
)
def demand_forecast(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Прогноз спроса на следующий месяц по категориям товаров.
    
    Использует историю заказов из базы данных.
    
    Доступно только для ролей: admin, manager.
    
    Пример ответа:
    [
        {
            "category_name": "Куклы",
            "predicted_items": 150,
            "predicted_revenue": 45000.0,
            "trend": "up",
            "confidence": 0.8
        }
    ]
    """
    if not current_user.can_view_reports():
        raise HTTPException(
            status_code=403,
            detail="Прогноз доступен только для администраторов и менеджеров"
        )

    return forecast_next_month(db)
