from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SyncResult:
    created_count: int = 0
    updated_count: int = 0
    error_count: int = 0
    errors: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class CatalogSyncProvider(ABC):
    """Интерфейс синхронизации каталога (1С, CSV, API). Реальный обмен с 1С подключается сюда."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def sync(self, data: Any) -> SyncResult:
        """
        импорт/обновление товаров. data: сырые данные (файл, json и т.д.).
        обновление по sku (создать если нет). логирование результата в importlog: снаружи.
        """
        pass
