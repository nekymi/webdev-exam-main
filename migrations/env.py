from logging.config import fileConfig
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from flask import current_app

_webdev_exam_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _webdev_exam_dir)

from dotenv import load_dotenv
# .env в папке webdev-exam (рядом с run.py)
load_dotenv(os.path.join(_webdev_exam_dir, ".env"))
load_dotenv()

config = context.config
# Логирование: подключаем только если alembic.ini рядом с migrations есть (Flask-Migrate кладёт alembic.ini в корень проекта)
if config.config_file_name is not None and os.path.exists(config.config_file_name):
    fileConfig(config.config_file_name)
target_metadata = None


def get_url():
    return os.getenv("DATABASE_URL") or "sqlite:///app.db"


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


from app import create_app
from app import db
app = create_app()
with app.app_context():
    target_metadata = db.metadata

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
