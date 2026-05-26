from decimal import Decimal

from app import db
from app.models import Cart, CartItem, Product


def _coerce_add_qty(qty, cap=999):
    """количество для добавления в корзину: целое, от 1 до cap."""
    try:
        q = int(qty)
    except (TypeError, ValueError):
        q = 1
    return max(1, min(q, cap))


def get_or_create_cart(user_id):
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    return cart


def get_cart_items_and_total(cart):
    items = []
    total = Decimal("0.00")
    for item in cart.items:
        if not item.product or not item.product.is_active:
            continue
        line_total = Decimal(item.price_snapshot) * item.qty
        total += line_total
        items.append({
            "cart_item": item,
            "product": item.product,
            "qty": item.qty,
            "line_total": line_total,
        })
    return items, total


def add_to_cart(cart_id, product_id, qty=1):
    """Добавляет товар в корзину. Возвращает (item|None, error|None, warning|None)."""
    product = Product.query.filter_by(id=product_id, is_active=True).first()
    if not product:
        return None, "Товар не найден", None
    cart = db.session.get(Cart, cart_id)
    if not cart:
        return None, "Корзина не найдена", None
    stock = int(product.stock_qty or 0)
    if stock <= 0:
        return None, "Товар не в наличии", None

    qty_add = _coerce_add_qty(qty)
    item = CartItem.query.filter_by(cart_id=cart_id, product_id=product_id).first()
    current = item.qty if item else 0
    requested_total = current + qty_add
    max_allowed = min(stock, 999)
    final_qty = min(requested_total, max_allowed)

    warning = None
    if final_qty < requested_total:
        warning = f"В наличии только {stock} шт. Количество ограничено остатком."

    if item:
        item.qty = final_qty
        item.price_snapshot = product.price
    else:
        item = CartItem(
            cart_id=cart_id,
            product_id=product_id,
            qty=final_qty,
            price_snapshot=product.price,
        )
        db.session.add(item)
    db.session.commit()
    return item, None, warning


def update_cart_item(cart_id, product_id, qty):
    item = CartItem.query.filter_by(cart_id=cart_id, product_id=product_id).first()
    if not item:
        return False, None
    qty = max(0, int(qty))
    if qty == 0:
        db.session.delete(item)
        db.session.commit()
        return True, None
    product = item.product
    stock = int(product.stock_qty or 0) if product else 0
    if stock <= 0:
        db.session.delete(item)
        db.session.commit()
        return True, "Товар снят с продажи — позиция удалена из корзины."
    capped = min(qty, stock, 999)
    item.qty = capped
    item.price_snapshot = product.price
    db.session.commit()
    warning = None
    if capped < qty:
        warning = f"В наличии только {stock} шт."
    return True, warning


def remove_from_cart(cart_id, product_id):
    item = CartItem.query.filter_by(cart_id=cart_id, product_id=product_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
        return True
    return False


def get_cart_count_and_total(cart):
    """Возвращает (количество позиций в корзине, итоговая сумма)."""
    items, total = get_cart_items_and_total(cart)
    count = sum(item["qty"] for item in items)
    return count, total


def line_items_and_total_from_session_cart(session_cart):
    """Гостевая корзина из session['cart']: список позиций для checkout и итог."""
    items = []
    total = Decimal("0.00")
    if not session_cart:
        return items, total
    for product_id, qty in session_cart.items():
        try:
            pid = int(product_id)
        except (TypeError, ValueError):
            continue
        product = Product.query.filter_by(id=pid, is_active=True).first()
        if not product:
            continue
        try:
            q = max(1, min(int(qty), 999))
        except (TypeError, ValueError):
            continue
        q = min(q, int(product.stock_qty or 0))
        if q <= 0:
            continue
        line_total = Decimal(product.price) * q
        total += line_total
        items.append({"product": product, "qty": q, "line_total": line_total})
    return items, total


def get_cart_stats_for_user_or_session(user_id=None, session_cart=None):
    """(count, total) для шаблонов/API. user_id если авторизован, иначе session_cart (dict)."""
    if user_id is not None:
        cart = get_or_create_cart(user_id)
        return get_cart_count_and_total(cart)
    if session_cart:
        count = 0
        total = Decimal("0.00")
        for pid, qty in session_cart.items():
            try:
                p = Product.query.filter_by(id=int(pid), is_active=True).first()
                q = max(1, min(int(qty), 999))
                if p:
                    q = min(q, int(p.stock_qty or 0))
                    if q > 0:
                        count += q
                        total += Decimal(p.price) * q
            except (ValueError, TypeError):
                pass
        return count, total
    return 0, Decimal("0.00")
