import io
import os
import unittest
from decimal import Decimal


os.environ["SECRET_KEY"] = "test-secret-key-1234567890"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app import create_app, db
from app.models import Category, Order, Payment, Product, Role, User
from app.services.cart_service import add_to_cart, get_cart_count_and_total, get_or_create_cart
from app.services.catalog_sync_service import run_csv_import
from app.services.order_service import confirm_stub_payment, create_order_from_cart_items, create_payment_for_order


class ProjectServicesTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        )
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        admin_role = Role(name="Администратор")
        customer_role = Role(name="Покупатель")
        db.session.add_all([admin_role, customer_role])
        db.session.flush()

        self.user = User(
            email="user@example.com",
            first_name="Тест",
            last_name="Пользователь",
            role=customer_role,
        )
        self.user.set_password("password123")

        self.category = Category(name="Мед", slug="med")
        self.product = Product(
            sku="MED-TEST-001",
            name="Алтайский мед",
            price=Decimal("250.00"),
            stock_qty=15,
            category=self.category,
            is_active=True,
        )
        db.session.add_all([self.user, self.category, self.product])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_add_to_cart_creates_item_and_updates_totals(self):
        cart = get_or_create_cart(self.user.id)

        item, err, warn = add_to_cart(cart.id, self.product.id, 2)

        self.assertIsNone(err)
        self.assertIsNone(warn)
        self.assertIsNotNone(item)
        count, total = get_cart_count_and_total(cart)
        self.assertEqual(count, 2)
        self.assertEqual(total, Decimal("500.00"))

    def test_add_to_cart_caps_quantity_to_stock(self):
        cart = get_or_create_cart(self.user.id)
        item, err, warn = add_to_cart(cart.id, self.product.id, 100)
        self.assertIsNone(err)
        self.assertIsNotNone(warn)
        self.assertEqual(item.qty, 15)
        count, total = get_cart_count_and_total(cart)
        self.assertEqual(count, 15)

    def test_add_to_cart_invalid_qty_falls_back_to_one(self):
        cart = get_or_create_cart(self.user.id)
        item, err, warn = add_to_cart(cart.id, self.product.id, None)
        self.assertIsNone(err)
        self.assertIsNotNone(item)
        self.assertEqual(item.qty, 1)

    def test_create_order_from_cart_items_calculates_total_and_items(self):
        cart_items_with_totals = [
            {
                "product": self.product,
                "qty": 3,
                "line_total": Decimal("750.00"),
            }
        ]

        order = create_order_from_cart_items(
            user_id=self.user.id,
            cart_items_with_totals=cart_items_with_totals,
            contact_name="Иван Иванов",
            phone="+79990000000",
            address="Санкт-Петербург",
        )

        self.assertEqual(order.status, "NEW")
        self.assertEqual(order.total_amount, Decimal("750.00"))
        self.assertEqual(order.items.count(), 1)

    def test_create_order_from_cart_pay_online_sets_awaiting_payment(self):
        cart_items_with_totals = [
            {
                "product": self.product,
                "qty": 1,
                "line_total": Decimal("250.00"),
            }
        ]

        order = create_order_from_cart_items(
            user_id=self.user.id,
            cart_items_with_totals=cart_items_with_totals,
            contact_name="Иван Иванов",
            phone="+79990000000",
            pay_online=True,
        )

        self.assertEqual(order.status, "AWAITING_PAYMENT")

    def test_guest_order_user_id_null_and_guest_email(self):
        order = create_order_from_cart_items(
            user_id=None,
            cart_items_with_totals=[
                {
                    "product": self.product,
                    "qty": 1,
                    "line_total": Decimal("250.00"),
                }
            ],
            contact_name="Гость Тест",
            phone="+79991112233",
            guest_email="guest@example.com",
        )
        self.assertIsNone(order.user_id)
        self.assertEqual(order.guest_email, "guest@example.com")
        self.assertEqual(order.status, "NEW")
        loaded = db.session.get(Order, order.id)
        self.assertIsNone(loaded.user_id)

    def test_confirm_stub_payment_marks_payment_and_order_as_paid(self):
        order = create_order_from_cart_items(
            user_id=self.user.id,
            cart_items_with_totals=[
                {
                    "product": self.product,
                    "qty": 1,
                    "line_total": Decimal("250.00"),
                }
            ],
            contact_name="Иван Иванов",
            phone="+79990000000",
            pay_online=True,
        )

        with self.app.test_request_context():
            payment = create_payment_for_order(order)

        confirmed_order, err = confirm_stub_payment(payment.id)
        refreshed_payment = db.session.get(Payment, payment.id)

        self.assertIsNone(err)
        self.assertEqual(confirmed_order.status, "PAID")
        self.assertEqual(refreshed_payment.status, "PAID")

    def test_run_csv_import_creates_and_updates_products(self):
        csv_content = (
            "sku;name;description;price;stock_qty;category_name;external_id;is_active\n"
            "MED-CSV-001;Мед цветочный;Описание;300;7;Мед;ext-1;1\n"
            "MED-TEST-001;Алтайский мед обновленный;Новое описание;275;20;Мед;ext-2;1\n"
        )

        log, result = run_csv_import(io.BytesIO(csv_content.encode("utf-8")))

        created_product = Product.query.filter_by(sku="MED-CSV-001").first()
        updated_product = Product.query.filter_by(sku="MED-TEST-001").first()

        self.assertEqual(result.created_count, 1)
        self.assertEqual(result.updated_count, 1)
        self.assertEqual(result.error_count, 0)
        self.assertIsNotNone(log)
        self.assertIsNotNone(created_product)
        self.assertEqual(updated_product.name, "Алтайский мед обновленный")
        self.assertEqual(updated_product.price, Decimal("275.00"))


if __name__ == "__main__":
    unittest.main()
