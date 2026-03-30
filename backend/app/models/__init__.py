# Этот файл делает папку models "пакетом" Python.
# Здесь импортируем все модели, чтобы Alembic их видел при создании миграций.
from app.models.user import User, UserRole
from app.models.product import Product, Category, ProductCharacteristics
from app.models.order import Cart, CartItem, Order, OrderItem, PickupPoint
from app.models.review import Review

__all__ = [
    "User", "UserRole",
    "Product", "Category", "ProductCharacteristics",
    "Cart", "CartItem", "Order", "OrderItem", "PickupPoint",
    "Review",
]
