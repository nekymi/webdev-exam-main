"""Однократно проставляет товарам картинки из app/static/uploads/products/ по кругу.
Запуск из корня проекта: python sync_product_images_from_uploads.py"""
import os

from dotenv import load_dotenv

_this_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_this_dir, ".env"))
load_dotenv()

from app import create_app, db
from app.models import Product, ProductImage


def _list_image_files():
    root = os.path.join(_this_dir, "app", "static", "uploads", "products")
    if not os.path.isdir(root):
        return []
    exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    names = []
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if os.path.isfile(path) and os.path.splitext(name)[1].lower() in exts:
            names.append(name)
    return sorted(names)


def sync():
    files = _list_image_files()
    if not files:
        print("Папка uploads/products пуста или не найдена — нечего назначать.")
        return

    app = create_app()
    with app.app_context():
        products = Product.query.order_by(Product.id).all()
        if not products:
            print("В БД нет товаров.")
            return

        n = len(files)
        for i, p in enumerate(products):
            rel = f"uploads/products/{files[i % n]}"
            ProductImage.query.filter_by(product_id=p.id).delete()
            p.image_filename = rel
        db.session.commit()
        print(f"Обновлено товаров: {len(products)}. Использованы файлы из uploads/products ({n} шт.), назначение по кругу.")


if __name__ == "__main__":
    sync()
