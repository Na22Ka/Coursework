"""
crud/product.py — операции с товарами и категориями.
"""
import os
from typing import List, Optional, Tuple

from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload

from app.models.product import Category, Product, ProductCharacteristics, ProductStatus
from app.schemas.product import (
    CategoryCreate, CategoryUpdate,
    ProductCreate, ProductUpdate, ProductFilter
)


# ── Категории ─────────────────────────────────────────────────────────────────

def get_categories(db: Session, active_only: bool = True) -> List[Category]:
    """Список всех категорий (с подкатегориями)."""
    query = db.query(Category)
    if active_only:
        query = query.filter(Category.is_active == True)
    return query.order_by(Category.name).all()


def get_root_categories(db: Session) -> List[Category]:
    """Только корневые категории (без родителя)."""
    return (
        db.query(Category)
        .filter(Category.parent_id == None, Category.is_active == True)
        .order_by(Category.name)
        .all()
    )


def get_category_by_id(db: Session, category_id: int) -> Optional[Category]:
    return db.query(Category).filter(Category.id == category_id).first()


def get_category_by_slug(db: Session, slug: str) -> Optional[Category]:
    return db.query(Category).filter(Category.slug == slug).first()


def create_category(db: Session, data: CategoryCreate) -> Category:
    category = Category(**data.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: Category, data: CategoryUpdate) -> Category:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()


# ── Товары ────────────────────────────────────────────────────────────────────

def get_product_by_id(db: Session, product_id: int) -> Optional[Product]:
    """Получить товар по ID с загрузкой связанных данных."""
    return (
        db.query(Product)
        .options(
            joinedload(Product.category),
            joinedload(Product.characteristics),
        )
        .filter(Product.id == product_id)
        .first()
    )


def get_products(
    db: Session,
    filters: ProductFilter
) -> Tuple[List[Product], int]:
    """
    Получить список товаров с фильтрацией, поиском и пагинацией.
    
    Возвращает кортеж (список товаров, общее количество).
    Общее количество нужно для пагинации на фронтенде.
    """
    query = db.query(Product).filter(Product.status == ProductStatus.active)

    # Поиск по тексту
    if filters.q:
        search = f"%{filters.q}%"
        query = query.filter(
            or_(
                Product.name.ilike(search),
                Product.description.ilike(search),
                Product.brand.ilike(search),
            )
        )

    # Фильтр по категории (по ID или slug)
    if filters.category_id:
        query = query.filter(Product.category_id == filters.category_id)
    elif filters.category_slug:
        query = query.join(Category).filter(Category.slug == filters.category_slug)

    # Фильтр по цене
    if filters.min_price is not None:
        query = query.filter(Product.price >= filters.min_price)
    if filters.max_price is not None:
        query = query.filter(Product.price <= filters.max_price)

    # Фильтр по возрасту
    if filters.age_from is not None:
        query = query.filter(Product.age_from >= filters.age_from)
    if filters.age_to is not None:
        query = query.filter(Product.age_to <= filters.age_to)

    # Фильтр по бренду
    if filters.brand:
        query = query.filter(Product.brand.ilike(f"%{filters.brand}%"))

    # Только бестселлеры
    if filters.is_bestseller:
        query = query.filter(Product.is_bestseller == True)

    # Только в наличии
    if filters.in_stock:
        query = query.filter(Product.stock > 0)

    # Сортировка
    sort_map = {
        "price_asc":   Product.price.asc(),
        "price_desc":  Product.price.desc(),
        "name":        Product.name.asc(),
        "newest":      Product.created_at.desc(),
        "bestseller":  Product.is_bestseller.desc(),
        "sale":        Product.discount_percent.desc(),
    }
    order_by = sort_map.get(filters.sort, Product.created_at.desc())
    query = query.order_by(order_by)

    # Считаем общее количество (до применения пагинации)
    total = query.count()

    # Пагинация: пропускаем первые N записей, берём следующие M
    offset = (filters.page - 1) * filters.page_size
    products = query.offset(offset).limit(filters.page_size).all()

    return products, total


def create_product(db: Session, data: ProductCreate, image_path: Optional[str] = None) -> Product:
    """Создать новый товар."""
    # Извлекаем характеристики (если есть) из данных
    char_data = data.characteristics
    product_data = data.model_dump(exclude={"characteristics"})
    product_data["image"] = image_path

    product = Product(**product_data)
    db.add(product)
    db.flush()  # flush сохраняет product в БД, но без commit — мы получаем product.id

    # Если переданы характеристики — создаём запись в product_characteristics
    if char_data:
        chars = ProductCharacteristics(
            product_id=product.id,
            **char_data.model_dump(exclude_unset=True)
        )
        db.add(chars)

    db.commit()
    db.refresh(product)
    return product


def update_product(
    db: Session,
    product: Product,
    data: ProductUpdate,
    image_path: Optional[str] = None
) -> Product:
    """Обновить товар."""
    update_dict = data.model_dump(exclude_unset=True, exclude={"characteristics"})

    if image_path:
        update_dict["image"] = image_path

    for field, value in update_dict.items():
        setattr(product, field, value)

    # Обновляем характеристики если переданы
    if data.characteristics:
        if product.characteristics:
            for field, value in data.characteristics.model_dump(exclude_unset=True).items():
                setattr(product.characteristics, field, value)
        else:
            chars = ProductCharacteristics(
                product_id=product.id,
                **data.characteristics.model_dump(exclude_unset=True)
            )
            db.add(chars)

    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product: Product) -> None:
    """Удалить товар и его изображение."""
    # Удаляем файл изображения если он есть
    if product.image and os.path.exists(product.image):
        os.remove(product.image)
    db.delete(product)
    db.commit()


def get_bestsellers(db: Session, limit: int = 4) -> List[Product]:
    """Бестселлеры для главной страницы."""
    return (
        db.query(Product)
        .filter(Product.status == ProductStatus.active, Product.is_bestseller == True)
        .limit(limit).all()
    )


def get_new_products(db: Session, limit: int = 8) -> List[Product]:
    """Новинки для главной страницы."""
    return (
        db.query(Product)
        .filter(Product.status == ProductStatus.active)
        .order_by(Product.created_at.desc())
        .limit(limit).all()
    )


def get_sale_products(db: Session, limit: int = 4) -> List[Product]:
    """Товары со скидкой для главной страницы."""
    return (
        db.query(Product)
        .filter(Product.status == ProductStatus.active, Product.discount_percent > 0)
        .order_by(Product.discount_percent.desc())
        .limit(limit).all()
    )
