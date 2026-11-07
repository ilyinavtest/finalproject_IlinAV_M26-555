"""Декораторы для ValutaTrade Hub.

@log_action — логирует вызовы доменных операций (BUY/SELL/REGISTER/LOGIN).
Не глотает исключения: пробрасывает дальше, но фиксирует в лог.
"""

import functools
from collections.abc import Callable
from typing import Any

from valutatrade_hub.logging_config import get_logger

# Маппинг имён функций в имена действий для лога.
_ACTION_MAP = {
    "buy_currency": "BUY",
    "sell_currency": "SELL",
    "register_user": "REGISTER",
    "login_user": "LOGIN",
}


def log_action(func: Callable[..., Any]) -> Callable[..., Any]:
    """Логирует вызов доменной операции.

    Действие определяется по имени функции (см. _ACTION_MAP).
    Всегда пишет базовый контекст: action, username/user_id, currency, amount, result.
    """
    action = _ACTION_MAP.get(func.__name__, func.__name__.upper())

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger()

        # Пытаемся собрать контекст из аргументов (не падаем, если чего-то нет).
        user_id = args[0] if args else kwargs.get("user_id")
        username = kwargs.get("username")
        currency = kwargs.get("currency") or kwargs.get("currency_code")
        amount = kwargs.get("amount")

        base_context = (
            f"action={action} user_id={user_id} username={username} "
            f"currency={currency} amount={amount}"
        )

        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            logger.info(
                "%s result=ERROR error_type=%s error_message=%s",
                base_context,
                type(exc).__name__,
                str(exc),
            )
            raise

        logger.info("%s result=OK", base_context)
        return result

    return wrapper
