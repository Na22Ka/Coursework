"""
ai/demand_forecast.py — прогнозирование спроса на товары.

Алгоритм:
1. Берём историю заказов за последние N месяцев
2. Группируем по категориям и по месяцам
3. Строим простую модель линейной регрессии для каждой категории
4. Прогнозируем следующий месяц

Для маленького учебного проекта этого достаточно.
В реальных системах используют Prophet, ARIMA или нейросети.
"""
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.product import Category, Product


def get_monthly_sales_by_category(db: Session, months: int = 12) -> pd.DataFrame:
    """
    Получить историю продаж по категориям за последние N месяцев.
    
    Возвращает DataFrame с колонками:
      year, month, category_id, category_name, total_items, total_revenue
    """
    start_date = datetime.utcnow() - timedelta(days=months * 30)

    # Запрашиваем все позиции заказов за нужный период
    rows = (
        db.query(
            OrderItem.product_id,
            OrderItem.quantity,
            OrderItem.price,
            Order.created_at,
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.created_at >= start_date)
        .all()
    )

    if not rows:
        return pd.DataFrame()

    # Получаем категории для каждого товара
    product_to_category = {}
    category_names = {}

    products = db.query(Product.id, Product.category_id).all()
    for p in products:
        product_to_category[p.id] = p.category_id

    categories = db.query(Category.id, Category.name).all()
    for c in categories:
        category_names[c.id] = c.name

    # Строим DataFrame
    records = []
    for row in rows:
        cat_id = product_to_category.get(row.product_id)
        records.append({
            "year":          row.created_at.year,
            "month":         row.created_at.month,
            "category_id":   cat_id,
            "category_name": category_names.get(cat_id, "Без категории"),
            "quantity":      row.quantity,
            "revenue":       float(row.price) * row.quantity,
        })

    df = pd.DataFrame(records)
    if df.empty:
        return df

    # Группируем по месяцу и категории
    df_grouped = (
        df.groupby(["year", "month", "category_id", "category_name"])
        .agg(total_items=("quantity", "sum"), total_revenue=("revenue", "sum"))
        .reset_index()
    )
    return df_grouped


def forecast_next_month(db: Session) -> List[Dict]:
    """
    Прогноз спроса на следующий месяц по категориям.
    
    Использует линейную регрессию (скользящее среднее + тренд).
    
    Возвращает список словарей:
    [
        {
            "category_id": 1,
            "category_name": "Куклы",
            "predicted_items": 150,
            "predicted_revenue": 45000.0,
            "trend": "up",      # up/down/stable
            "confidence": 0.75  # условная уверенность
        },
        ...
    ]
    """
    df = get_monthly_sales_by_category(db, months=12)

    if df.empty:
        return [{"message": "Недостаточно данных для прогноза. Нужна история заказов."}]

    results = []
    categories = df["category_id"].unique()

    for cat_id in categories:
        cat_df = df[df["category_id"] == cat_id].sort_values(["year", "month"])
        cat_name = cat_df["category_name"].iloc[0]

        items_series = cat_df["total_items"].values
        revenue_series = cat_df["total_revenue"].values

        # Минимум 2 точки нужно для прогноза
        if len(items_series) < 2:
            predicted_items   = int(items_series[-1])
            predicted_revenue = float(revenue_series[-1])
            trend = "stable"
        else:
            # Взвешенное скользящее среднее (последние месяцы важнее)
            # Веса: 1, 2, 3, ... (чем свежее — тем важнее)
            weights = np.arange(1, len(items_series) + 1, dtype=float)
            predicted_items   = int(np.average(items_series,   weights=weights) * 1.1)
            predicted_revenue = float(np.average(revenue_series, weights=weights) * 1.1)

            # Определяем тренд
            recent_avg = np.mean(items_series[-3:]) if len(items_series) >= 3 else items_series[-1]
            earlier_avg = np.mean(items_series[:-3]) if len(items_series) > 3 else items_series[0]

            if recent_avg > earlier_avg * 1.1:
                trend = "up"       # Рост спроса
            elif recent_avg < earlier_avg * 0.9:
                trend = "down"     # Падение спроса
            else:
                trend = "stable"   # Стабильно

        # Условная уверенность: чем больше данных — тем выше
        confidence = min(0.95, len(items_series) / 12)

        results.append({
            "category_id":       int(cat_id) if cat_id else None,
            "category_name":     cat_name,
            "predicted_items":   predicted_items,
            "predicted_revenue": round(predicted_revenue, 2),
            "trend":             trend,
            "confidence":        round(confidence, 2),
            "data_points":       len(items_series),
        })

    # Сортируем по прогнозируемому спросу (самые популярные сначала)
    results.sort(key=lambda x: x["predicted_items"], reverse=True)
    return results
