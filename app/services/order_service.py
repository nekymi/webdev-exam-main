from decimal import Decimal

from flask import url_for
from sqlalchemy import func

from app import db
from app.models import Order, OrderItem, Payment, Product
from app.providers.payments.stub import StubPaymentProvider


def attach_guest_orders_to_user(user_id, user_email=None):
    """
    Переносит на аккаунт гостевые заказы: из session['guest_order_ids'] и
    (при user_email) заказы с тем же guest_email. Вызывать после login/register.
    """
    from flask import session

    attached = 0
    seen = set()
    for oid in list(session.get("guest_order_ids") or []):
        o = db.session.get(Order, oid)
        if o and o.user_id is None and o.id not in seen:
            o.user_id = user_id
            seen.add(o.id)
            attached += 1
    if user_email:
        em = (user_email or "").strip().lower()
        if em:
            for o in (
                Order.query.filter(
                    Order.user_id.is_(None),
                    func.lower(Order.guest_email) == em,
                )
                .all()
            ):
                if o.id not in seen:
                    o.user_id = user_id
                    seen.add(o.id)
                    attached += 1
    if attached:
        db.session.commit()
    session.pop("guest_order_ids", None)
    session.modified = True
    return attached


def create_order_from_cart_items(
    user_id,
    cart_items_with_totals,
    contact_name,
    phone,
    address=None,
    delivery_method=None,
    comment=None,
    pay_online=False,
    guest_email=None,
):
    """cart_items_with_totals: list of dicts with product, qty, line_total.
    user_id=None - гостевой заказ (оформление без регистрации).
    pay_online=True: заказ с онлайн-оплатой (заглушка) - статус AWAITING_PAYMENT.
    pay_online=False: оплата при получении - статус NEW.
    """
    if not cart_items_with_totals:
        raise ValueError("нельзя создать заказ с пустой корзиной")
    checked_items = []
    total = Decimal("0.00")
    for item in cart_items_with_totals:
        product_id = getattr(item.get("product"), "id", None)
        try:
            qty = int(item.get("qty") or 0)
        except (TypeError, ValueError):
            qty = 0
        product = db.session.get(Product, product_id) if product_id else None
        if not product or not product.is_active:
            raise ValueError("в корзине есть недоступный товар")
        if qty <= 0:
            raise ValueError("некорректное количество товара")
        if int(product.stock_qty or 0) < qty:
            raise ValueError(f"товара «{product.name}» недостаточно на складе")
        line_total = Decimal(product.price) * qty
        total += line_total
        checked_items.append({"product": product, "qty": qty})
    initial_status = "AWAITING_PAYMENT" if pay_online else "NEW"
    ge = (guest_email or "").strip() or None
    if ge:
        ge = ge.lower()
    order = Order(
        user_id=user_id,
        guest_email=ge,
        status=initial_status,
        total_amount=total,
        contact_name=contact_name,
        phone=phone,
        address=address,
        delivery_method=delivery_method,
        comment=comment,
    )
    db.session.add(order)
    db.session.flush()

    for item in checked_items:
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=item["product"].id,
                qty=item["qty"],
                price_snapshot=item["product"].price,
            )
        )

    db.session.commit()
    return order


def create_payment_for_order(order, provider=None):
    if provider is None:
        provider = StubPaymentProvider()
    payment = Payment(
        order_id=order.id,
        provider=provider.name,
        status="PENDING",
        amount=order.total_amount,
        payment_url=None,
        external_id=None,
    )
    db.session.add(payment)
    db.session.flush()

    if provider.name == "stub":
        payment.payment_url = url_for("orders.stub_payment_page", payment_id=payment.id, _external=True)
    else:
        ext_id, pay_url = provider.create_payment(
            order_id=order.id,
            amount=order.total_amount,
            success_url=url_for("orders.payment_success", _external=True),
            cancel_url=url_for("orders.payment_cancel", _external=True),
        )
        payment.external_id = ext_id or None
        payment.payment_url = pay_url

    db.session.commit()
    return payment


def confirm_stub_payment(payment_id):
    payment = db.session.get(Payment, payment_id)
    if not payment or payment.provider != "stub":
        return None, "Платёж не найден или не заглушка"
    if payment.status == "PAID":
        return payment.order, None
    payment.status = "PAID"
    # заказ оплачен (тестовая заглушка); дальше обработка и отгрузка вручную в админке
    payment.order.status = "PAID"
    db.session.commit()
    return payment.order, None


def get_payment_by_id(payment_id):
    return db.session.get(Payment, payment_id)


def get_orders_for_user(user_id):
    return Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
