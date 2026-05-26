from flask import flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app import db
from app.models import CartItem, Order
from app.orders import orders_bp
from app.services.cart_service import (
    get_cart_items_and_total,
    get_or_create_cart,
    line_items_and_total_from_session_cart,
)
from app.services.order_service import (
    confirm_stub_payment,
    create_order_from_cart_items,
    create_payment_for_order,
    get_orders_for_user,
    get_payment_by_id,
)


def _guest_order_ids():
    ids = session.get("guest_order_ids")
    if not isinstance(ids, list):
        return []
    return ids


def _remember_guest_order(order_id):
    ids = _guest_order_ids()
    if order_id not in ids:
        ids.append(order_id)
    session["guest_order_ids"] = ids
    session.modified = True


def _clear_guest_pending_payment():
    session.pop("guest_pending_payment_order_id", None)
    session.modified = True


def _can_view_order(order):
    if order.user_id is not None:
        return current_user.is_authenticated and current_user.id == order.user_id
    return order.id in _guest_order_ids()


def _cart_items_for_checkout():
    if current_user.is_authenticated:
        cart = get_or_create_cart(current_user.id)
        items, total = get_cart_items_and_total(cart)
        out = []
        for x in items:
            out.append({"product": x["product"], "qty": x["qty"], "line_total": x["line_total"]})
        return out, total
    raw, total = line_items_and_total_from_session_cart(session.get("cart") or {})
    return list(raw), total


def _redirect_after_confirmed_payment(order):
    """После успешной оплаты заглушки."""
    if order.user_id is not None:
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=url_for("orders.order_list")))
        flash("Оплата успешно проведена (тестовый режим).", "success")
        return redirect(url_for("orders.order_list"))
    _clear_guest_pending_payment()
    _remember_guest_order(order.id)
    flash("Оплата успешно проведена (тестовый режим).", "success")
    return redirect(url_for("orders.order_complete", order_id=order.id))


@orders_bp.route("")
@login_required
def order_list():
    orders = get_orders_for_user(current_user.id)
    return render_template("orders/orders.html", orders=orders)


@orders_bp.route("/complete/<int:order_id>")
def order_complete(order_id):
    """просмотр заказа после оформления: для гостя только из этой сессии, для пользователя свой заказ."""
    order = Order.query.get_or_404(order_id)
    if not _can_view_order(order):
        flash("Заказ не найден или доступ запрещён.", "danger")
        return redirect(url_for("main.index"))
    return render_template("orders/order_complete.html", order=order)


@orders_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = _cart_items_for_checkout()
    if not items:
        flash("Корзина пуста.", "warning")
        return redirect(url_for("main.index"))

    is_guest = not current_user.is_authenticated

    if request.method == "POST":
        contact_name = request.form.get("contact_name", "").strip()
        phone = request.form.get("phone", "").strip()
        guest_email = request.form.get("guest_email", "").strip() or None
        address = request.form.get("address", "").strip()
        delivery_method = request.form.get("delivery_method", "").strip() or None
        comment = request.form.get("comment", "").strip() or None
        pay_online = request.form.get("pay_online") == "1"

        if not contact_name or not phone:
            flash("Укажите имя и телефон.", "danger")
            return redirect(url_for("orders.checkout"))
        if len(contact_name) > 255 or len(phone) > 50:
            flash("Проверьте длину имени и телефона.", "danger")
            return redirect(url_for("orders.checkout"))

        uid = None if is_guest else current_user.id

        try:
            order = create_order_from_cart_items(
                user_id=uid,
                cart_items_with_totals=items,
                contact_name=contact_name,
                phone=phone,
                address=address or None,
                delivery_method=delivery_method,
                comment=comment,
                pay_online=pay_online,
                guest_email=guest_email if is_guest else None,
            )
        except ValueError as e:
            db.session.rollback()
            flash(str(e), "danger")
            return redirect(url_for("cart.view_cart"))

        if is_guest:
            session["cart"] = {}
            session.modified = True
            _remember_guest_order(order.id)
            if pay_online:
                session["guest_pending_payment_order_id"] = order.id
                session.modified = True
        else:
            cart = get_or_create_cart(current_user.id)
            CartItem.query.filter_by(cart_id=cart.id).delete()
            db.session.commit()

        if pay_online:
            payment = create_payment_for_order(order)
            target = payment.payment_url or url_for("orders.order_complete", order_id=order.id)
            return redirect(target)

        flash("Заказ оформлен. Ожидает обработки.", "success")
        return redirect(url_for("orders.order_complete", order_id=order.id))

    return render_template(
        "orders/checkout.html",
        items=items,
        total=total,
        checkout_is_guest=is_guest,
    )


@orders_bp.route("/payments/stub/<int:payment_id>", methods=["GET", "POST"])
def stub_payment_page(payment_id):
    payment = get_payment_by_id(payment_id)
    if not payment or payment.provider != "stub":
        flash("Платёж не найден.", "danger")
        return redirect(url_for("main.index"))

    order = payment.order

    if order.user_id is not None:
        if not current_user.is_authenticated or current_user.id != order.user_id:
            flash("Войдите, чтобы оплатить заказ.", "warning")
            return redirect(url_for("auth.login", next=request.path))
    else:
        pending = session.get("guest_pending_payment_order_id")
        allowed_ids = _guest_order_ids()
        if pending != order.id and order.id not in allowed_ids:
            flash("Ссылка на оплату недействительна или устарела.", "danger")
            return redirect(url_for("main.index"))

    if payment.status == "PAID":
        flash("Оплата уже проведена.", "info")
        if not _can_view_order(order):
            return redirect(url_for("main.index"))
        return redirect(url_for("orders.order_complete", order_id=order.id))

    if request.method == "POST":
        order_after, err = confirm_stub_payment(payment_id)
        if err:
            flash(err, "danger")
        else:
            return _redirect_after_confirmed_payment(order_after)

    return render_template("orders/stub_payment.html", payment=payment)


@orders_bp.route("/payments/success")
def payment_success():
    flash("Оплата прошла успешно.", "success")
    if current_user.is_authenticated:
        return redirect(url_for("orders.order_list"))
    return redirect(url_for("main.index"))


@orders_bp.route("/payments/cancel")
def payment_cancel():
    flash("Оплата отменена.", "info")
    if current_user.is_authenticated:
        return redirect(url_for("orders.order_list"))
    return redirect(url_for("main.index"))
