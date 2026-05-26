# Итоги внедрения: галерея, загрузка фото, корзина AJAX, поиск AJAX

## Список изменённых и добавленных файлов

### Модели и миграции
- **app/models.py** — модель `ProductImage`, у `Product`: relationship `images`, свойства `main_image_path_or_url`, `display_images`.
- **migrations/versions/b2c3d4e5f67_product_images.py** — миграция для таблицы `product_image`.

### Конфигурация
- **config.py** — `MAX_CONTENT_LENGTH`, `UPLOAD_PRODUCT_EXTENSIONS`.

### Сервисы
- **app/services/image_service.py** — загрузка, удаление, назначение главного, переупорядочивание фото.
- **app/services/cart_service.py** — `get_cart_count_and_total`, `get_cart_stats_for_user_or_session`.

### Роуты и представления
- **app/admin/views.py** — эндпоинты: загрузка фото, set_main, delete, reorder.
- **app/cart/views.py** — `POST /cart/api/add` (JSON), обновление badge/toast.
- **app/main/views.py** — `GET /api/products` (JSON: items, page, pages, total), в items добавлен `stock_qty`.

### Шаблоны
- **app/templates/base.html** — meta `csrf-token`, иконка корзины с badge `.js-cart-badge`, контейнер тостов `#toast-container`, подключение `cart.js`.
- **app/templates/main/index.html** — форма поиска с `id="catalog-search-form"`, контейнер `#catalog-products`, блок пагинации `#catalog-pagination-wrap`, ссылки с `.js-catalog-page` и `data-page`, блок `scripts` с `catalog.js`.
- **app/templates/main/product_detail.html** — карусель по `product.display_images`, иначе одно изображение/placeholder; форма «В корзину» с классом `js-add-to-cart-form`.
- **app/templates/admin/product_form.html** — блок «Фото товара»: multiple upload, список фото (главное, порядок, удаление), кнопка «Сохранить порядок».

### Статика
- **app/static/css/theme.css** — стили галереи и карусели (`.product-gallery`, `.product-gallery-img` и т.д.).
- **app/static/js/cart.js** — перехват отправки `.js-add-to-cart-form`, fetch на `/cart/api/add`, обновление badge, показ Toast.
- **app/static/js/catalog.js** — перехват отправки формы поиска и кликов по пагинации, fetch на `/api/products`, обновление `#catalog-products` и пагинации без перезагрузки.

### Инициализация приложения
- **app/__init__.py** — context processor с `cart_count`, `cart_total`.

---

## Как протестировать

1. **Миграции**
   ```bash
   cd webdev-exam
   flask db upgrade
   ```
   Убедиться, что миграция применяется без ошибок.

2. **Админка: фото товара**
   - Войти как админ, перейти в редактирование/создание товара.
   - Загрузить несколько файлов (jpg/png/webp, до 5 MB).
   - Убедиться, что файлы появляются в списке, папка `app/static/uploads/products/` создаётся и в ней есть файлы с именами вида uuid + расширение.
   - Назначить главное фото (кнопка «Сделать главным»).
   - Изменить порядок (поля sort_order) и нажать «Сохранить порядок».
   - Удалить одно фото — проверить, что запись в БД и файл на диске удалены.

3. **Карточка товара: слайдер**
   - Открыть товар с несколькими фото — должна отображаться карусель Bootstrap с индикаторами и стрелками.
   - Товар без фото — одно изображение-placeholder.

4. **Каталог: главное фото**
   - На главной в карточках показывается главное фото (is_main) или первое по sort_order; при отсутствии — placeholder.

5. **Добавление в корзину без перезагрузки**
   - В каталоге или на странице товара нажать «В корзину».
   - Страница не перезагружается, скролл не уходит вверх.
   - Badge на иконке корзины обновляется, показывается Toast «Добавлено в корзину».
   - При отключённом JS форма отправляется обычным POST — редирект и перезагрузка (fallback).

6. **Поиск и пагинация без перезагрузки**
   - Ввести текст в поле поиска и нажать «Найти» — список товаров и пагинация обновляются через AJAX, скролл не сбрасывается.
   - Переключить страницу по номерам — контент и пагинация обновляются через AJAX.
   - При отключённом JS форма поиска отправляется GET на тот же каталог с параметрами — обычная перезагрузка (fallback).

---

## Безопасность загрузки файлов

- **Расширения:** разрешены только `jpg`, `jpeg`, `png`, `webp` (конфиг `UPLOAD_PRODUCT_EXTENSIONS`).
- **Размер:** лимит 5 MB через `MAX_CONTENT_LENGTH` в конфиге.
- **Имена файлов:** сохраняются как `uuid + расширение` (например `uuid.jpg`), без использования имени исходного файла — защита от path traversal и коллизий.
- **Путь сохранения:** фиксированная папка `app/static/uploads/products/`, без подстановки пользовательского пути.
- **Доступ к эндпоинтам загрузки/удаления/смены главного/переупорядочивания:** только для авторизованных админов (проверка прав в admin views).
