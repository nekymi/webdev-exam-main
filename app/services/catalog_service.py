from app.models import Category, Product


def get_categories_ordered():
    return Category.query.order_by(Category.name).all()


def get_products_paginated(page=1, per_page=12, category_id=None, search=None):
    query = Product.query.filter(Product.is_active == True)
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if search and search.strip():
        query = query.filter(Product.name.ilike(f"%{search.strip()}%"))
    query = query.order_by(Product.updated_at.desc())
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total


def get_product_by_id(product_id):
    return Product.query.filter_by(id=product_id, is_active=True).first()
