"""
seed_data.py — скрипт для заполнения базы данных начальными данными.

Запуск: python seed_data.py

Создаёт:
- Тестовых пользователей (admin, operator, покупатели)
- Категории игрушек
- Товары
- ПВЗ (пункты выдачи заказов)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base
from app.models import *  # Импортируем все модели
from app.models.user import User, UserRole
from app.models.product import Category, Product, ProductCharacteristics, ProductStatus
from app.models.order import PickupPoint
from app.auth.jwt import hash_password


def seed_database():
    """Заполнить базу данных начальными данными."""
    # Создаём все таблицы (если не существуют)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        print("🌱 Начинаем заполнение базы данных...")

        # ── 1. Пользователи ───────────────────────────────────────────────────
        print("👤 Создаём пользователей...")

        users_data = [
            {
                "email": "admin@toyshop.ru",
                "first_name": "Иван",
                "last_name": "Администратов",
                "hashed_password": hash_password("admin123"),
                "role": UserRole.admin,
            },
            {
                "email": "operator@toyshop.ru",
                "first_name": "Мария",
                "last_name": "Операторова",
                "hashed_password": hash_password("operator123"),
                "role": UserRole.operator,
            },
            {
                "email": "manager@toyshop.ru",
                "first_name": "Пётр",
                "last_name": "Менеджеров",
                "hashed_password": hash_password("manager123"),
                "role": UserRole.manager,
            },
            {
                "email": "user@example.com",
                "first_name": "Анна",
                "last_name": "Покупателева",
                "phone": "+79001234567",
                "hashed_password": hash_password("user123"),
                "role": UserRole.customer,
                "address": "г. Москва, ул. Примерная, д. 1",
            },
            {
                "email": "test@example.com",
                "first_name": "Тест",
                "last_name": "Тестов",
                "hashed_password": hash_password("test123"),
                "role": UserRole.customer,
            },
        ]

        for u_data in users_data:
            if not db.query(User).filter(User.email == u_data["email"]).first():
                user = User(**u_data)
                db.add(user)
        db.commit()
        print(f"  ✅ Создано {len(users_data)} пользователей")

        # ── 2. Категории ──────────────────────────────────────────────────────
        print("📁 Создаём категории...")

        root_categories = [
            {"name": "Мягкие игрушки",       "slug": "myagkie",      "description": "Мягкие и плюшевые игрушки для всех возрастов"},
            {"name": "Куклы",                 "slug": "kukly",        "description": "Куклы Барби, Братц, Монстер Хай и другие"},
            {"name": "Машинки",               "slug": "mashinki",     "description": "Машинки, грузовики, гоночные автомобили"},
            {"name": "Радиоуправляемые",      "slug": "rc",           "description": "Радиоуправляемые машинки, самолёты, квадрокоптеры"},
            {"name": "Аниме",                 "slug": "anime",        "description": "Фигурки и игрушки по аниме"},
            {"name": "Мультгерои",            "slug": "multgeroi",    "description": "Человек-паук, My Little Pony и другие"},
            {"name": "Подушки",               "slug": "podushki",     "description": "Декоративные подушки в виде животных и смайлов"},
            {"name": "Конструкторы",          "slug": "konstruktory", "description": "Лего и другие конструкторы"},
        ]

        root_cat_objs = {}
        for rc in root_categories:
            if not db.query(Category).filter(Category.slug == rc["slug"]).first():
                cat = Category(**rc)
                db.add(cat)
                db.flush()
                root_cat_objs[rc["slug"]] = cat
            else:
                root_cat_objs[rc["slug"]] = db.query(Category).filter(Category.slug == rc["slug"]).first()
        db.commit()

        # Подкатегории
        subcategories = [
            # Мягкие → Животные
            {"name": "Кошки",      "slug": "koshki",      "parent_slug": "myagkie"},
            {"name": "Собаки",     "slug": "sobaki",      "parent_slug": "myagkie"},
            {"name": "Единороги",  "slug": "edinorogi",   "parent_slug": "myagkie"},
            {"name": "Лисы",       "slug": "lisy",        "parent_slug": "myagkie"},
            {"name": "Лягушки",    "slug": "lyagushki",   "parent_slug": "myagkie"},
            # Куклы
            {"name": "Барби",      "slug": "barbie",      "parent_slug": "kukly"},
            {"name": "Братц",      "slug": "bratz",       "parent_slug": "kukly"},
            {"name": "Монстер Хай","slug": "monsterhigh", "parent_slug": "kukly"},
            # Машинки
            {"name": "Легковые",   "slug": "legkovye",    "parent_slug": "mashinki"},
            {"name": "Грузовые",   "slug": "gruzovye",    "parent_slug": "mashinki"},
            {"name": "Гоночные",   "slug": "gonochye",    "parent_slug": "mashinki"},
            # RC
            {"name": "Квадрокоптеры", "slug": "drony",   "parent_slug": "rc"},
            {"name": "RC-машинки",    "slug": "rc-cars",  "parent_slug": "rc"},
            # Аниме
            {"name": "Магическая Битва", "slug": "jjk",   "parent_slug": "anime"},
            {"name": "Берсерк",          "slug": "berserk","parent_slug": "anime"},
        ]

        for sc in subcategories:
            if not db.query(Category).filter(Category.slug == sc["slug"]).first():
                parent = root_cat_objs.get(sc["parent_slug"])
                cat = Category(
                    name=sc["name"],
                    slug=sc["slug"],
                    parent_id=parent.id if parent else None,
                )
                db.add(cat)
        db.commit()
        print(f"  ✅ Создано {len(root_categories)} корневых и {len(subcategories)} подкатегорий")

        # ── 3. ПВЗ ────────────────────────────────────────────────────────────
        print("📍 Создаём пункты выдачи заказов...")

        pvz_list = [
            {"name": "ПВЗ Центр",         "address": "ул. Тверская, д. 10",    "city": "Москва",       "working_hours": "Пн-Вс 9:00-21:00", "phone": "+74951234567"},
            {"name": "ПВЗ Юго-Запад",     "address": "пр. Вернадского, д. 86", "city": "Москва",       "working_hours": "Пн-Пт 10:00-20:00","phone": "+74957654321"},
            {"name": "ПВЗ Невский",        "address": "Невский пр., д. 55",     "city": "Санкт-Петербург","working_hours": "Пн-Вс 10:00-22:00","phone": "+78121112233"},
            {"name": "ПВЗ Новосибирск",    "address": "ул. Ленина, д. 1",       "city": "Новосибирск",  "working_hours": "Пн-Пт 9:00-19:00"},
            {"name": "ПВЗ Краснодар",      "address": "ул. Красная, д. 100",    "city": "Краснодар",    "working_hours": "Пн-Сб 9:00-20:00"},
        ]

        for pvz_data in pvz_list:
            if not db.query(PickupPoint).filter(
                PickupPoint.name == pvz_data["name"]
            ).first():
                pvz = PickupPoint(**pvz_data)
                db.add(pvz)
        db.commit()
        print(f"  ✅ Создано {len(pvz_list)} ПВЗ")

        # ── 4. Товары ─────────────────────────────────────────────────────────
        print("🧸 Создаём товары...")

        # Получаем категории по slug
        def get_cat(slug):
            return db.query(Category).filter(Category.slug == slug).first()

        products_data = [
            # Мягкие игрушки
            {
                "name": "Плюшевый кот Симон 40 см",
                "category_slug": "koshki",
                "price": 1290.0,
                "stock": 50,
                "brand": "Мягкий мир",
                "age_from": 0, "age_to": 99,
                "description": "Мягкий плюшевый кот белого цвета. Приятный на ощупь, безопасные материалы.",
                "is_bestseller": True,
                "discount_percent": 10,
                "chars": {"color": "белый", "material": "плюш", "height": 40.0, "weight": 350},
            },
            {
                "name": "Единорог радужный 55 см",
                "category_slug": "edinorogi",
                "price": 1890.0,
                "stock": 30,
                "brand": "Rainbow Toys",
                "age_from": 3, "age_to": 99,
                "description": "Радужный единорог с блестящей гривой. Отличный подарок для девочки.",
                "is_bestseller": True,
                "chars": {"color": "розовый/радужный", "material": "плюш", "height": 55.0, "weight": 500},
            },
            {
                "name": "Лягушонок Кермит 30 см",
                "category_slug": "lyagushki",
                "price": 890.0,
                "stock": 25,
                "brand": "Мягкий мир",
                "age_from": 0, "age_to": 99,
                "description": "Мягкая игрушка лягушонок зелёного цвета. Мягкая и безопасная.",
                "chars": {"color": "зелёный", "material": "флис", "height": 30.0, "weight": 200},
            },
            # Куклы
            {
                "name": "Кукла Барби Стиль 2024",
                "category_slug": "barbie",
                "price": 2490.0,
                "stock": 40,
                "brand": "Mattel",
                "age_from": 3, "age_to": 12,
                "description": "Кукла Барби с модным нарядом. В комплекте аксессуары.",
                "is_bestseller": True,
                "chars": {"color": "блонд", "material": "пластик", "height": 29.0, "sku": "BBR-2024"},
            },
            {
                "name": "Монстер Хай Клодин 26 см",
                "category_slug": "monsterhigh",
                "price": 3190.0,
                "stock": 15,
                "brand": "Mattel",
                "age_from": 6, "age_to": 14,
                "description": "Кукла Монстер Хай — Клодин Вульф. Шарнирная, в фирменном наряде.",
                "chars": {"sku": "MH-CLAWDEEN"},
            },
            # Машинки
            {
                "name": "Машина Hot Wheels гоночная",
                "category_slug": "gonochye",
                "price": 299.0,
                "stock": 100,
                "brand": "Hot Wheels",
                "age_from": 3, "age_to": 12,
                "description": "Литая гоночная машинка из серии Hot Wheels.",
                "discount_percent": 0,
                "chars": {"color": "красный", "material": "металл/пластик", "length": 8.0, "sku": "HW-RACE-01"},
            },
            {
                "name": "Грузовик с прицепом 1:24",
                "category_slug": "gruzovye",
                "price": 1590.0,
                "stock": 20,
                "brand": "Технопарк",
                "age_from": 5, "age_to": 14,
                "description": "Большой грузовик с открывающимся кузовом и прицепом. Масштаб 1:24.",
                "chars": {"color": "синий", "length": 42.0},
            },
            # Радиоуправляемые
            {
                "name": "Квадрокоптер Fold Mini",
                "category_slug": "drony",
                "price": 4990.0,
                "stock": 12,
                "brand": "SkyTech",
                "age_from": 14, "age_to": 99,
                "description": "Складной квадрокоптер с камерой 720p. Дальность полёта до 100 м.",
                "is_bestseller": True,
                "chars": {"sku": "ST-FOLD-MINI", "weight": 95},
            },
            {
                "name": "RC Машина Monster Truck 4WD",
                "category_slug": "rc-cars",
                "price": 3490.0,
                "stock": 18,
                "brand": "Remo Hobby",
                "age_from": 8, "age_to": 99,
                "description": "Полноприводный монстр-трак с управлением на 2.4 ГГц. Скорость до 30 км/ч.",
                "chars": {"length": 38.0, "weight": 1200},
            },
            # Аниме
            {
                "name": "Фигурка Итадори Юдзи 20 см",
                "category_slug": "jjk",
                "price": 2990.0,
                "stock": 10,
                "brand": "Good Smile",
                "age_from": 14, "age_to": 99,
                "description": "Коллекционная фигурка главного героя манги Магическая Битва.",
                "is_bestseller": True,
                "discount_percent": 15,
                "chars": {"height": 20.0, "material": "PVC", "sku": "GS-JJK-YUJI"},
            },
            {
                "name": "Фигурка Гатс — Берсерк 18 см",
                "category_slug": "berserk",
                "price": 3590.0,
                "stock": 7,
                "brand": "Max Factory",
                "age_from": 18, "age_to": 99,
                "description": "Детально проработанная фигурка Гатса в Доспехах Берсерка.",
                "chars": {"height": 18.0, "material": "PVC/ABS", "sku": "MF-GUTS-BERSERK"},
            },
            # Подушки
            {
                "name": "Подушка-авокадо 40×40 см",
                "category_slug": "podushki",
                "price": 690.0,
                "stock": 60,
                "brand": "СофтДом",
                "age_from": 0, "age_to": 99,
                "description": "Декоративная подушка в форме авокадо. Мягкий наполнитель.",
                "discount_percent": 5,
                "chars": {"color": "зелёный", "material": "велюр", "height": 40.0, "length": 40.0},
            },
            {
                "name": "Длинная подушка-акула 150 см",
                "category_slug": "podushki",
                "price": 1990.0,
                "stock": 35,
                "brand": "Акула-пилула",
                "age_from": 0, "age_to": 99,
                "description": "Большая мягкая подушка в виде акулы. Можно обнимать.",
                "is_bestseller": True,
                "chars": {"color": "серый", "material": "плюш", "length": 150.0},
            },
        ]

        for pd in products_data:
            if not db.query(Product).filter(Product.name == pd["name"]).first():
                cat_slug = pd.pop("category_slug", None)
                chars_data = pd.pop("chars", None)
                cat = get_cat(cat_slug) if cat_slug else None

                product = Product(
                    category_id=cat.id if cat else None,
                    **pd
                )
                db.add(product)
                db.flush()

                if chars_data:
                    chars = ProductCharacteristics(product_id=product.id, **chars_data)
                    db.add(chars)

        db.commit()
        print(f"  ✅ Создано {len(products_data)} товаров")

        print()
        print("✅ База данных успешно заполнена!")
        print()
        print("📋 Тестовые аккаунты:")
        print("  👑 admin@toyshop.ru      / admin123    (Администратор)")
        print("  🔧 operator@toyshop.ru   / operator123 (Оператор)")
        print("  📊 manager@toyshop.ru    / manager123  (Менеджер)")
        print("  🛒 user@example.com      / user123     (Покупатель)")
        print("  🧪 test@example.com      / test123     (Покупатель)")

    except Exception as e:
        db.rollback()
        print(f"❌ Ошибка: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
