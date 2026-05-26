import re

from flask import flash, redirect, render_template, request, session, url_for
from flask_login import login_required, login_user, logout_user

from app import db
from app.auth import auth_bp
from app.models import Role, User
from app.services.order_service import attach_guest_orders_to_user


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email(email):
    return bool(email and len(email) <= 255 and EMAIL_RE.match(email))


def _password_error(password):
    if len(password) < 8:
        return "Пароль должен содержать не менее 8 символов."
    if len(password) > 128:
        return "Пароль слишком длинный."
    return None


def _reset_session_before_login():
    cart = session.get("cart")
    guest_order_ids = session.get("guest_order_ids")
    pending_order_id = session.get("guest_pending_payment_order_id")
    session.clear()
    if cart:
        session["cart"] = cart
    if guest_order_ids:
        session["guest_order_ids"] = guest_order_ids
    if pending_order_id:
        session["guest_pending_payment_order_id"] = pending_order_id


def _safe_redirect_target(next_param):
    """Только относительные пути приложения (защита от open redirect)."""
    if not next_param or not isinstance(next_param, str):
        return None
    n = next_param.strip()
    if n.startswith("/") and not n.startswith("//"):
        return n
    return None


def merge_session_cart_into_user(user_id):
    """Переносит гостевую корзину из сессии в корзину пользователя в БД."""
    session_cart = session.get("cart") or {}
    if not session_cart:
        return
    from app.services.cart_service import add_to_cart, get_or_create_cart

    cart = get_or_create_cart(user_id)
    for product_id_str, qty in session_cart.items():
        try:
            pid = int(product_id_str)
        except (ValueError, TypeError):
            continue
        _, err, _ = add_to_cart(cart.id, pid, qty)
    session["cart"] = {}
    session.modified = True


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not _is_valid_email(email):
            flash("Неверный email или пароль.", "danger")
            return redirect(url_for("auth.login"))
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Неверный email или пароль.", "danger")
            return redirect(url_for("auth.login"))
        _reset_session_before_login()
        login_user(user, remember=bool(request.form.get("remember")))
        merge_session_cart_into_user(user.id)
        attach_guest_orders_to_user(user.id, user_email=user.email)
        dest = _safe_redirect_target(request.form.get("next")) or _safe_redirect_target(request.args.get("next"))
        return redirect(dest or url_for("main.index"))
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not all([first_name, last_name, email, password, confirm]):
            flash("Заполните все поля.", "danger")
            return redirect(url_for("auth.register"))
        if not _is_valid_email(email):
            flash("Введите корректный email.", "danger")
            return redirect(url_for("auth.register"))
        password_error = _password_error(password)
        if password_error:
            flash(password_error, "danger")
            return redirect(url_for("auth.register"))
        if password != confirm:
            flash("Пароли не совпадают.", "danger")
            return redirect(url_for("auth.register"))
        if User.query.filter_by(email=email).first():
            flash("Пользователь с таким email уже существует.", "warning")
            return redirect(url_for("auth.register"))

        role = Role.query.filter_by(name="Покупатель").first()
        if not role:
            role = Role(name="Покупатель", description="Покупатель магазина")
            db.session.add(role)
            db.session.flush()

        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        _reset_session_before_login()
        login_user(user)
        merge_session_cart_into_user(user.id)
        attach_guest_orders_to_user(user.id, user_email=user.email)
        flash("Регистрация прошла успешно!", "success")
        dest = _safe_redirect_target(request.form.get("next")) or _safe_redirect_target(request.args.get("next"))
        return redirect(dest or url_for("main.index"))

    return render_template("auth/register.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта.", "info")
    return redirect(url_for("main.index"))
