import os

from dotenv import load_dotenv

# загружаем .env из папки webdev-exam (где лежит run.py), затем из текущей директории
_this_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_this_dir, ".env"))
load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    if debug:
        with app.app_context():
            from flask_migrate import upgrade

            upgrade()
        app.run(debug=True)
    else:
        app.run(debug=False)
