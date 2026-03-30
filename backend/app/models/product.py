"""
models/product.py — модели товаров и категорий.

Таблицы:
  categories              — категории товаров (с подкатегориями)
  products                — товары (игрушки)
  product_characteristics — характеристики конкретного товара
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, Numeric, SmallInteger, String, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class ProductStatus(str, enum.Enum):
    """Статус товара в магазине."""
    active       = "active"        # Активен, можно купить
    inactive     = "inactive"      # Скрыт из каталога
    out_of_stock = "out_of_stock"  # Нет в наличии


class Category(Base):
    """
    Таблица categories — категории и подкатегории товаров.
    
    Пример иерархии:
      Животные (parent_id=NULL)
        └── Кошки (parent_id=1)
        └── Собаки (parent_id=1)
    """
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)

    # Название категории
    name = Column(String(100), nullable=False)

    # URL-slug: "mягкие-игрушки" — часть URL (/catalog?category=myagkie-igrushki)
    slug = Column(String(100), unique=True, index=True, nullable=False)

    # Описание категории (необязательное)
    description = Column(Text, nullable=True)

    # Путь к изображению категории
    image = Column(String(500), nullable=True)

    # Для подкатегорий: ID родительской категории
    # NULL = это корневая категория
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Показывать ли категорию в каталоге
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    # children — подкатегории этой категории
    children = relationship("Category", back_populates="parent", lazy="select")
    parent   = relationship("Category", back_populates="children", remote_side="Category.id")
    products = relationship("Product",  back_populates="category", lazy="dynamic")

    def __repr__(self):
        return f"<Category id={self.id} name={self.name}>"


class Product(Base):
    """
    Таблица products — товары магазина.
    """
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    # Название товара
    name = Column(String(200), nullable=False, index=True)

    # Категория (внешний ключ → categories.id)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # Описание
    description = Column(Text, nullable=True)

    # Цена в рублях (Numeric = точные дробные числа, не теряет копейки)
    price = Column(Numeric(10, 2), nullable=False)

    # Количество на складе
    stock = Column(Integer, default=0)

    # Путь к изображению
    image = Column(String(500), nullable=True)

    # Статус товара
    status = Column(Enum(ProductStatus), default=ProductStatus.active, nullable=False)

    # Возрастной диапазон
    age_from = Column(SmallInteger, default=0)
    age_to   = Column(SmallInteger, default=99)

    # Бренд-производитель
    brand = Column(String(100), nullable=True)

    # Флаги
    is_bestseller = Column(Boolean, default=False)

    # Скидка в процентах (0 = нет скидки)
    discount_percent = Column(SmallInteger, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    category        = relationship("Category",               back_populates="products")
    characteristics = relationship("ProductCharacteristics", back_populates="product", uselist=False)
    reviews         = relationship("Review",                 back_populates="product", lazy="dynamic")
    order_items     = relationship("OrderItem",              back_populates="product")
    cart_items      = relationship("CartItem",               back_populates="product")

    def __repr__(self):
        return f"<Product id={self.id} name={self.name} price={self.price}>"

    @property
    def discounted_price(self):
        """Цена с учётом скидки."""
        if self.discount_percent and self.discount_percent > 0:
            from decimal import Decimal
            discount = self.price * Decimal(self.discount_percent) / Decimal(100)
            return float((self.price - discount))
        return float(self.price)

    @property
    def is_available(self):
        """Доступен ли товар для покупки."""
        return self.status == ProductStatus.active and self.stock > 0


class ProductCharacteristics(Base):
    """
    Таблица product_characteristics — физические характеристики товара.
    
    Отдельная таблица (а не просто колонки в products) потому что:
    - не все товары имеют все характеристики
    - проще расширять список характеристик
    """
    __tablename__ = "product_characteristics"

    id = Column(Integer, primary_key=True, index=True)

    # Связь с товаром (один-к-одному)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), unique=True)

    # Артикул (уникальный код товара)
    sku = Column(String(100), nullable=True, unique=True)

    # Цвет
    color = Column(String(50), nullable=True)

    # Материал
    material = Column(String(100), nullable=True)

    # Размеры в сантиметрах
    height = Column(Numeric(6, 1), nullable=True)
    length = Column(Numeric(6, 1), nullable=True)
    width  = Column(Numeric(6, 1), nullable=True)

    # Вес в граммах
    weight = Column(Integer, nullable=True)

    # Страна производства
    country = Column(String(50), nullable=True)

    # Связь
    product = relationship("Product", back_populates="characteristics")

    def __repr__(self):
        return f"<ProductCharacteristics product_id={self.product_id}>"
