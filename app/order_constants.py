# единая модель статусов заказа (mvp, без реального эквайринга).
# коды в бд: латиница, подписи: для ui.

ORDER_STATUS_LABELS = {
    "NEW": "Новый",
    "AWAITING_PAYMENT": "Ожидает оплаты",
    "PAID": "Оплачен",
    "PROCESSING": "В обработке",
    "SHIPPED": "Отправлен",
    "COMPLETED": "Завершён",
    "CANCELLED": "Отменён",
    # legacy (старые данные)
    "CONFIRMED": "Подтверждён",
    "DONE": "Выполнен",
}

# статусы, которые может выставить администратор вручную
ADMIN_SELECTABLE_STATUSES = (
    "NEW",
    "AWAITING_PAYMENT",
    "PAID",
    "PROCESSING",
    "SHIPPED",
    "COMPLETED",
    "CANCELLED",
    # устаревшие коды (старые данные в БД)
    "CONFIRMED",
    "DONE",
)


# статусы, допустимые для корпоративных заявок (совпадают с вариантами в шаблоне)
CORPORATE_REQUEST_STATUSES = {"NEW", "IN_PROGRESS", "DONE"}


def label_for_status(code):
    if not code:
        return "—"
    return ORDER_STATUS_LABELS.get(code, code)
