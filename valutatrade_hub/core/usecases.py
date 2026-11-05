"""Бизнес-логика приложения (usecases)"""

import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import (
    load_json,
    save_json,
    validate_amount,
    validate_currency,
)


def _hash_password(password: str, salt: str) -> str:
    """Вспомогательная функция для хеширования пароля (аналогично User)"""
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


def register_user(username: str, password: str) -> User:
    """Регистрирует нового пользователя и создает для него пустой портфель"""
    if not username or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users_data = load_json("users.json")

    # Проверка уникальности
    for user in users_data:
        if user["username"] == username:
            raise ValueError(f"Имя пользователя '{username}' уже занято")

    # Генерация ID (автоинкремент)
    new_id = max((u["user_id"] for u in users_data), default=0) + 1
    salt = secrets.token_hex(8)
    hashed = _hash_password(password, salt)
    reg_date = datetime.now().isoformat()

    new_user_dict = {
        "user_id": new_id,
        "username": username,
        "hashed_password": hashed,
        "salt": salt,
        "registration_date": reg_date,
    }

    users_data.append(new_user_dict)
    save_json("users.json", users_data)

    # Создаем пустой портфель
    portfolios_data = load_json("portfolios.json")
    portfolios_data.append({
        "user_id": new_id,
        "wallets": {}
    })
    save_json("portfolios.json", portfolios_data)

    return User.from_dict(new_user_dict)


def login_user(username: str, password: str) -> User:
    """Аутентифицирует пользователя по имени и паролю"""
    users_data = load_json("users.json")

    for user_dict in users_data:
        if user_dict["username"] == username:
            user = User.from_dict(user_dict)
            if user.verify_password(password):
                return user
            raise ValueError("Неверный пароль.")

    raise ValueError(f"Пользователь '{username}' не найден")


def get_portfolio(user_id: int) -> Portfolio:
    """Загружает портфель пользователя из JSON"""
    users_data = load_json("users.json")
    user = next((u for u in users_data if u["user_id"] == user_id), None)
    if not user:
        raise ValueError("Пользователь не найден")

    user_obj = User.from_dict(user)
    portfolios_data = load_json("portfolios.json")
    portfolio_dict = next((p for p in portfolios_data if p["user_id"] == user_id), None)

    if not portfolio_dict:
        return Portfolio(user=user_obj)

    return Portfolio.from_dict(portfolio_dict, user=user_obj)


def save_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет портфель в JSON"""
    portfolios_data = load_json("portfolios.json")
    updated = False

    for i, p in enumerate(portfolios_data):
        if p["user_id"] == portfolio.user.user_id:
            portfolios_data[i] = portfolio.to_dict()
            updated = True
            break

    if not updated:
        portfolios_data.append(portfolio.to_dict())

    save_json("portfolios.json", portfolios_data)


def get_rate(from_currency: str, to_currency: str) -> dict:
    """Возвращает курс валют. Пока используется заглушка из rates.json"""
    from_c = validate_currency(from_currency)
    to_c = validate_currency(to_currency)

    rates = load_json("rates.json")
    pair = f"{from_c}_{to_c}"

    if pair in rates:
        return rates[pair]

    # Обратная пара: если есть to_from, инвертируем
    reverse_pair = f"{to_c}_{from_c}"
    if reverse_pair in rates:
        rev = rates[reverse_pair]
        return {
            "rate": 1.0 / rev["rate"],
            "updated_at": rev["updated_at"],
            "source": "calculated",
        }

    # Кросс-курс через USD (когда одна из валют USD или обе не USD)
    usd_from = rates.get(f"{from_c}_USD")
    usd_to = rates.get(f"{to_c}_USD")
    if usd_from and usd_to:
        rate = usd_from["rate"] / usd_to["rate"]
        return {
            "rate": rate,
            "updated_at": usd_from["updated_at"],
            "source": "calculated",
        }

    raise ValueError(f"Курс {from_c}->{to_c} недоступен. Повторите попытку позже")


def buy_currency(user_id: int, currency: str, amount: float) -> dict:
    """Покупка валюты."""
    currency = validate_currency(currency)
    amount = validate_amount(amount)

    portfolio = get_portfolio(user_id)

    # Автосоздание кошелька
    wallet = portfolio.get_wallet(currency)
    if not wallet:
        wallet = portfolio.add_currency(currency)

    old_balance = wallet.balance
    wallet.deposit(amount)
    save_portfolio(portfolio)

    # Получаем курс для оценки стоимости (опционально)
    try:
        rate_info = get_rate(currency, "USD")
        rate = rate_info["rate"]
    except ValueError:
        rate = 0.0

    return {
        "currency": currency,
        "old_balance": old_balance,
        "new_balance": wallet.balance,
        "rate": rate,
        "total_cost": amount * rate,
    }


def sell_currency(user_id: int, currency: str, amount: float) -> dict:
    """Продажа валюты."""
    currency = validate_currency(currency)
    amount = validate_amount(amount)

    portfolio = get_portfolio(user_id)
    wallet = portfolio.get_wallet(currency)

    if not wallet:
        raise ValueError(
            f"У вас нет кошелька '{currency}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке"
        )

    old_balance = wallet.balance
    try:
        wallet.withdraw(amount)
    except ValueError as e:
        raise ValueError(
            f"Недостаточно средств: доступно {old_balance:.4f} {currency}, "
            f"требуется {amount:.4f} {currency}"
        ) from e

    save_portfolio(portfolio)

    try:
        rate_info = get_rate(currency, "USD")
        rate = rate_info["rate"]
    except ValueError:
        rate = 0.0

    return {
        "currency": currency,
        "old_balance": old_balance,
        "new_balance": wallet.balance,
        "rate": rate,
        "total_revenue": amount * rate,
    }
