"""Хранилище Parser Service: чтение/запись exchange_rates.json и rates.json.

- exchange_rates.json — история измерений (массив записей с уникальным id).
- rates.json — кеш для Core Service (последний срез по каждой паре).
Запись атомарная: tmp-файл -> rename.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from valutatrade_hub.parser_service.config import ParserConfig


class RateStorage:
    """Абстракция над JSON-файлами Parser Service."""

    def __init__(self, config: ParserConfig) -> None:
        self._config = config
        self._history_path = Path(config.HISTORY_FILE_PATH)
        self._rates_path = Path(config.RATES_FILE_PATH)

    # === Атомарная запись (tmp -> rename) ===

    @staticmethod
    def _atomic_write_json(path: Path, data: object) -> None:
        """Пишет JSON в path атомарно: сначала во временный, затем rename."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            prefix=path.name + ".",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    @staticmethod
    def _safe_load_json(path: Path, default: object) -> object:
        """Читает JSON с защитой от отсутствия/пустого/битого файла."""
        if not path.exists():
            return default
        try:
            with path.open("r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                return default
            return json.loads(content)
        except json.JSONDecodeError:
            return default

    # === exchange_rates.json (история) ===

    def load_history(self) -> list[dict]:
        """Загружает историю измерений (массив)."""
        data = self._safe_load_json(self._history_path, [])
        return data if isinstance(data, list) else []

    def append_history(self, records: list[dict]) -> int:
        """Добавляет записи в историю с дедупликацией по id.

        Возвращает количество реально добавленных записей.
        """
        if not records:
            return 0

        history = self.load_history()
        existing_ids = {r.get("id") for r in history if isinstance(r, dict)}

        added = 0
        for rec in records:
            rid = rec.get("id")
            if rid and rid not in existing_ids:
                history.append(rec)
                existing_ids.add(rid)
                added += 1

        if added > 0:
            self._atomic_write_json(self._history_path, history)
        return added

    # === rates.json (кеш для Core) ===

    def load_rates_cache(self) -> dict:
        """Загружает кеш курсов. Поддерживает миграцию старого формата.

        Старый формат: {"EUR_USD": {"rate": 1.07, "updated_at": "..."}, ...}
        Новый формат (по ТЗ): {"pairs": {...}, "last_refresh": "..."}
        """
        raw = self._safe_load_json(self._rates_path, {})
        if not isinstance(raw, dict):
            return {"pairs": {}, "last_refresh": None}

        if "pairs" in raw:
            # Уже новый формат.
            return {
                "pairs": raw.get("pairs") or {},
                "last_refresh": raw.get("last_refresh"),
            }

        # Миграция старого плоского формата.
        pairs: dict[str, dict] = {}
        for key, value in raw.items():
            if key in {"source", "last_refresh"}:
                continue
            if isinstance(value, dict) and "rate" in value:
                pairs[key] = value
        return {"pairs": pairs, "last_refresh": raw.get("last_refresh")}

    def save_rates_cache(self, pairs: dict[str, dict], last_refresh: str) -> None:
        """Сохраняет кеш курсов в новом формате (атомарно)."""
        payload = {
            "pairs": pairs,
            "last_refresh": last_refresh,
        }
        self._atomic_write_json(self._rates_path, payload)

    def merge_pairs_into_cache(self, new_pairs: dict[str, dict]) -> dict[str, dict]:
        """Объединяет новые пары с текущим кешем.

        Правило по ТЗ: «Апдейт побеждает, если updated_at свежее текущего».
        Возвращает итоговый словарь пар.
        """
        current = self.load_rates_cache()["pairs"]
        merged = dict(current)

        for pair_key, new_entry in new_pairs.items():
            old = merged.get(pair_key)
            if old is None:
                merged[pair_key] = new_entry
                continue
            old_ts = old.get("updated_at") or ""
            new_ts = new_entry.get("updated_at") or ""
            if new_ts >= old_ts:
                merged[pair_key] = new_entry

        return merged
