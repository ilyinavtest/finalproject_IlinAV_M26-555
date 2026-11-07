"""Клиенты внешних API: CoinGecko (крипто) и ExchangeRate-API (фиат).

Все клиенты приводят ответ к стандартизированному виду:
    {"<CODE>_USD": <rate_float>, ...}

Ошибки сети/API оборачиваются в ApiRequestError.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Абстрактный клиент API для получения курсов."""

    name: str = "base"

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Возвращает курсы в формате {PAIR: rate}."""


class CoinGeckoClient(BaseApiClient):
    """Клиент CoinGecko для криптовалют."""

    name = "CoinGecko"

    def __init__(self, config: ParserConfig) -> None:
        self._config = config

    def fetch_rates(self) -> dict[str, float]:
        """Запрашивает курсы криптовалют к базовой валюте.

        Формат ответа от CoinGecko:
            {"bitcoin": {"usd": 59337.21}, ...}
        Возвращает:
            {"BTC_USD": 59337.21, ...}
        """
        ids = ",".join(self._config.CRYPTO_ID_MAP.values())
        vs = self._config.BASE_FIAT_CURRENCY.lower()
        params = {"ids": ids, "vs_currencies": vs}

        try:
            response = requests.get(
                self._config.COINGECKO_URL,
                params=params,
                timeout=self._config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(
                f"CoinGecko: ошибка сети ({exc.__class__.__name__})"
            ) from exc

        self._check_status(response, "CoinGecko")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiRequestError("CoinGecko: некорректный JSON в ответе") from exc

        result: dict[str, float] = {}
        for code, raw_id in self._config.CRYPTO_ID_MAP.items():
            entry = payload.get(raw_id)
            if not isinstance(entry, dict):
                continue
            rate = entry.get(vs)
            if isinstance(rate, (int, float)) and not isinstance(rate, bool):
                result[f"{code}_{self._config.BASE_FIAT_CURRENCY}"] = float(rate)

        if not result:
            raise ApiRequestError("CoinGecko: пустой ответ, не удалось разобрать курсы")
        return result

    @staticmethod
    def _check_status(response: requests.Response, source: str) -> None:
        """Проверяет status_code и бросает ApiRequestError с понятным текстом."""
        if response.status_code == 200:
            return
        if response.status_code == 429:
            raise ApiRequestError(f"{source}: превышен лимит запросов (429)")
        if response.status_code in (401, 403):
            raise ApiRequestError(f"{source}: доступ запрещён ({response.status_code})")
        raise ApiRequestError(
            f"{source}: HTTP {response.status_code} при обращении к API"
        )


class ExchangeRateApiClient(BaseApiClient):
    """Клиент ExchangeRate-API для фиатных валют."""

    name = "ExchangeRate-API"

    def __init__(self, config: ParserConfig) -> None:
        self._config = config

    def fetch_rates(self) -> dict[str, float]:
        """Запрашивает курсы фиатных валют к базовой валюте.

        Формат ответа от ExchangeRate-API:
            {"result": "success", "rates": {"EUR": 0.927, ...}}
        Возвращает:
            {"EUR_USD": 0.927, ...}
        """
        if not self._config.EXCHANGERATE_API_KEY:
            raise ApiRequestError(
                "ExchangeRate-API: не задан EXCHANGERATE_API_KEY "
                "(проверьте .env)"
            )

        base = self._config.BASE_FIAT_CURRENCY
        url = (
            f"{self._config.EXCHANGERATE_API_URL}/"
            f"{self._config.EXCHANGERATE_API_KEY}/latest/{base}"
        )

        try:
            response = requests.get(
                url,
                timeout=self._config.REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ApiRequestError(
                f"ExchangeRate-API: ошибка сети ({exc.__class__.__name__})"
            ) from exc

        CoinGeckoClient._check_status(response, "ExchangeRate-API")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiRequestError("ExchangeRate-API: некорректный JSON в ответе") from exc

        if payload.get("result") != "success":
            error_type = payload.get("error-type", "unknown")
            raise ApiRequestError(
                f"ExchangeRate-API: ответ с ошибкой ({error_type})"
            )

        rates = payload.get("conversion_rates") or payload.get("rates")
        if not isinstance(rates, dict):
            raise ApiRequestError(
                "ExchangeRate-API: в ответе нет поля 'conversion_rates'/'rates'"
            )

        result: dict[str, float] = {}
        for code in self._config.FIAT_CURRENCIES:
            rate = rates.get(code)
            if isinstance(rate, (int, float)) and not isinstance(rate, bool):
                # API возвращает «сколько code за 1 base», а нам нужен
                # «сколько base за 1 code» → инвертируем.
                if rate == 0:
                    continue
                result[f"{code}_{base}"] = 1.0 / float(rate)

        if not result:
            raise ApiRequestError("ExchangeRate-API: пустой ответ, не удалось разобрать курсы")
        return result
