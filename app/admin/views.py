import functools
from decimal import Decimal

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.admin import admin_bp
from app.models import Category, CorporateRequest, Order, Product, ImportLog
from app.order_constants import ADMIN_SELECTABLE_STATUSES, CORPORATE_REQUEST_STATUSES
from app.services.catalog_sync_service import run_csv_import
from app.services.image_service import (
    delete_product_image,
    reorder_images,
    save_product_images,
    set_main_image,
)


def admin_required(f):
    """декоратор: доступ только для авторизованного администратора."""
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not getattr(current_user, "is_admin", False):
            flash("Недостаточно прав.", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("")
@admin_required
def dashboard():
    product_count = Product.query.count()
    order_count = Order.query.count()
    category_count = Category.query.count()
    return render_template(
        "admin/dashboard.html",
        product_count=product_count,
        order_count=order_count,
        category_count=category_count,
    )


@admin_bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        slug = request.form.get("slug", "").strip() or None
        description = request.form.get("description", "").strip() or None
        if not name:
            flash("Название обязательно.", "danger")
            return redirect(url_for("admin.categories"))
        if Category.query.filter_by(name=name).first():
            flash("Такая категория уже есть.", "warning")
            return redirect(url_for("admin.categories"))
        db.session.add(Category(name=name, slug=slug, description=description))
        db.session.commit()
        flash("Категория добавлена.", "success")
        return redirect(url_for("admin.categories"))
    categories_list = Category.query.order_by(Category.name).all()
    return render_template("admin/categories.html", categories=categories_list)


@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
@admin_required
def category_edit(category_id):
    category = Category.query.get_or_404(category_id)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Название категории не может быть пустым.", "danger")
            return redirect(url_for("admin.category_edit", category_id=category_id))
        category.name = name
        category.slug = request.form.get("slug", "").strip() or None
        category.description = request.form.get("description", "").strip() or None
        db.session.commit()
        flash("Категория обновлена.", "success")
        return redirect(url_for("admin.categories"))
    return render_template("admin/category_form.html", category=category)


@admin_bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@admin_required
def category_delete(category_id):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash("Категория удалена.", "warning")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/products")
@admin_required
def products():
    page = request.args.get("page", 1, type=int)
    pagination = Product.query.order_by(Product.updated_at.desc()).paginate(page=page, per_page=20)
    return render_template("admin/products.html", pagination=pagination)


@admin_bp.route("/products/new", methods=["GET", "POST"])
@admin_required
def product_new():
    categories_list = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        sku = request.form.get("sku", "").strip()
        name = request.form.get("name", "").strip()
        summary = request.form.get("summary", "").strip() or None
        description = request.form.get("description", "").strip() or None
        price = request.form.get("price", type=Decimal)
        stock_qty = request.form.get("stock_qty", 0, type=int)
        category_id = request.form.get("category_id", type=int) or None
        is_active = request.form.get("is_active") == "1"
        image_filename = request.form.get("image_filename", "").strip() or None
        external_id = request.form.get("external_id", "").strip() or None

        if not sku or not name or price is None:
            flash("Заполните SKU, название и цену.", "danger")
            return redirect(url_for("admin.product_new"))
        if price < 0 or (stock_qty or 0) < 0:
            flash("Цена и остаток не могут быть отрицательными.", "danger")
            return redirect(url_for("admin.product_new"))
        if Product.query.filter_by(sku=sku).first():
            flash("Товар с таким SKU уже есть.", "danger")
            return redirect(url_for("admin.product_new"))

        product = Product(
            sku=sku,
            name=name,
            summary=summary,
            description=description,
            price=price,
            stock_qty=stock_qty or 0,
            category_id=category_id,
            is_active=is_active,
            image_filename=image_filename,
            external_id=external_id,
        )
        db.session.add(product)
        db.session.commit()
        msg = "Товар добавлен."
        upload_files = request.files.getlist("images")
        if upload_files and any(f and f.filename for f in upload_files):
            n, err = save_product_images(product.id, upload_files)
            if err:
                flash(err, "warning")
            elif n:
                msg += f" Загружено изображений: {n}."
        flash(msg, "success")
        return redirect(url_for("admin.product_edit", product_id=product.id))

    return render_template("admin/product_form.html", product=None, categories=categories_list)


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    categories_list = Category.query.order_by(Category.name).all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price", type=Decimal)
        if not name or price is None:
            flash("Название и цена обязательны.", "danger")
            return redirect(url_for("admin.product_edit", product_id=product_id))
        stock_qty = request.form.get("stock_qty", 0, type=int)
        if price < 0 or (stock_qty or 0) < 0:
            flash("Цена и остаток не могут быть отрицательными.", "danger")
            return redirect(url_for("admin.product_edit", product_id=product_id))
        sku = request.form.get("sku", "").strip()
        if not sku:
            flash("SKU не может быть пустым.", "danger")
            return redirect(url_for("admin.product_edit", product_id=product_id))
        product.sku = sku
        product.name = name
        product.summary = request.form.get("summary", "").strip() or None
        product.description = request.form.get("description", "").strip() or None
        product.price = price
        product.stock_qty = stock_qty
        product.category_id = request.form.get("category_id", type=int) or None
        product.is_active = request.form.get("is_active") == "1"
        product.image_filename = request.form.get("image_filename", "").strip() or None
        product.external_id = request.form.get("external_id", "").strip() or None
        db.session.commit()
        flash("Товар обновлён.", "success")
        return redirect(url_for("admin.products"))
    return render_template("admin/product_form.html", product=product, categories=categories_list)


@admin_bp.route("/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def product_delete(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Товар удалён.", "warning")
    return redirect(url_for("admin.products"))


@admin_bp.route("/products/<int:product_id>/images/upload", methods=["POST"])
@admin_required
def product_images_upload(product_id):
    Product.query.get_or_404(product_id)
    files = request.files.getlist("images")
    if not files:
        flash("Выберите файлы.", "warning")
        return redirect(url_for("admin.product_edit", product_id=product_id))
    try:
        created, err = save_product_images(product_id, files)
        if err:
            flash(err, "danger")
        elif created:
            flash(f"Загружено изображений: {created}.", "success")
        else:
            flash("Нет подходящих файлов (разрешены jpg, png, webp).", "warning")
    except Exception as e:
        flash(f"Ошибка загрузки: {e}", "danger")
    return redirect(url_for("admin.product_edit", product_id=product_id))


@admin_bp.route("/products/<int:product_id>/images/<int:image_id>/set_main", methods=["POST"])
@admin_required
def product_image_set_main(product_id, image_id):
    ok, err = set_main_image(product_id, image_id)
    if err:
        flash(err, "danger")
    else:
        flash("Главное фото обновлено.", "success")
    return redirect(url_for("admin.product_edit", product_id=product_id))


@admin_bp.route("/products/<int:product_id>/images/<int:image_id>/delete", methods=["POST"])
@admin_required
def product_image_delete(product_id, image_id):
    ok, err = delete_product_image(image_id)
    if err:
        flash(err, "danger")
    else:
        flash("Изображение удалено.", "success")
    return redirect(url_for("admin.product_edit", product_id=product_id))


@admin_bp.route("/products/<int:product_id>/images/reorder", methods=["POST"])
@admin_required
def product_images_reorder(product_id):
    order_list = []
    for key, value in request.form.items():
        if key.startswith("sort_") and value.isdigit():
            try:
                img_id = int(key.replace("sort_", ""))
                order_list.append((img_id, int(value)))
            except ValueError:
                pass
    if order_list:
        reorder_images(product_id, order_list)
        flash("Порядок фото обновлён.", "success")
    return redirect(url_for("admin.product_edit", product_id=product_id))


@admin_bp.route("/orders")
@admin_required
def orders():
    page = request.args.get("page", 1, type=int)
    pagination = Order.query.order_by(Order.created_at.desc()).paginate(page=page, per_page=20)
    return render_template("admin/orders.html", pagination=pagination)


@admin_bp.route("/orders/<int:order_id>")
@admin_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template("admin/order_detail.html", order=order)


@admin_bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status", "").strip()
    if new_status == order.status:
        return redirect(url_for("admin.order_detail", order_id=order_id))
    if new_status in ADMIN_SELECTABLE_STATUSES:
        order.status = new_status
        db.session.commit()
        flash("Статус заказа обновлён.", "success")
    else:
        flash("Недопустимый статус заказа.", "warning")
    return redirect(url_for("admin.order_detail", order_id=order_id))


@admin_bp.route("/corporate")
@admin_required
def corporate_requests():
    requests_list = CorporateRequest.query.order_by(CorporateRequest.created_at.desc()).all()
    return render_template("admin/corporate_requests.html", requests=requests_list)


@admin_bp.route("/corporate/<int:req_id>/status", methods=["POST"])
@admin_required
def corporate_request_status(req_id):
    req = CorporateRequest.query.get_or_404(req_id)
    new_status = request.form.get("status", "").strip()
    if new_status not in CORPORATE_REQUEST_STATUSES:
        flash("Недопустимый статус заявки.", "warning")
        return redirect(url_for("admin.corporate_requests"))
    req.status = new_status
    db.session.commit()
    flash("Статус заявки обновлён.", "success")
    return redirect(url_for("admin.corporate_requests"))


@admin_bp.route("/import/csv", methods=["GET", "POST"])
@admin_required
def import_csv():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Выберите файл CSV.", "danger")
            return redirect(url_for("admin.import_csv"))
        try:
            log, result = run_csv_import(file.stream)
            flash(
                f"Импорт завершён: создано {result.created_count}, обновлено {result.updated_count}, ошибок {result.error_count}.",
                "success" if result.error_count == 0 else "warning",
            )
        except Exception as e:
            flash(f"Ошибка импорта: {e}", "danger")
        return redirect(url_for("admin.import_csv"))
    logs = ImportLog.query.filter_by(type="csv").order_by(ImportLog.created_at.desc()).limit(20).all()
    return render_template("admin/import_csv.html", logs=logs)
