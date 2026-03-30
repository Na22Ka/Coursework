"""
routers/products.py — публичные эндпоинты каталога товаров.

Эндпоинты:
  GET /api/products           — список товаров с фильтрами
  GET /api/products/featured  — главная страница (новинки/бестселлеры/акции)
  GET /api/products/{id}      — карточка товара
  GET /api/categories         — список категорий
  GET /api/categories/{id}    — одна категория
"""
import math
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud import product as product_crud
from app.database import get_db
from app.schemas.product import (
    CategoryResponse, CategoryWithChildren,
    ProductFilter, ProductListResponse, ProductResponse, ProductShort,
)

router = APIRouter(tags=["🛍️ Каталог"])


# ── Категории ─────────────────────────────────────────────────────────────────

@router.get(
    "/categories",
    response_model=List[CategoryResponse],
    summary="Список всех категорий",
)
def get_categories(db: Session = Depends(get_db)):
    """Возвращает все активные категории (включая подкатегории)."""
    return product_crud.get_categories(db)


@router.get(
    "/categories/tree",
    response_model=List[CategoryWithChildren],
    summary="Дерево категорий (с подкатегориями)",
)
def get_categories_tree(db: Session = Depends(get_db)):
    """
    Возвращает корневые категории с вложенными подкатегориями.
    Удобно для построения меню навигации.
    """
    return product_crud.get_root_categories(db)


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Одна категория по ID",
)
def get_category(category_id: int, db: Session = Depends(get_db)):
    category = product_crud.get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Категория не найдена")
    return category


# ── Товары ────────────────────────────────────────────────────────────────────

@router.get(
    "/products/featured",
    summary="Товары для главной страницы",
)
def get_featured_products(db: Session = Depends(get_db)):
    """
    Возвращает три группы товаров для главной страницы:
    - new_products: последние 8 новинок
    - bestsellers: до 4 бестселлеров
    - sale_products: до 4 товаров со скидкой
    """
    return {
        "new_products":   product_crud.get_new_products(db, limit=8),
        "bestsellers":    product_crud.get_bestsellers(db, limit=4),
        "sale_products":  product_crud.get_sale_products(db, limit=4),
    }


@router.get(
    "/products",
    response_model=ProductListResponse,
    summary="Каталог товаров с фильтрацией",
)
def get_products(
    # Query-параметры — то, что приходит в URL после ?
    # Например: /api/products?q=кукла&min_price=500&sort=price_asc&page=2
    q:             Optional[str]   = Query(None, description="Поиск по названию/описанию/бренду"),
    category_id:   Optional[int]   = Query(None, description="ID категории"),
    category_slug: Optional[str]   = Query(None, description="Slug категории"),
    min_price:     Optional[float] = Query(None, description="Минимальная цена"),
    max_price:     Optional[float] = Query(None, description="Максимальная цена"),
    age_from:      Optional[int]   = Query(None, description="Возраст от"),
    age_to:        Optional[int]   = Query(None, description="Возраст до"),
    brand:         Optional[str]   = Query(None, description="Бренд"),
    is_bestseller: Optional[bool]  = Query(None, description="Только бестселлеры"),
    in_stock:      Optional[bool]  = Query(None, description="Только в наличии"),
    sort:          str             = Query("newest", description="Сортировка: price_asc|price_desc|name|newest|bestseller|sale"),
    page:          int             = Query(1, ge=1, description="Номер страницы"),
    page_size:     int             = Query(20, ge=1, le=100, description="Товаров на странице"),
    db:            Session         = Depends(get_db),
):
    """
    Получить список товаров с фильтрацией, поиском и пагинацией.
    
    Все параметры необязательны.
    """
    filters = ProductFilter(
        q=q,
        category_id=category_id,
        category_slug=category_slug,
        min_price=min_price,
        max_price=max_price,
        age_from=age_from,
        age_to=age_to,
        brand=brand,
        is_bestseller=is_bestseller,
        in_stock=in_stock,
        sort=sort,
        page=page,
        page_size=page_size,
    )

    products, total = product_crud.get_products(db, filters)
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return ProductListResponse(
        items=products,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Карточка товара",
)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Полная информация о товаре:
    - Основные данные
    - Характеристики
    - Категория
    """
    product = product_crud.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product
