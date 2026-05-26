# Интернет-магазин «Берегиня Алтая»

Дипломный проект на Flask: витрина натуральных продуктов Алтая, корзина с гостевым и авторизованным режимом, оформление заказа с тестовой онлайн-оплатой, админ-панель и API/CSV для синхронизации каталога.

## Основной функционал

- Каталог: пагинация, поиск по названию, фильтр по категории и AJAX-обновление списка товаров.
- Карточка товара с галереей изображений и ограничением по остатку.
- Корзина: для гостей в `session`, для авторизованных в БД, AJAX-изменение количества и удаление позиций, перенос корзины при входе/регистрации.
- Оформление заказа: гостевое (имя, телефон, email опционально) и под пользователем; статус `NEW` или `AWAITING_PAYMENT`.
- Тестовая онлайн-оплата (provider `stub`) со страницей подтверждения и переходом в статус `PAID`.
- Личный кабинет «Мои заказы» для авторизованных.
- Админ-панель: товары и категории (CRUD, загрузка фото, главное фото, порядок), заказы и смена статуса, корпоративные заявки, импорт CSV.
- API интеграции 1С: `POST /api/integrations/1c/import` с заголовком `X-API-Key`, идемпотентность по SKU.

## Стек

- Python 3.10+, Flask 3, Flask-Login, Flask-WTF (CSRF), Flask-Migrate (Alembic).
- SQLAlchemy 2 + PostgreSQL (рекомендуется) / MySQL / SQLite.
- Jinja2, Bootstrap 5, Bootstrap Icons, ванильный JS (`fetch`).

## Структура

- `run.py` — точка входа.
- `config.py` — конфигурация из переменных окружения.
- `seed_data.py` — наполнение БД ролями, админом, демо-категориями и товарами.
- `app/__init__.py` — фабрика приложения, регистрация blueprint'ов и контекст-процессоров.
- `app/models.py` — модели User, Role, Category, Product, ProductImage, Cart, CartItem, Order, OrderItem, Payment, CorporateRequest, ImportLog.
- `app/main` — витрина (каталог, карточка, контакты, корпоративная форма).
- `app/auth` — вход, выход, регистрация, перенос гостевой корзины.
- `app/cart` — корзина (страница, AJAX endpoints `/cart/api/add`, `/cart/api/line`).
- `app/orders` — оформление заказа, заглушка оплаты, список заказов пользователя.
- `app/admin` — админ-панель.
- `app/integrations` — закрытое API для импорта из 1С.
- `app/services` — бизнес-логика (`cart_service`, `catalog_service`, `order_service`, `image_service`, `corporate_service`, `catalog_sync_service`).
- `app/providers/payments/` — интерфейс и заглушка платёжного провайдера.
- `app/providers/catalog_sync/` — провайдеры синхронизации каталога (CSV, API-stub).
- `migrations/` — миграции Alembic.
- `tests/test_project_services.py` — unit-тесты сервисов.

## Установка

1. Виртуальное окружение

   ```bash
   python -m venv .venv
   .venv\Scripts\activate         # Windows (PowerShell)
   # source .venv/bin/activate    # Linux/macOS
   ```

2. Зависимости

   ```bash
   pip install -r requirements.txt
   ```

3. Переменные окружения — создайте `.env` из шаблона:

   ```bash
   copy .env.example .env         # Windows
   # cp .env.example .env         # Linux/macOS
   ```

   Заполните как минимум `SECRET_KEY`, `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`.

4. Миграции

   ```bash
   set FLASK_APP=run.py           # Windows
   # export FLASK_APP=run.py      # Linux/macOS
   flask db upgrade
   ```

5. Начальные данные (роли, админ, категории, товары)

   ```bash
   python seed_data.py
   ```

## Запуск

```bash
python run.py
```

или

```bash
flask run
```

Приложение доступно на [http://127.0.0.1:5000](http://127.0.0.1:5000). В продакшене не используйте `FLASK_DEBUG=1`.

## Переменные окружения

| Переменная             | Назначение                                                                |
| ---------------------- | ------------------------------------------------------------------------- |
| `SECRET_KEY`           | секретный ключ Flask (длинная случайная строка)                           |
| `DATABASE_URL`         | строка подключения SQLAlchemy (PostgreSQL / MySQL / SQLite)               |
| `FLASK_APP`            | `run.py`                                                                  |
| `FLASK_DEBUG`          | `0` или `1` — debug-режим                                                 |
| `SESSION_COOKIE_SECURE`| `1` для продакшена с HTTPS                                                |
| `ADMIN_EMAIL`          | email администратора, который создаст `seed_data.py`                      |
| `ADMIN_PASSWORD`       | пароль администратора (если не задан, при сиде используется `admin123`)   |
| `INTEGRATION_API_KEY`  | ключ для закрытого API `POST /api/integrations/1c/import`                 |

Пример строк `DATABASE_URL`:

- `postgresql+psycopg2://user:password@localhost:5432/dbname`
- `mysql+pymysql://user:password@localhost/dbname`
- `sqlite:///app.db`

## Команды проверки

```bash
python -m compileall -q app
python -m unittest discover -s tests -p "test_*.py"
```

## Тестовый администратор

После `python seed_data.py` создаётся учётка администратора по `ADMIN_EMAIL` / `ADMIN_PASSWORD` из `.env`. Если `ADMIN_PASSWORD` не задан, используется временный пароль `admin123` — после первого входа смените его в админке.

По умолчанию (при незаполненном `.env`):

- email: `admin@altay.local`
- пароль: `admin123`

Эти значения подходят только для локальной демонстрации и проверки на защите. Для любого внешнего сценария задайте собственные.

## Статусы заказа

| Код                | Смысл                                              |
| ------------------ | -------------------------------------------------- |
| `NEW`              | новый (например, оплата при получении)             |
| `AWAITING_PAYMENT` | ожидает оплаты (выбрана онлайн-оплата, заглушка)   |
| `PAID`             | оплачен                                            |
| `PROCESSING`       | в обработке                                        |
| `SHIPPED`          | отправлен                                          |
| `COMPLETED`        | завершён                                           |
| `CANCELLED`        | отменён                                            |

`CONFIRMED` и `DONE` оставлены как legacy для совместимости со старыми данными и редактируемы через админку.

## Архитектурные решения и ограничения MVP

- Платёжная и каталоговая интеграции вынесены в провайдеры (`app/providers/payments`, `app/providers/catalog_sync`) — реальные эквайринг и обмен с 1С подключаются без переписывания ядра.
- Бизнес-логика — в `app/services`, представления тонкие.
- CSRF включён глобально (`Flask-WTF`), у API интеграции — отдельный заголовок `X-API-Key` с `hmac.compare_digest`.
- Защита от open redirect в `auth.login` / `auth.register`.
- Гостевой заказ хранится с `user_id IS NULL` и `guest_email`; при входе/регистрации сессионная корзина и заказы привязываются к пользователю.

Не входит в MVP: реальный эквайринг и webhooks, рассылка писем, живой обмен с 1С, страница «Статус заказа» по телефону без сессии.
