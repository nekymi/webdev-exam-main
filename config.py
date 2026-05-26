import os

# секреты только из .env (файл не коммитить). для локальной разработки скопируйте .env.example в .env.
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    INTEGRATION_API_KEY = os.getenv("INTEGRATION_API_KEY", "")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    WTF_CSRF_TIME_LIMIT = 3600
    # загрузка файлов: лимит 5 mb
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    UPLOAD_PRODUCT_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
