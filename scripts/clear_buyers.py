"""
Удаляет покупателей (всех пользователей без роли «Администратор»), их корзины,
связанные заказы (по умолчанию и гостевые), платежи и позиции заказов,
а также все заявки corporate_requests.

Роли, администраторов, каталог и import_logs не трогает.

  python scripts/clear_buyers.py --yes
  python scripts/clear_buyers.py --yes --keep-guest-orders
"""
from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

_this_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.dirname(_this_dir)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

load_dotenv(os.path.join(_repo_root, ".env"))
load_dotenv()

from sqlalchemy import or_  # noqa: E402

from app import create_app, db  # noqa: E402
from app.models import Cart, CorporateRequest, Order, OrderItem, Payment, User  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Очистка покупателей, заказов и корп. заявок.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Подтвердить необратимое удаление данных (обязательно).",
    )
    parser.add_argument(
        "--keep-guest-orders",
        action="store_true",
        help="Не удалять гостевые заказы (user_id IS NULL).",
    )
    args = parser.parse_args()

    if not args.yes:
        print("Укажите --yes для выполнения. См. python scripts/clear_buyers.py --help", file=sys.stderr)
        return 2

    app = create_app()
    with app.app_context():
        customer_ids = [u.id for u in User.query.all() if not u.is_admin]

        conds = []
        if not args.keep_guest_orders:
            conds.append(Order.user_id.is_(None))
        if customer_ids:
            conds.append(Order.user_id.in_(customer_ids))

        if conds:
            order_ids = [o.id for o in Order.query.filter(or_(*conds)).all()]
        else:
            order_ids = []

        n_corp = CorporateRequest.query.delete(synchronize_session=False)

        n_pay = n_items = n_orders = 0
        if order_ids:
            n_pay = Payment.query.filter(Payment.order_id.in_(order_ids)).delete(synchronize_session=False)
            n_items = OrderItem.query.filter(OrderItem.order_id.in_(order_ids)).delete(synchronize_session=False)
            n_orders = Order.query.filter(Order.id.in_(order_ids)).delete(synchronize_session=False)

        n_carts = 0
        if customer_ids:
            carts = Cart.query.filter(Cart.user_id.in_(customer_ids)).all()
            n_carts = len(carts)
            for cart in carts:
                db.session.delete(cart)

        n_users = 0
        for uid in customer_ids:
            u = db.session.get(User, uid)
            if u:
                db.session.delete(u)
                n_users += 1

        db.session.commit()

        print(
            "Готово:",
            f"corporate_requests={n_corp},",
            f"payments={n_pay},",
            f"order_items={n_items},",
            f"orders={n_orders},",
            f"carts={n_carts},",
            f"users(покупатели)={n_users}.",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
