"""Иерархия валют: базовый класс Currency, фиат и крипто, реестр и фабрика"""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Базовый абстрактный класс валюты"""

    def __init__(self, name: str, code: str) -> None:
        """Инициализация валюты с валидацией
        code: верхний регистр, 2-5 символов, без пробелов
        name: непустая строка
        """
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не может быть пустым")
        if not isinstance(code, str):
            raise ValueError("Код валюты должен быть строкой")

        normalized_code = code.strip().upper()
        if not 2 <= len(normalized_code) <= 5:
            raise ValueError("Код валюты должен быть длиной 2-5 символов")
        if " " in normalized_code:
            raise ValueError("Код валюты не должен содержать пробелы")

        self.name = name.strip()
        self.code = normalized_code

    @abstractmethod
    def get_display_info(self) -> str:
        """Строковое представление для UI/логов"""


class FiatCurrency(Currency):
    """Фиатная валюта (государственная)"""

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        super().__init__(name=name, code=code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна/зона эмиссии не может быть пустой")
        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        return f"[FIAT] {self.code} - {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Криптовалюта"""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        super().__init__(name=name, code=code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустой строкой")
        if not isinstance(market_cap, (int, float)) or isinstance(market_cap, bool):
            raise ValueError("Market cap должен быть числом")
        if market_cap < 0:
            raise ValueError("Market cap не может быть отрицательным")
        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        return (
            f"[CRYPTO] {self.code} - {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"
        )


# Реестр валют: словарь code -> Currency
_CURRENCIES: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 4.5e11),
    "USDT": CryptoCurrency("Tether", "USDT", "Omni", 1.0e11),
}


def get_currency(code: str) -> Currency:
    """Возвращает объект валюты по коду
    Бросает CurrencyNotFoundError, если код неизвестен
    """
    if not isinstance(code, str) or not code.strip():
        raise CurrencyNotFoundError(str(code) if code is not None else "")
    normalized = code.strip().upper()
    currency = _CURRENCIES.get(normalized)
    if currency is None:
        raise CurrencyNotFoundError(normalized)
    return currency
