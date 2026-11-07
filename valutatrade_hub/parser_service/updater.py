"""RatesUpdater — координатор обновления курсов

- Опрашивает всех клиентов
- Объединяет результаты
- Сохраняет в exchange_rates.json (история) и rates.json (кеш для Core)
- Отказоустойчив: падение одного клиента не останавливает других
- Логирует каждый шаг в logs/parser.log
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from valutatrade_hub.logging_config import get_parser_logger
from valutatrade_hub.parser_service.api_clients import (
    BaseApiClient,
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig, get_parser_config
from valutatrade_hub.parser_service.storage import RateStorage


def _now_iso_z() -> str:
    """Текущий момент в ISO-UTC с суффиксом Z (например, 2025-10-10T12:00:00Z)"""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _split_pair(pair: str) -> tuple[str, str]:
    """'BTC_USD' -> ('BTC', 'USD')."""
    from_currency, to_currency = pair.split("_", 1)
    return from_currency, to_currency


class RatesUpdater:
    """Точка входа для логики парсинга"""

    def __init__(
        self,
        config: ParserConfig,
        clients: list[BaseApiClient],
        storage: RateStorage,
    ) -> None:
        self._config = config
        self._clients = clients
        self._storage = storage
        self._logger = get_parser_logger()

    @classmethod
    def from_config(cls, config: ParserConfig | None = None) -> RatesUpdater:
        """Удобная фабрика: собирает клиентов и storage из конфига"""
        cfg = config or get_parser_config()
        clients: list[BaseApiClient] = [
            CoinGeckoClient(cfg),
            ExchangeRateApiClient(cfg),
        ]
        storage = RateStorage(cfg)
        return cls(config=cfg, clients=clients, storage=storage)

    def run_update(self, sources: list[str] | None = None) -> dict:
        """Обновляет курсы. Возвращает сводку.

        sources: список имён клиентов для фильтрации (например, ['coingecko']).
                 None — все клиенты.
        """
        started_at = _now_iso_z()
        self._logger.info("Starting rates update at %s", started_at)

        selected = self._select_clients(sources)
        all_rates: dict[str, float] = {}
        history_records: list[dict] = []
        errors: list[str] = []

        timestamp = _now_iso_z()

        for client in selected:
            self._logger.info("Fetching from %s...", client.name)
            t0 = time.perf_counter()
            try:
                rates = client.fetch_rates()
            except Exception as exc:
                self._logger.error(
                    "Failed to fetch from %s: %s", client.name, exc
                )
                errors.append(f"{client.name}: {exc}")
                continue
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            self._logger.info(
                "Fetching from %s... OK (%d rates, %d ms)",
                client.name,
                len(rates),
                elapsed_ms,
            )

            for pair, rate in rates.items():
                all_rates[pair] = rate
                from_c, to_c = _split_pair(pair)
                history_records.append(
                    {
                        "id": f"{from_c}_{to_c}_{timestamp}",
                        "from_currency": from_c,
                        "to_currency": to_c,
                        "rate": rate,
                        "timestamp": timestamp,
                        "source": client.name,
                        "meta": {"request_ms": elapsed_ms},
                    }
                )

        if not all_rates:
            self._logger.error("No rates fetched at all. Aborting.")
            return {
                "updated": 0,
                "errors": errors,
                "last_refresh": None,
            }

        # 1. Пишем историю.
        added = self._storage.append_history(history_records)
        self._logger.info("History: %d new records (dedup total %d)",
                          added, len(history_records))

        # 2. Обновляем кеш rates.json (merge по updated_at).
        new_pairs = {
            pair: {"rate": rate, "updated_at": timestamp, "source": "ParserService"}
            for pair, rate in all_rates.items()
        }
        merged = self._storage.merge_pairs_into_cache(new_pairs)
        self._storage.save_rates_cache(merged, last_refresh=timestamp)
        self._logger.info(
            "Writing %d rates to data/rates.json (total pairs %d)",
            len(all_rates),
            len(merged),
        )
        self._logger.info("Update finished at %s", _now_iso_z())

        return {
            "updated": len(all_rates),
            "errors": errors,
            "last_refresh": timestamp,
        }

    def _select_clients(self, sources: list[str] | None) -> list[BaseApiClient]:
        """Фильтрует клиентов по --source (по ТЗ: coingecko, exchangerate)."""
        if not sources:
            return list(self._clients)
        wanted = {s.strip().lower() for s in sources}
        result: list[BaseApiClient] = []
        for client in self._clients:
            key = client.name.lower().replace("-", "").replace(" ", "")
            if key in wanted or any(w in key for w in wanted):
                result.append(client)
        return result
