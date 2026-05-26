from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = "auth.login"
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY не задан. Создайте .env из .env.example и укажите SECRET_KEY.")
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL не задан. Укажите DATABASE_URL в .env.")
    csrf.init_app(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)

    from app.main import main_bp
    app.register_blueprint(main_bp)
    from app.auth import auth_bp
    app.register_blueprint(auth_bp)
    from app.cart import cart_bp
    app.register_blueprint(cart_bp)
    from app.orders import orders_bp
    app.register_blueprint(orders_bp)
    from app.admin import admin_bp
    app.register_blueprint(admin_bp)
    from app.integrations import integrations_bp
    # api интеграций защищается x-api-key, csrf для внешней системы не применяется.
    csrf.exempt(integrations_bp)
    app.register_blueprint(integrations_bp)

    @login.user_loader
    def load_user(user_id):
        return db.session.get(models.User, int(user_id))

    @app.context_processor
    def inject_cart_stats():
        from flask import session
        from flask_login import current_user
        from app.services.cart_service import get_cart_stats_for_user_or_session
        if current_user.is_authenticated:
            count, total = get_cart_stats_for_user_or_session(user_id=current_user.id, session_cart=None)
        else:
            count, total = get_cart_stats_for_user_or_session(user_id=None, session_cart=session.get("cart"))
        return {"cart_count": count, "cart_total": float(total)}

    @app.context_processor
    def inject_order_status_ui():
        from app.order_constants import ADMIN_SELECTABLE_STATUSES, label_for_status

        return {
            "order_status_label": label_for_status,
            "admin_order_statuses": ADMIN_SELECTABLE_STATUSES,
        }

    return app

from app import models
