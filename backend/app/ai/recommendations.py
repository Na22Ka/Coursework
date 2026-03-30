"""
ai/recommendations.py — AI-модуль рекомендаций товаров.

Использует коллаборативную фильтрацию на основе истории заказов.

Алгоритм:
1. Строим матрицу совместных покупок:
   entry[i][j] = сколько раз товар i и товар j покупали вместе
2. Вычисляем косинусное сходство между строками матрицы
3. Для запрошенного товара находим N самых похожих

Если данных мало (магазин новый) — возвращаем товары из той же категории.
"""
from typing import List, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.product import Product, ProductStatus


def build_cooccurrence_matrix(db: Session):
    """
    Строит матрицу совместных покупок из истории заказов.
    
    Возвращает: (матрица numpy, список product_id в порядке столбцов/строк)
    """
    # Получаем ID всех активных товаров
    product_ids = [
        p.id for p in db.query(Product.id).filter(Product.status == ProductStatus.active).all()
    ]
    n = len(product_ids)

    if n == 0:
        return None, []

    # Индекс: product_id → позиция в матрице
    idx = {pid: i for i, pid in enumerate(product_ids)}

    # Матрица n×n, изначально все нули
    matrix = np.zeros((n, n), dtype=np.float32)

    # Обходим все заказы
    orders = db.query(Order).all()
    for order in orders:
        # ID товаров в этом заказе
        items_in_order = [
            item.product_id
            for item in db.query(OrderItem.product_id)
                          .filter(OrderItem.order_id == order.id)
                          .all()
            if item.product_id in idx
        ]

        # Для каждой пары товаров увеличиваем счётчик
        for i in range(len(items_in_order)):
            for j in range(len(items_in_order)):
                if i != j:
                    matrix[idx[items_in_order[i]]][idx[items_in_order[j]]] += 1

    return matrix, product_ids


def get_recommendations(
    db: Session,
    product_id: int,
    n: int = 4
) -> List[Product]:
    """
    Получить рекомендации для товара по ID.
    
    Параметры:
        db         — сессия базы данных
        product_id — ID товара, для которого ищем рекомендации
        n          — количество рекомендаций
    
    Возвращает: список объектов Product
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return []

    try:
        matrix, product_ids = build_cooccurrence_matrix(db)

        # Если данных нет или товар отсутствует в истории
        if matrix is None or product_id not in product_ids:
            return _fallback_recommendations(db, product, n)

        idx = {pid: i for i, pid in enumerate(product_ids)}
        product_idx = idx[product_id]

        # Вычисляем косинусное сходство строки этого товара со всеми остальными
        product_vector = matrix[product_idx].reshape(1, -1)
        similarities = cosine_similarity(product_vector, matrix)[0]

        # Убираем сам товар из результатов
        similarities[product_idx] = -1

        # Берём N индексов с наибольшим сходством
        top_indices = np.argsort(similarities)[::-1][:n]

        # Фильтруем: берём только те, где сходство > 0 (действительно покупали вместе)
        recommended_ids = [
            product_ids[i]
            for i in top_indices
            if similarities[i] > 0
        ]

        if recommended_ids:
            products = (
                db.query(Product)
                .filter(Product.id.in_(recommended_ids), Product.status == ProductStatus.active)
                .all()
            )
            # Сохраняем порядок по убыванию сходства
            products.sort(key=lambda p: recommended_ids.index(p.id) if p.id in recommended_ids else 999)
            return products

    except Exception:
        pass  # При любой ошибке — запасной вариант

    return _fallback_recommendations(db, product, n)


def _fallback_recommendations(db: Session, product: Product, n: int = 4) -> List[Product]:
    """
    Запасной вариант: товары из той же категории.
    Используется когда нет данных о совместных покупках.
    """
    query = (
        db.query(Product)
        .filter(Product.status == ProductStatus.active, Product.id != product.id)
    )

    if product.category_id:
        same_category = query.filter(Product.category_id == product.category_id).limit(n).all()
        if len(same_category) >= n:
            return same_category
        # Добираем из других категорий
        other = (
            query.filter(Product.category_id != product.category_id)
            .limit(n - len(same_category))
            .all()
        )
        return same_category + other

    return query.order_by(Product.created_at.desc()).limit(n).all()
