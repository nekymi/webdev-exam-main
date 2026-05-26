from decimal import Decimal
from typing import Any

from app.providers.catalog_sync.base import CatalogSyncProvider, SyncResult


class ApiStubCatalogSyncProvider(CatalogSyncProvider):
    """Заглушка API импорта (формат как от 1С). JSON: список объектов с sku, name, description, price, stock_qty, category_name, external_id."""

    @property
    def name(self) -> str:
        return "api_stub"

    def sync(self, data: Any) -> SyncResult:
        from app import db
        from app.models import Category, Product

        result = SyncResult()
        if not data:
            return result

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and "items" in data:
            items = data["items"]
        else:
            result.error_count += 1
            result.errors.append({"error": "Ожидается список или объект с полем items"})
            return result

        for i, row in enumerate(items):
            if not isinstance(row, dict):
                result.error_count += 1
                result.errors.append({"index": i, "error": "Элемент не объект"})
                continue

            sku = (row.get("sku") or "").strip()
            if not sku:
                result.error_count += 1
                result.errors.append({"index": i, "error": "SKU пустой"})
                continue

            try:
                price = Decimal(str(row.get("price", 0)))
            except Exception:
                price = Decimal("0")
            try:
                stock_qty = int(row.get("stock_qty", 0))
            except Exception:
                stock_qty = 0
            if price < 0 or stock_qty < 0:
                result.error_count += 1
                result.errors.append({"index": i, "sku": sku, "error": "цена и остаток не могут быть отрицательными"})
                continue

            name = (row.get("name") or "").strip() or sku
            description = (row.get("description") or "").strip() or None
            category_name = (row.get("category_name") or "").strip()
            external_id = (row.get("external_id") or "").strip() or None
            is_active = row.get("is_active", True)
            if isinstance(is_active, str):
                is_active = is_active.strip().lower() in ("1", "true", "yes", "да")

            category_id = None
            if category_name:
                cat = Category.query.filter_by(name=category_name).first()
                if cat:
                    category_id = cat.id
                else:
                    cat = Category(name=category_name)
                    db.session.add(cat)
                    db.session.flush()
                    category_id = cat.id

            product = Product.query.filter_by(sku=sku).first()
            if product:
                product.name = name
                product.description = description
                product.price = price
                product.stock_qty = stock_qty
                product.category_id = category_id
                product.external_id = external_id
                product.is_active = is_active
                result.updated_count += 1
            else:
                product = Product(
                    sku=sku,
                    name=name,
                    description=description,
                    price=price,
                    stock_qty=stock_qty,
                    category_id=category_id,
                    external_id=external_id,
                    is_active=is_active,
                )
                db.session.add(product)
                result.created_count += 1

        return result
