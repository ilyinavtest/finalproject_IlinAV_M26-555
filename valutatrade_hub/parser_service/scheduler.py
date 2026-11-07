"""Планировщик периодического обновления курсов.

Запуск вручную:
    python -m valutatrade_hub.parser_service.scheduler

Интервал задаётся в ParserConfig.SCHEDULER_INTERVAL_SECONDS (по умолчанию 3600 сек).
Защита от слишком частых вызовов API: минимальный интервал — 60 сек.
"""

from __future__ import annotations

import time

from valutatrade_hub.logging_config import get_parser_logger
from valutatrade_hub.parser_service.config import get_parser_config
from valutatrade_hub.parser_service.updater import RatesUpdater

_MIN_INTERVAL_SECONDS = 60


def run_forever(interval_seconds: int | None = None) -> None:
    """Бесконечно обновляет курсы с заданным интервалом.

    Ctrl+C — корректный выход.
    """
    logger = get_parser_logger()
    cfg = get_parser_config()

    interval = interval_seconds or cfg.SCHEDULER_INTERVAL_SECONDS
    if interval < _MIN_INTERVAL_SECONDS:
        logger.warning(
            "Scheduler interval %d sec is too small, forcing %d sec",
            interval,
            _MIN_INTERVAL_SECONDS,
        )
        interval = _MIN_INTERVAL_SECONDS

    updater = RatesUpdater.from_config(cfg)
    logger.info("Scheduler started (interval=%d sec)", interval)

    try:
        while True:
            try:
                result = updater.run_update()
                logger.info(
                    "Scheduled update: %d rates, errors=%d",
                    result["updated"],
                    len(result["errors"]),
                )
            except Exception as exc:
                logger.exception("Scheduled update failed: %s", exc)

            logger.info("Sleeping %d sec until next update...", interval)
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user (Ctrl+C)")
        print("Scheduler stopped.")


if __name__ == "__main__":
    run_forever()
