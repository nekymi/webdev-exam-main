from flask import abort, flash, redirect, render_template, request, url_for, jsonify

from app.main import main_bp
from app.services.catalog_service import (
    get_categories_ordered,
    get_product_by_id,
    get_products_paginated,
)
from app.services.corporate_service import create_corporate_request


@main_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    per_page = 12
    category_id = request.args.get("category", type=int)
    search = request.args.get("search", "").strip() or None
    products, total = get_products_paginated(page=page, per_page=per_page, category_id=category_id, search=search)
    total_pages = max((total + per_page - 1) // per_page, 1)
    categories = get_categories_ordered()
    return render_template(
        "main/index.html",
        products=products,
        categories=categories,
        page=page,
        total_pages=total_pages,
        current_category=category_id,
        search=search or "",
    )


@main_bp.route("/api/products")
def api_products():
    """JSON: список товаров с пагинацией и фильтрами (query, category, page)."""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 12, type=int)
    per_page = min(max(per_page, 1), 48)
    category_id = request.args.get("category", type=int)
    search = request.args.get("query", request.args.get("search", ""), type=str).strip() or None
    products, total = get_products_paginated(page=page, per_page=per_page, category_id=category_id, search=search)
    total_pages = max((total + per_page - 1) // per_page, 1)
    items = []
    for p in products:
        img = p.main_image_path_or_url
        if img and img.startswith("http"):
            image_url = img
        elif img:
            image_url = url_for("static", filename=img)
        else:
            image_url = url_for("static", filename="img/placeholder-product.svg")
        items.append({
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "summary": p.text_for_catalog,
            "category_name": p.category.name if p.category else None,
            "url": url_for("main.product_detail", product_id=p.id, _external=False),
            "image": image_url,
            "stock_qty": getattr(p, "stock_qty", None),
        })
    return jsonify({"items": items, "page": page, "pages": total_pages, "total": total})


@main_bp.route("/product/<int:product_id>")
def product_detail(product_id):
    product = get_product_by_id(product_id)
    if not product:
        abort(404)
    return render_template("main/product_detail.html", product=product)


@main_bp.route("/contacts")
def contacts():
    return render_template("main/contacts.html")


@main_bp.route("/about")
def about():
    """о компании: адаптированный текст с публичного сайта «берегиня алтая» (altayber.ru)."""
    return render_template("main/about.html")


@main_bp.route("/corporate", methods=["GET", "POST"])
def corporate():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        message = request.form.get("message", "").strip()
        if not name:
            flash("Укажите имя или название организации.", "danger")
            return redirect(url_for("main.corporate"))
        create_corporate_request(name=name, phone=phone, email=email, message=message)
        flash("Заявка отправлена. Мы свяжемся с вами.", "success")
        return redirect(url_for("main.corporate"))
    return render_template("main/corporate.html")
