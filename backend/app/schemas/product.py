"""
schemas/product.py — Pydantic-схемы для товаров и категорий.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.product import ProductStatus


# ── Характеристики ────────────────────────────────────────────────────────────

class CharacteristicsBase(BaseModel):
    sku:      Optional[str]   = None
    color:    Optional[str]   = None
    material: Optional[str]   = None
    height:   Optional[float] = None
    length:   Optional[float] = None
    width:    Optional[float] = None
    weight:   Optional[int]   = None
    country:  Optional[str]   = None


class CharacteristicsCreate(CharacteristicsBase):
    pass


class CharacteristicsResponse(CharacteristicsBase):
    id: int
    class Config:
        from_attributes = True


# ── Категории ─────────────────────────────────────────────────────────────────

class CategoryBase(BaseModel):
    name:        str           = Field(..., max_length=100)
    slug:        str           = Field(..., max_length=100)
    description: Optional[str] = None
    parent_id:   Optional[int] = None
    is_active:   bool          = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name:        Optional[str]  = None
    description: Optional[str]  = None
    is_active:   Optional[bool] = None


class CategoryResponse(CategoryBase):
    id:         int
    image:      Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CategoryWithChildren(CategoryResponse):
    """Категория со списком подкатегорий."""
    children: List["CategoryResponse"] = []

    class Config:
        from_attributes = True


# ── Товары ────────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    name:             str           = Field(..., max_length=200, description="Название товара")
    description:      Optional[str] = Field(None, description="Описание")
    price:            float         = Field(..., gt=0, description="Цена в рублях")
    stock:            int           = Field(0, ge=0, description="Количество на складе")
    status:           ProductStatus = ProductStatus.active
    age_from:         int           = Field(0, ge=0, le=99)
    age_to:           int           = Field(99, ge=0, le=99)
    brand:            Optional[str] = Field(None, max_length=100)
    is_bestseller:    bool          = False
    discount_percent: int           = Field(0, ge=0, le=100)
    category_id:      Optional[int] = None


class ProductCreate(ProductBase):
    """Схема для создания нового товара (POST /admin/products)."""
    characteristics: Optional[CharacteristicsCreate] = None


class ProductUpdate(BaseModel):
    """Схема для обновления товара (PATCH /admin/products/{id})."""
    name:             Optional[str]           = None
    description:      Optional[str]           = None
    price:            Optional[float]         = Field(None, gt=0)
    stock:            Optional[int]           = Field(None, ge=0)
    status:           Optional[ProductStatus] = None
    age_from:         Optional[int]           = Field(None, ge=0, le=99)
    age_to:           Optional[int]           = Field(None, ge=0, le=99)
    brand:            Optional[str]           = None
    is_bestseller:    Optional[bool]          = None
    discount_percent: Optional[int]           = Field(None, ge=0, le=100)
    category_id:      Optional[int]           = None
    characteristics:  Optional[CharacteristicsCreate] = None


class ProductResponse(ProductBase):
    """Полная карточка товара в ответе API."""
    id:               int
    image:            Optional[str]                  = None
    discounted_price: float                          = 0.0
    is_available:     bool                           = True
    created_at:       datetime
    updated_at:       datetime
    category:         Optional[CategoryResponse]     = None
    characteristics:  Optional[CharacteristicsResponse] = None

    class Config:
        from_attributes = True


class ProductShort(BaseModel):
    """Краткая карточка товара (для списков, корзины)."""
    id:               int
    name:             str
    price:            float
    discounted_price: float
    image:            Optional[str] = None
    status:           ProductStatus
    stock:            int
    discount_percent: int
    category_id:      Optional[int] = None

    class Config:
        from_attributes = True


# ── Фильтры каталога ──────────────────────────────────────────────────────────

class ProductFilter(BaseModel):
    """Параметры фильтрации каталога (приходят в query-параметрах URL)."""
    q:            Optional[str]   = Field(None, description="Поисковый запрос")
    category_id:  Optional[int]   = None
    category_slug:Optional[str]   = None
    min_price:    Optional[float] = None
    max_price:    Optional[float] = None
    age_from:     Optional[int]   = None
    age_to:       Optional[int]   = None
    brand:        Optional[str]   = None
    is_bestseller:Optional[bool]  = None
    in_stock:     Optional[bool]  = None
    sort:         Optional[str]   = Field("newest", description="price_asc|price_desc|name|newest|bestseller|sale")
    page:         int             = Field(1, ge=1)
    page_size:    int             = Field(20, ge=1, le=100)


class ProductListResponse(BaseModel):
    """Ответ на запрос списка товаров с пагинацией."""
    items:      List[ProductShort]
    total:      int
    page:       int
    page_size:  int
    total_pages:int
