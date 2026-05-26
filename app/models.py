# модели интернет-магазина
from datetime import datetime
import json

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"{self.name}"


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=True)
    role = db.relationship("Role", backref="users")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role and self.role.name == "Администратор"

    def __repr__(self):
        return f"<User {self.email}>"


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    # чпу-идентификатор для ссылок и импорта (altayskiy-med); на сайте в фильтре пока id.
    # можно оставить пустым: в каталоге используется category_id.
    slug = db.Column(db.String(255), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=True)
    products = db.relationship("Product", backref="category", lazy="dynamic")

    def __repr__(self):
        return self.name


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(100), unique=True, nullable=False)
    external_id = db.Column(db.String(100), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock_qty = db.Column(db.Integer, default=0, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)  # legacy / запасной путь
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    images = db.relationship(
        "ProductImage",
        backref="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
        lazy="joined",
    )

    @property
    def text_for_catalog(self) -> str:
        """Краткий текст для карточки в каталоге: поле summary или усечённое description."""
        s = (self.summary or "").strip()
        if s:
            return s
        d = (self.description or "").strip()
        if not d:
            return ""
        return d[:100] + "…" if len(d) > 100 else d

    @property
    def main_image_path_or_url(self):
        """Путь (относительный для static) или полный URL главного изображения, или None."""
        if self.images:
            main = next((i for i in self.images if i.is_main), self.images[0])
            return main.filename
        if self.image_filename:
            return self.image_filename
        return None

    @property
    def display_images(self):
        """Список изображений для слайдера: главное первым, остальные по sort_order."""
        if not self.images:
            return []
        main = next((i for i in self.images if i.is_main), None)
        if main:
            rest = [i for i in self.images if i.id != main.id]
            return [main] + rest
        return list(self.images)

    def __repr__(self):
        return f"<Product {self.name} ({self.sku})>"


class ProductImage(db.Model):
    __tablename__ = "product_images"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    filename = db.Column(db.String(500), nullable=False)  # относительный путь, например uploads/products/uuid.jpg
    alt_text = db.Column(db.String(255), nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_main = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Cart(db.Model):
    __tablename__ = "carts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("User", backref=db.backref("cart", uselist=False))
    items = db.relationship("CartItem", backref="cart", cascade="all, delete-orphan", lazy="dynamic")


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("carts.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product = db.relationship("Product")
    qty = db.Column(db.Integer, nullable=False, default=1)
    price_snapshot = db.Column(db.Numeric(10, 2), nullable=False)


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user = db.relationship("User", backref="orders", foreign_keys=[user_id])
    guest_email = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), default="NEW", nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    contact_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(500), nullable=True)
    delivery_method = db.Column(db.String(100), nullable=True)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan", lazy="dynamic")
    payments = db.relationship("Payment", backref="order", lazy="dynamic")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product = db.relationship("Product")
    qty = db.Column(db.Integer, nullable=False)
    price_snapshot = db.Column(db.Numeric(10, 2), nullable=False)


class Payment(db.Model):
    __tablename__ = "payments"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    provider = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="CREATED")
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_url = db.Column(db.String(500), nullable=True)
    external_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CorporateRequest(db.Model):
    __tablename__ = "corporate_requests"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    message = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default="NEW", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ImportLog(db.Model):
    __tablename__ = "import_logs"
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)
    created_count = db.Column(db.Integer, default=0, nullable=False)
    updated_count = db.Column(db.Integer, default=0, nullable=False)
    error_count = db.Column(db.Integer, default=0, nullable=False)
    details_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_details(self, data):
        self.details_json = json.dumps(data, ensure_ascii=False) if data is not None else None

    def get_details(self):
        if not self.details_json:
            return None
        try:
            return json.loads(self.details_json)
        except (TypeError, ValueError):
            return None
