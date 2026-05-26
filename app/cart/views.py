from flask import flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user

from app.cart import cart_bp
from app.models import Product
from app.services.cart_service import (
    add_to_cart,
    get_cart_count_and_total,
    get_cart_items_and_total,
    get_or_create_cart,
    line_items_and_total_from_session_cart,
    remove_from_cart,
    update_cart_item,
)


def _session_cart():
    return session.setdefault("cart", {})


def _flash_add_result(err, warn):
    """выводит flash после попытки добавить товар в корзину."""
    if err:
        flash(err, "danger")
    else:
        flash("Товар добавлен в корзину.", "success")
        if warn:
            flash(warn, "warning")


def _session_add_product(product_id, qty_add):
    """Гостевая корзина: добавить qty_add с учётом остатка. Возвращает (ok, err, warning)."""
    product = Product.query.filter_by(id=product_id, is_active=True).first()
    if not product:
        return False, "Товар не найден", None
    stock = int(product.stock_qty or 0)
    if stock <= 0:
        return False, "Товар не в наличии", None
    data = _session_cart()
    try:
        current = int(data.get(str(product_id), 0))
    except (TypeError, ValueError):
        current = 0
    try:
        add_n = int(qty_add)
    except (TypeError, ValueError):
        add_n = 1
    add_n = max(1, min(add_n, 999))
    requested = current + add_n
    final = min(requested, stock, 999)
    warning = None
    if final < requested:
        warning = f"В наличии только {stock} шт. Количество ограничено остатком."
    data[str(product_id)] = final
    session.modified = True
    return True, None, warning


def _session_cart_totals():
    return line_items_and_total_from_session_cart(_session_cart())


def _get_cart_items_and_total():
    if current_user.is_authenticated:
        cart = get_or_create_cart(current_user.id)
        return get_cart_items_and_total(cart)
    return _session_cart_totals()


def _get_cart_count_and_total():
    """(count, total) для текущего пользователя или сессии."""
    if current_user.is_authenticated:
        cart = get_or_create_cart(current_user.id)
        return get_cart_count_and_total(cart)
    items, total = _session_cart_totals()
    count = sum(item["qty"] for item in items)
    return count, total


def _json_cart_state(warnings):
    items, total = _get_cart_items_and_total()
    lines = []
    for it in items:
        p = it["product"]
        lines.append(
            {
                "product_id": p.id,
                "qty": it["qty"],
                "line_total": float(it["line_total"]),
                "unit_price": float(p.price),
                "max_qty": min(max(int(p.stock_qty or 0), 0), 999),
            }
        )
    count, _ = _get_cart_count_and_total()
    return {
        "ok": True,
        "lines": lines,
        "cart_total": float(total),
        "cart_count": int(count),
        "line_count": len(lines),
        "warnings": list(warnings) if warnings else [],
    }


@cart_bp.route("")
def view_cart():
    items, total = _get_cart_items_and_total()
    total_qty = sum(int(i["qty"]) for i in items) if items else 0
    return render_template(
        "cart/cart.html", items=items, total=total, total_qty=total_qty
    )


@cart_bp.route("/add/<int:product_id>", methods=["POST"])
def add(product_id):
    qty = request.form.get("quantity", default=1, type=int)
    if qty is None or qty < 1:
        qty = 1
    qty = min(qty, 999)
    if current_user.is_authenticated:
        cart = get_or_create_cart(current_user.id)
        _, err, warn = add_to_cart(cart.id, product_id, qty)
    else:
        _, err, warn = _session_add_product(product_id, qty)
    _flash_add_result(err, warn)
    return redirect(request.referrer or url_for("cart.view_cart"))


@cart_bp.route("/update", methods=["POST"])
def update():
    warnings = []
    if current_user.is_authenticated:
        cart = get_or_create_cart(current_user.id)
        for key, value in request.form.items():
            if key.startswith("qty_"):
                product_id = key.replace("qty_", "")
                try:
                    product_id = int(product_id)
                    _, warn = update_cart_item(cart.id, product_id, int(value))
                    if warn:
                        warnings.append(warn)
                except (ValueError, TypeError):
                    pass
    else:
        data = _session_cart()
        for key, value in request.form.items():
            if key.startswith("qty_"):
                pid = key.replace("qty_", "")
                try:
                    qty = max(0, int(value)) if value else 0
                except (ValueError, TypeError):
                    continue
                if qty == 0:
                    data.pop(pid, None)
                else:
                    product = Product.query.filter_by(id=int(pid), is_active=True).first()
                    if not product:
                        data.pop(pid, None)
                        continue
                    stock = int(product.stock_qty or 0)
                    if stock <= 0:
                        data.pop(pid, None)
                        warnings.append("Товар снят с продажи — позиция удалена из корзины.")
                        continue
                    capped = min(qty, stock, 999)
                    if capped < qty:
                        warnings.append(f"В наличии только {stock} шт.")
                    data[pid] = capped
        session.modified = True
    for w in warnings:
        flash(w, "warning")
    flash("Корзина обновлена.", "success")
    return redirect(url_for("cart.view_cart"))


@cart_bp.route("/api/line", methods=["POST"])
def api_set_line():
    """json: post { product_id, qty }. устанавливает количество (0 убирает позицию)."""
    data = request.get_json(force=True, silent=True) or {}
    product_id = data.get("product_id")
    qty = data.get("qty", 0)
    try:
        product_id = int(product_id)
        qty = int(qty)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Некорректные данные"}), 400
    if qty < 0 or qty > 999:
        return jsonify({"ok": False, "message": "Количество вне допустимого диапазона"}), 400

    warnings = []

    if qty == 0:
        if current_user.is_authenticated:
            cart = get_or_create_cart(current_user.id)
            remove_from_cart(cart.id, product_id)
        else:
            _session_cart().pop(str(product_id), None)
            session.modified = True
        return jsonify(_json_cart_state(warnings))

    if current_user.is_authenticated:
        cart = get_or_create_cart(current_user.id)
        ok, warn = update_cart_item(cart.id, product_id, qty)
        if not ok:
            return jsonify({"ok": False, "message": "Позиция не найдена в корзине"}), 400
        if warn:
            warnings.append(warn)
    else:
        sdata = _session_cart()
        product = Product.query.filter_by(id=product_id, is_active=True).first()
        if not product:
            return jsonify({"ok": False, "message": "Товар не найден"}), 400
        str_pid = str(product_id)
        if str_pid not in sdata:
            return jsonify({"ok": False, "message": "Позиция не найдена в корзине"}), 400
        stock = int(product.stock_qty or 0)
        if stock <= 0:
            sdata.pop(str_pid, None)
            session.modified = True
            warnings.append("Товар снят с продажи — позиция удалена из корзины.")
            return jsonify(_json_cart_state(warnings))
        capped = min(qty, stock, 999)
        if capped < qty:
            warnings.append(f"В наличии только {stock} шт.")
        sdata[str_pid] = capped
        session.modified = True

    return jsonify(_json_cart_state(warnings))


@cart_bp.route("/api/add", methods=["POST"])
def api_add():
    """JSON API: POST { product_id, qty } -> { ok, cart_count, cart_total, message }."""
    data = request.get_json(force=True, silent=True) or {}
    product_id = data.get("product_id")
    qty = data.get("qty", 1)
    try:
        product_id = int(product_id)
        qty = max(1, min(int(qty), 999))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Некорректные данные"}), 400
    if current_user.is_authenticated:
        cart = get_or_create_cart(current_user.id)
        _, err, warn = add_to_cart(cart.id, product_id, qty)
        if err:
            return jsonify({"ok": False, "message": err}), 400
        msg = "Товар добавлен в корзину."
        if warn:
            msg = warn
        count, total = _get_cart_count_and_total()
        return jsonify(
            {
                "ok": True,
                "cart_count": count,
                "cart_total": float(total),
                "message": msg,
            }
        )
    ok, err, warn = _session_add_product(product_id, qty)
    if not ok:
        return jsonify({"ok": False, "message": err}), 400
    count, total = _get_cart_count_and_total()
    msg = warn or "Товар добавлен в корзину."
    return jsonify(
        {
            "ok": True,
            "cart_count": count,
            "cart_total": float(total),
            "message": msg,
        }
    )


@cart_bp.route("/remove/<int:product_id>", methods=["POST"])
def remove(product_id):
    if current_user.is_authenticated:
        cart = get_or_create_cart(current_user.id)
        remove_from_cart(cart.id, product_id)
    else:
        _session_cart().pop(str(product_id), None)
        session.modified = True
    flash("Товар удалён из корзины.", "warning")
    return redirect(url_for("cart.view_cart"))
