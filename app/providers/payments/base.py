from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional, Tuple


class PaymentProvider(ABC):
    """Интерфейс платёжного провайдера. Реальные платёжки (ЮKassa, Stripe и т.д.) реализуют этот интерфейс."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Идентификатор провайдера (например 'stub', 'yookassa')."""
        pass

    @abstractmethod
    def create_payment(
        self,
        order_id: int,
        amount: Decimal,
        success_url: str,
        cancel_url: str,
        description: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """
        Создать платёж у провайдера.
        Returns: (external_id или пустая строка, payment_url для редиректа пользователя).
        """
        pass

    @abstractmethod
    def check_status(self, external_id: str) -> str:
        """
        Проверить статус платежа у провайдера.
        Returns: 'CREATED' | 'PENDING' | 'PAID' | 'FAILED'
        """
        pass
