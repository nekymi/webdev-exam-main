import csv
import io
from decimal import Decimal
from typing import Any

from app.providers.catalog_sync.base import CatalogSyncProvider, SyncResult


class CSVCatalogSyncProvider(CatalogSyncProvider):
    """Импорт товаров из CSV. Колонки: sku, name, description, price, stock_qty, category_name, external_id, is_active."""

    @property
    def name(self) -> str:
        return "csv"

    def sync(self, data: Any) -> SyncResult:
        from app import db
        from app.models import Category, Product

        result = SyncResult()
        if not data:
            return result

        stream = data if hasattr(data, "read") else io.BytesIO(data)
        try:
            content = stream.read().decode("utf-8-sig")
        except Exception as e:
            result.error_count += 1
            result.errors.append({"row": 0, "error": str(e)})
            return result

        reader = csv.DictReader(io.StringIO(content), delimiter=";")
        if not reader.fieldnames:
            reader = csv.DictReader(io.StringIO(content), delimiter=",")

        for row_num, row in enumerate(reader, start=2):
            sku = (row.get("sku") or "").strip()
            if not sku:
                result.error_count += 1
                result.errors.append({"row": row_num, "sku": "", "error": "SKU пустой"})
                continue

            try:
                price = Decimal(row.get("price") or "0")
            except Exception:
                price = Decimal("0")
            try:
                stock_qty = int(row.get("stock_qty") or 0)
            except Exception:
                stock_qty = 0
            if price < 0 or stock_qty < 0:
                result.error_count += 1
                result.errors.append({"row": row_num, "sku": sku, "error": "цена и остаток не могут быть отрицательными"})
                continue

            name = (row.get("name") or "").strip() or sku
            description = (row.get("description") or "").strip() or None
            category_name = (row.get("category_name") or "").strip()
            external_id = (row.get("external_id") or "").strip() or None
            is_active = (row.get("is_active", "1").strip().lower() in ("1", "true", "yes", "да"))

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
