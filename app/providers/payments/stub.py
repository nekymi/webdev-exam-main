from decimal import Decimal
from typing import Optional, Tuple

from flask import url_for

from app.providers.payments.base import PaymentProvider


class StubPaymentProvider(PaymentProvider):
    """Заглушка платежа: создаёт payment_url на внутреннюю страницу /payments/stub/<payment_id>."""

    @property
    def name(self) -> str:
        return "stub"

    def create_payment(
        self,
        order_id: int,
        amount: Decimal,
        success_url: str,
        cancel_url: str,
        description: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        # external_id не нужен для stub; payment_url формируется в сервисе по payment.id
        return ("", None)

    def get_stub_payment_url(self, payment_id: int) -> str:
        """Вне контекста запроса передайте request context или base_url."""
        return url_for("orders.stub_payment_page", payment_id=payment_id, _external=True)

    def check_status(self, external_id: str) -> str:
        return "PENDING"
