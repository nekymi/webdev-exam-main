"""Сервис загрузки и управления изображениями товаров."""
import uuid
from pathlib import Path

from flask import current_app

from app import db
from app.models import Product, ProductImage


def _uploads_dir():
    """Путь к папке uploads/products (относительно static)."""
    root = current_app.static_folder
    path = Path(root) / "uploads" / "products"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _allowed_file(filename):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config.get("UPLOAD_PRODUCT_EXTENSIONS", {"jpg", "jpeg", "png", "webp"})


def _relative_path(filename):
    """Относительный путь для сохранения в БД: uploads/products/xxx.jpg."""
    return f"uploads/products/{filename}"


def save_product_images(product_id, files):
    """
    Сохраняет загруженные файлы на диск и создаёт записи ProductImage.
    files: list of FileStorage from request.files.getlist().
    Returns: (created_count, error_message or None).
    """
    product = db.session.get(Product, product_id)
    if not product:
        return 0, "Товар не найден"

    upload_dir = _uploads_dir()
    created = 0
    max_order = db.session.query(db.func.max(ProductImage.sort_order)).filter_by(product_id=product_id).scalar() or 0
    first_saved = None

    for f in files:
        if not f or f.filename == "":
            continue
        if not _allowed_file(f.filename):
            continue
        ext = f.filename.rsplit(".", 1)[1].lower()
        if ext == "jpeg":
            ext = "jpg"
        new_name = f"{uuid.uuid4().hex}.{ext}"
        filepath = upload_dir / new_name
        try:
            f.save(str(filepath))
        except Exception as e:
            current_app.logger.warning("Failed to save upload %s: %s", new_name, e)
            continue
        rel = _relative_path(new_name)
        img = ProductImage(
            product_id=product_id,
            filename=rel,
            sort_order=max_order + 1 + created,
            is_main=False,
        )
        db.session.add(img)
        if first_saved is None:
            first_saved = img
        created += 1

    if created:
        has_main = ProductImage.query.filter_by(product_id=product_id, is_main=True).first()
        if not has_main and first_saved:
            first_saved.is_main = True
        db.session.commit()
    return created, None


def delete_product_image(image_id):
    """
    Удаляет ProductImage и файл с диска.
    Returns: (True, None) or (False, error_message).
    """
    img = db.session.get(ProductImage, image_id)
    if not img:
        return False, "Изображение не найдено"
    product_id = img.product_id
    filepath = Path(current_app.static_folder) / img.filename
    db.session.delete(img)
    db.session.commit()
    if filepath.exists():
        try:
            filepath.unlink()
        except OSError:
            pass
    return True, None


def set_main_image(product_id, image_id):
    """Делает одно изображение главным (остальные is_main=False)."""
    product = db.session.get(Product, product_id)
    if not product:
        return False, "Товар не найден"
    img = ProductImage.query.filter_by(id=image_id, product_id=product_id).first()
    if not img:
        return False, "Изображение не найдено"
    ProductImage.query.filter_by(product_id=product_id).update({"is_main": False})
    img.is_main = True
    db.session.commit()
    return True, None


def reorder_images(product_id, order_list):
    """
    order_list: list of (image_id, sort_order) or dict image_id -> sort_order.
    """
    product = db.session.get(Product, product_id)
    if not product:
        return False, "Товар не найден"
    if isinstance(order_list, dict):
        order_list = list(order_list.items())
    for image_id, sort_order in order_list:
        img = ProductImage.query.filter_by(id=image_id, product_id=product_id).first()
        if img:
            img.sort_order = int(sort_order)
    db.session.commit()
    return True, None
