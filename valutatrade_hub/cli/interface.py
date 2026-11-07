"""Командный интерфейс (CLI) для ValutaTrade Hub.

CLI только оркестрирует: парсит аргументы, вызывает usecases,
ловит ошибки и выводит сообщения. Бизнес-логика — в core/usecases.py.
"""

import argparse

from valutatrade_hub.core.exceptions import InsufficientFundsError
from valutatrade_hub.core.models import User
from valutatrade_hub.core.usecases import (
    buy_currency,
    get_portfolio,
    get_rate,
    login_user,
    register_user,
    sell_currency,
)
from valutatrade_hub.core.utils import ensure_data_files

# Текущий залогиненный пользователь (сессия в памяти процесса).
CURRENT_USER: User | None = None


def _require_login() -> User:
    """Возвращает текущего пользователя или выбрасывает ошибку, если не залогинен."""
    if CURRENT_USER is None:
        raise ValueError("Сначала выполните login")
    return CURRENT_USER


def cmd_register(args: argparse.Namespace) -> None:
    """Обработчик команды register."""
    user = register_user(args.username, args.password)
    print(
        f"Пользователь '{user.username}' зарегистрирован (id={user.user_id}). "
        f"Войдите: login --username {user.username} --password ****"
    )


def cmd_login(args: argparse.Namespace) -> None:
    """Обработчик команды login."""
    global CURRENT_USER
    user = login_user(args.username, args.password)
    CURRENT_USER = user
    print(f"Вы вошли как '{user.username}'")


def cmd_show_portfolio(args: argparse.Namespace) -> None:
    """Обработчик команды show-portfolio."""
    user = _require_login()
    base = args.base.upper()

    # Проверка, что базовая валюта известна
    if base != "USD":
        try:
            get_rate("USD", base)
        except ValueError:
            print(f"Ошибка: Неизвестная базовая валюта '{base}'")
            return

    portfolio = get_portfolio(user.user_id)
    wallets = portfolio.wallets

    if not wallets:
        print(f"Портфель пользователя '{user.username}' пуст.")
        return

    print(f"Портфель пользователя '{user.username}' (база: {base}):")

    total = 0.0
    for code, wallet in wallets.items():
        value = _wallet_value_in_base(code, wallet.balance, base)
        total += value
        print(f"- {code}: {wallet.balance:.4f}  -> {value:,.2f} {base}")

    print("-" * 33)
    print(f"ИТОГО: {total:,.2f} {base}")


def _wallet_value_in_base(currency: str, amount: float, base: str) -> float:
    """Считает стоимость amount единиц currency в базовой валюте base."""
    if currency == base:
        return amount
    try:
        rate_info = get_rate(currency, base)
    except ValueError:
        return 0.0
    return amount * rate_info["rate"]


def cmd_buy(args: argparse.Namespace) -> None:
    """Обработчик команды buy."""
    user = _require_login()
    result = buy_currency(user.user_id, args.currency, args.amount)

    if result["rate"] > 0:
        print(
            f"Покупка выполнена: {args.amount:.4f} {result['currency']} "
            f"по курсу {result['rate']:,.2f} USD/{result['currency']}"
        )
    else:
        print(f"Покупка выполнена: {args.amount:.4f} {result['currency']}")

    print("Изменения в портфеле:")
    print(
        f"- {result['currency']}: было {result['old_balance']:.4f} "
        f"-> стало {result['new_balance']:.4f}"
    )
    if result.get("rate_error"):
        print(f"Ошибка: {result['rate_error']}")
    elif result["rate"] > 0:
        print(f"Оценочная стоимость покупки: {result['total_cost']:,.2f} USD")


def cmd_sell(args: argparse.Namespace) -> None:
    """Обработчик команды sell."""
    user = _require_login()
    result = sell_currency(user.user_id, args.currency, args.amount)

    if result["rate"] > 0:
        print(
            f"Продажа выполнена: {args.amount:.4f} {result['currency']} "
            f"по курсу {result['rate']:,.2f} USD/{result['currency']}"
        )
    else:
        print(f"Продажа выполнена: {args.amount:.4f} {result['currency']}")

    print("Изменения в портфеле:")
    print(
        f"- {result['currency']}: было {result['old_balance']:.4f} "
        f"-> стало {result['new_balance']:.4f}"
    )
    if result["rate"] > 0:
        print(f"Оценочная выручка: {result['total_revenue']:,.2f} USD")


def cmd_get_rate(args: argparse.Namespace) -> None:
    """Обработчик команды get-rate."""
    from_c = args.from_currency.upper()
    to_c = args.to_currency.upper()

    rate_info = get_rate(from_c, to_c)
    rate = rate_info["rate"]
    updated_at = rate_info.get("updated_at", "n/a")

    print(f"Курс {from_c}->{to_c}: {rate:.8f} (обновлено: {updated_at})")

    # Обратный курс
    try:
        reverse_info = get_rate(to_c, from_c)
        print(f"Обратный курс {to_c}->{from_c}: {reverse_info['rate']:.8f}")
    except ValueError:
        pass


def build_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов с подкомандами."""
    parser = argparse.ArgumentParser(
        prog="valutatrade",
        description="ValutaTrade Hub — управление виртуальным портфелем.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # register
    p_register = subparsers.add_parser("register", help="Регистрация нового пользователя")
    p_register.add_argument("--username", required=True, help="Имя пользователя")
    p_register.add_argument("--password", required=True, help="Пароль (>= 4 символов)")
    p_register.set_defaults(func=cmd_register)

    # login
    p_login = subparsers.add_parser("login", help="Вход в систему")
    p_login.add_argument("--username", required=True, help="Имя пользователя")
    p_login.add_argument("--password", required=True, help="Пароль")
    p_login.set_defaults(func=cmd_login)

    # show-portfolio
    p_show = subparsers.add_parser("show-portfolio", help="Показать портфель")
    p_show.add_argument("--base", default="USD", help="Базовая валюта (по умолчанию USD)")
    p_show.set_defaults(func=cmd_show_portfolio)

    # buy
    p_buy = subparsers.add_parser("buy", help="Купить валюту")
    p_buy.add_argument("--currency", required=True, help="Код валюты (например, BTC)")
    p_buy.add_argument("--amount", type=float, required=True, help="Количество валюты")
    p_buy.set_defaults(func=cmd_buy)

    # sell
    p_sell = subparsers.add_parser("sell", help="Продать валюту")
    p_sell.add_argument("--currency", required=True, help="Код валюты")
    p_sell.add_argument("--amount", type=float, required=True, help="Количество валюты")
    p_sell.set_defaults(func=cmd_sell)

    # get-rate
    p_rate = subparsers.add_parser("get-rate", help="Получить курс валюты")
    p_rate.add_argument("--from", dest="from_currency", required=True, help="Исходная валюта")
    p_rate.add_argument("--to", dest="to_currency", required=True, help="Целевая валюта")
    p_rate.set_defaults(func=cmd_get_rate)

    return parser


def main() -> None:
    """Главная функция CLI."""
    ensure_data_files()
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except InsufficientFundsError as e:
        print(f"Ошибка: {e}")
    except ValueError as e:
        print(f"Ошибка: {e}")


if __name__ == "__main__":
    main()
