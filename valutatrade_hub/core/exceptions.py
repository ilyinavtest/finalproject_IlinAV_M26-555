"""Пользовательские исключения ValutaTrade Hub

Иерархия:
- ValutaTradeError — базовое исключение проекта (для перехвата всех доменных ошибок)
- InsufficientFundsError — недостаточно средств на кошельке
- CurrencyNotFoundError — неизвестная валюта
- ApiRequestError — сбой при обращении к внешнему API
"""


class ValutaTradeError(Exception):
    """Базовое исключение проекта

    Позволяет в CLI перехватывать все доменные ошибки одним блоком,
    если потребуется
    """


class InsufficientFundsError(ValutaTradeError):
    """Недостаточно средств для выполнения операции"""

    def __init__(self, available: float, required: float, code: str) -> None:
        self.available = available
        self.required = required
        self.code = code
        message = (
            f"Недостаточно средств: доступно {available} {code}, "
            f"требуется {required} {code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutaTradeError):
    """Неизвестный код валюты"""

    def __init__(self, code: str) -> None:
        self.code = code
        message = f"Неизвестная валюта '{code}'"
        super().__init__(message)


class ApiRequestError(ValutaTradeError):
    """Сбой при обращении к внешнему API"""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        message = f"Ошибка при обращении к внешнему API: {reason}"
        super().__init__(message)
