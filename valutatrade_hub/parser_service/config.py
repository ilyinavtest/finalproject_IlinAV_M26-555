"""Конфигурация Parser Service

Все изменяемые параметры вынесены сюда (по ТЗ п.4.4.3)
Секреты (API-ключи) — только из переменных окружения, не хардкодятся
"""

import os
from dataclasses import dataclass, field

from valutatrade_hub.infra.settings import get_settings


@dataclass
class ParserConfig:
    """Структурированная конфигурация Parser Service."""

    # === Секреты из окружения ===
    EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY", "")

    # === Эндпоинты ===
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    # === Списки валют (строго по ТЗ п.4.3) ===
    BASE_FIAT_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")
    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    # === Сетевые параметры ===
    REQUEST_TIMEOUT: int = 10

    # === Планировщик (чтобы не превысить лимит 1500/день) ===
    SCHEDULER_INTERVAL_SECONDS: int = 3600  # 1 час

    def __post_init__(self) -> None:
        """Приводит пути к абсолютным (из SettingsLoader) и валидирует интервал"""
        settings = get_settings()
        data_dir = settings.get("data_dir_abs")
        self.RATES_FILE_PATH: str = str(data_dir / "rates.json")
        self.HISTORY_FILE_PATH: str = str(data_dir / "exchange_rates.json")
        self.LOG_FILE_PATH: str = str(settings.get("log_file_abs"))

        if self.SCHEDULER_INTERVAL_SECONDS < 60:
            # Защита от слишком частых опросов API.
            self.SCHEDULER_INTERVAL_SECONDS = 60


def get_parser_config() -> ParserConfig:
    """Хелпер для получения конфигурации парсера"""
    return ParserConfig()
