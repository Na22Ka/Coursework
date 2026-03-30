"""
crud/order.py — операции с корзиной и заказами.
"""
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.order import Cart, CartItem, Order, OrderItem, OrderStatus, PickupPoint
from app.models.product import Product
from app.schemas.order import AddToCartRequest, OrderCreate, OrderStatusUpdate


# ── ПВЗ ───────────────────────────────────────────────────────────────────────

def get_pickup_points(db: Session, active_only: bool = True) -> List[PickupPoint]:
    query = db.query(PickupPoint)
    if active_only:
        query = query.filter(PickupPoint.is_active == True)
    return query.order_by(PickupPoint.city).all()


def get_pickup_point_by_id(db: Session, point_id: int) -> Optional[PickupPoint]:
    return db.query(PickupPoint).filter(PickupPoint.id == point_id).first()


# ── Корзина ───────────────────────────────────────────────────────────────────

def get_or_create_cart(db: Session, user_id: int) -> Cart:
    """
    Получить корзину пользователя или создать новую.
    
    У каждого пользователя только одна корзина.
    """
    cart = (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.product))
        .filter(Cart.user_id == user_id)
        .first()
    )
    if not cart:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def add_item_to_cart(db: Session, user_id: int, data: AddToCartRequest) -> Cart:
    """
    Добавить товар в корзину.
    
    Если товар уже есть в корзине — увеличиваем количество.
    Если нет — создаём новую позицию.
    """
    cart = get_or_create_cart(db, user_id)

    # Проверяем, есть ли такой товар в корзине
    existing_item = (
        db.query(CartItem)
        .filter(CartItem.cart_id == cart.id, CartItem.product_id == data.product_id)
        .first()
    )

    # Проверяем наличие на складе
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product or not product.is_available:
        raise ValueError("Товар недоступен")

    if existing_item:
        new_qty = existing_item.quantity + data.quantity
        if new_qty > product.stock:
            raise ValueError(f"На складе только {product.stock} шт.")
        existing_item.quantity = new_qty
    else:
        if data.quantity > product.stock:
            raise ValueError(f"На складе только {product.stock} шт.")
        new_item = CartItem(
            cart_id=cart.id,
            product_id=data.product_id,
            quantity=data.quantity,
        )
        db.add(new_item)

    db.commit()
    db.refresh(cart)
    return get_or_create_cart(db, user_id)  # Обновлённая корзина с товарами


def update_cart_item(db: Session, user_id: int, item_id: int, quantity: int) -> Cart:
    """Изменить количество товара в корзине. quantity=0 → удалить."""
    cart = get_or_create_cart(db, user_id)
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.cart_id == cart.id)
        .first()
    )
    if not item:
        raise ValueError("Позиция не найдена в корзине")

    if quantity <= 0:
        db.delete(item)
    else:
        product = item.product
        if quantity > product.stock:
            raise ValueError(f"На складе только {product.stock} шт.")
        item.quantity = quantity

    db.commit()
    return get_or_create_cart(db, user_id)


def remove_cart_item(db: Session, user_id: int, item_id: int) -> Cart:
    """Удалить позицию из корзины."""
    cart = get_or_create_cart(db, user_id)
    item = (
        db.query(CartItem)
        .filter(CartItem.id == item_id, CartItem.cart_id == cart.id)
        .first()
    )
    if item:
        db.delete(item)
        db.commit()
    return get_or_create_cart(db, user_id)


def clear_cart(db: Session, user_id: int) -> None:
    """Очистить корзину (после оформления заказа)."""
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart:
        db.query(CartItem).filter(CartItem.cart_id == cart.id).delete()
        db.commit()


# ── Заказы ────────────────────────────────────────────────────────────────────

def create_order(db: Session, user_id: int, data: OrderCreate) -> Order:
    """
    Создать заказ из корзины пользователя.
    
    Алгоритм:
    1. Получаем корзину пользователя
    2. Создаём Order
    3. Для каждой позиции корзины создаём OrderItem
    4. Уменьшаем stock у каждого товара
    5. Очищаем корзину
    """
    cart = (
        db.query(Cart)
        .options(joinedload(Cart.items).joinedload(CartItem.product))
        .filter(Cart.user_id == user_id)
        .first()
    )

    if not cart or not cart.items:
        raise ValueError("Корзина пуста")

    # Проверяем наличие всех товаров
    for item in cart.items:
        if not item.product or not item.product.is_available:
            raise ValueError(f"Товар «{item.product.name if item.product else '?'}» недоступен")
        if item.quantity > item.product.stock:
            raise ValueError(
                f"Товара «{item.product.name}» нет в достаточном количестве. "
                f"Доступно: {item.product.stock} шт."
            )

    # Считаем итоговую сумму
    total = sum(float(item.product.price) * item.quantity for item in cart.items)

    # Создаём заказ
    order = Order(
        user_id=user_id,
        payment_method=data.payment_method,
        pickup_point_id=data.pickup_point_id,
        delivery_address=data.delivery_address,
        comment=data.comment,
        total_price=total,
    )
    db.add(order)
    db.flush()  # Получаем order.id

    # Создаём позиции заказа
    for item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            product_name=item.product.name,   # Сохраняем название на момент заказа
            quantity=item.quantity,
            price=item.product.price,          # Сохраняем цену на момент заказа
        )
        db.add(order_item)

        # Уменьшаем остаток на складе
        item.product.stock -= item.quantity
        if item.product.stock == 0:
            from app.models.product import ProductStatus
            item.product.status = ProductStatus.out_of_stock

    db.commit()

    # Очищаем корзину
    clear_cart(db, user_id)

    db.refresh(order)
    return order


def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
    return (
        db.query(Order)
        .options(
            joinedload(Order.items).joinedload(OrderItem.product),
            joinedload(Order.pickup_point),
        )
        .filter(Order.id == order_id)
        .first()
    )


def get_user_orders(db: Session, user_id: int) -> List[Order]:
    """Список заказов конкретного пользователя."""
    return (
        db.query(Order)
        .options(joinedload(Order.items))
        .filter(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )


def get_all_orders(
    db: Session,
    status: Optional[OrderStatus] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Order]:
    """Все заказы (для оператора/администратора)."""
    query = (
        db.query(Order)
        .options(joinedload(Order.items), joinedload(Order.user))
        .order_by(Order.created_at.desc())
    )
    if status:
        query = query.filter(Order.status == status)
    return query.offset(skip).limit(limit).all()


def update_order_status(db: Session, order: Order, data: OrderStatusUpdate) -> Order:
    """Обновить статус заказа."""
    order.status = data.status
    if data.operator_note is not None:
        order.operator_note = data.operator_note
    db.commit()
    db.refresh(order)
    return order


def cancel_order(db: Session, order: Order) -> Order:
    """
    Отменить заказ.
    Возвращает товары обратно на склад.
    """
    if not order.can_be_cancelled:
        raise ValueError("Этот заказ нельзя отменить")

    from app.models.product import ProductStatus

    # Возвращаем товары на склад
    for item in order.items:
        if item.product:
            item.product.stock += item.quantity
            if item.product.status == ProductStatus.out_of_stock:
                item.product.status = ProductStatus.active

    order.status = OrderStatus.cancelled
    db.commit()
    db.refresh(order)
    return order
