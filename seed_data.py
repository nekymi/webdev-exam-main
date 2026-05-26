"""Скрипт начального заполнения БД: роли, админ, категории, демо-товары.
Контент категорий и товаров перенесён и адаптирован с публичной информации altayber.ru (без копирования HTML).

Запуск: python seed_data.py (из корня проекта, с активированным venv и .env)."""
import os
from dotenv import load_dotenv

_this_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_this_dir, ".env"))
load_dotenv()

from decimal import Decimal

from app import create_app, db
from app.models import Category, Product, Role, User

# локальные файлы в app/static/uploads/products/ (имена из репозитория)
_UPLOADS = [
    "uploads/products/1aef10f920fd45b0b840bcdafffcd9bb.png",
    "uploads/products/389fd878a0484ac193bc41ad90052ea9.png",
    "uploads/products/5494f7c0f8f44513b977d9e2d8761349.jpg",
]


def seed():
    app = create_app()
    with app.app_context():
        roles = [
            ("Администратор", "Полный доступ к системе"),
            ("Покупатель", "Покупатель магазина"),
        ]
        for name, description in roles:
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name, description=description))
        db.session.commit()

        admin_email = os.getenv("ADMIN_EMAIL", "admin@altay.local").strip().lower()
        admin_password = (os.getenv("ADMIN_PASSWORD") or "").strip()
        if not admin_password:
            admin_password = "admin123"
            print(
                "внимание: в .env не задан ADMIN_PASSWORD. "
                "для первого входа админа использован временный пароль admin123 - смените его после входа."
            )
        if not User.query.filter_by(email=admin_email).first():
            admin_role = Role.query.filter_by(name="Администратор").first()
            admin = User(
                email=admin_email,
                first_name="Админ",
                last_name="Алтай",
                role=admin_role,
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()

        # категории по линейке источника (названия сокращены и адаптированы)
        categories_data = [
            (
                "Алтайский мёд",
                "altayskiy-med",
                "Горный, таёжный и цветочный мёд с Алтая.",
            ),
            (
                "Фиточаи и сборы",
                "fitochai-sbory",
                "Травяные чаи и сборы без кофеина, для спокойного чаепития.",
            ),
            (
                "Бальзамы и сиропы",
                "balzamy-siropy",
                "Фитобальзамы и сиропы на основе алтайских трав и ягод.",
            ),
        ]
        for name, slug, description in categories_data:
            c = Category.query.filter_by(name=name).first()
            if not c:
                db.session.add(Category(name=name, slug=slug, description=description))
            else:
                c.slug = slug
                c.description = description
        db.session.commit()

        honey = Category.query.filter_by(slug="altayskiy-med").first()
        tea = Category.query.filter_by(slug="fitochai-sbory").first()
        balsam = Category.query.filter_by(slug="balzamy-siropy").first()

        # тексты описаний адаптированы с карточек товаров altayber.ru (кратко).
        sample_products = [
            {
                "sku": "ALT-MED-GORN-220",
                "name": "Мёд горный (стекло), 2,2 кг",
                "summary": "Горный мёд с альпийских лугов: тонкий вкус, редкий аромат, нежный цвет.",
                "description": (
                    "Высоко в горах, на альпийских лугах, цветут редкие кустарники и веками некошеные травы. "
                    "Горный мёд отличается тонким вкусом, редким ароматом и нежным цветом. "
                    "В составе — растения вроде акации, боярышника, жимолости, душицы и мастерство пчеловода."
                ),
                "price": Decimal("4050.00"),
                "stock_qty": 8,
                "image_filename": "img/content/product-honey.jpg",
                "category": honey,
            },
            {
                "sku": "ALT-TEA-HVOYA-100",
                "name": "Хвойный чай «Согревающий», 100 г",
                "summary": "Купаж хвойного чая: тайга, цитрус и специи в одном согревающем напитке.",
                "description": (
                    "Купажи хвойного чая: сочетание сибирской тайги и чайных культур Востока. "
                    "Ароматы хвои, цитрусовых и специй — для тех, кто ценит натуральный состав и необычный вкус."
                ),
                "price": Decimal("540.00"),
                "stock_qty": 35,
                "image_filename": "img/content/product-tea.jpg",
                "category": tea,
            },
            {
                "sku": "ALT-BAL-ZA-250",
                "name": "Бальзам «Золотой Алтай» общеукрепляющий, 250 мл",
                "summary": "Фитобальзам с натуральным сырьём алтайского региона — к чаю, сокам, воде.",
                "description": (
                    "Фитобальзам на основе натурного сырья Алтая. "
                    "Рекомендуем добавлять к чаю, сокам или воде по вкусу — как тёплый тонизирующий напиток."
                ),
                "price": Decimal("630.00"),
                "stock_qty": 22,
                "image_filename": "img/content/product-balsam.png",
                "category": balsam,

            },
        ]

        for data in sample_products:
            if not Product.query.filter_by(sku=data["sku"]).first():
                product = Product(
                    sku=data["sku"],
                    name=data["name"],
                    summary=data.get("summary"),
                    description=data["description"],
                    price=data["price"],
                    stock_qty=data["stock_qty"],
                    image_filename=data["image_filename"],
                    category_id=data["category"].id if data["category"] else None,
                    is_active=True,
                )
                db.session.add(product)
        db.session.commit()
    print("Seed завершён.")


if __name__ == "__main__":
    seed()
