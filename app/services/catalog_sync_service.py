from typing import Tuple

from app import db
from app.models import ImportLog
from app.providers.catalog_sync import CSVCatalogSyncProvider, ApiStubCatalogSyncProvider
from app.providers.catalog_sync.base import SyncResult


def run_csv_import(file_stream) -> Tuple[ImportLog, SyncResult]:
    provider = CSVCatalogSyncProvider()
    result = provider.sync(file_stream)
    log = ImportLog(
        type="csv",
        created_count=result.created_count,
        updated_count=result.updated_count,
        error_count=result.error_count,
    )
    log.set_details({"errors": result.errors})
    db.session.add(log)
    db.session.commit()
    return log, result


def run_api_stub_import(data) -> Tuple[ImportLog, SyncResult]:
    provider = ApiStubCatalogSyncProvider()
    result = provider.sync(data)
    log = ImportLog(
        type="api_stub",
        created_count=result.created_count,
        updated_count=result.updated_count,
        error_count=result.error_count,
    )
    log.set_details({"errors": result.errors})
    db.session.add(log)
    db.session.commit()
    return log, result
