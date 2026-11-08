# ValutaTrade Hub 

Виртуальная платформа для управления портфелем фиатных и криптовалют.
Позволяет регистрироваться, управлять кошельками, покупать/продавать валюты
и отслеживать актуальные курсы через локальный кэш.

## Идея проекта

Проект состоит из двух сервисов:

- **Core Service** (CLI) — регистрация, логин, портфель, покупка/продажа,
  получение курсов из локального кэша `data/rates.json`.
- **Parser Service** — периодически (или по запросу) опрашивает внешние API
  (CoinGecko для крипты, ExchangeRate-API для фиата), обновляет кэш
  `data/rates.json` и ведёт историю в `data/exchange_rates.json`.

## Структура проекта

```
finalproject_IlinAV_M26-555/
├── data/
│   ├── users.json              # пользователи
│   ├── portfolios.json         # портфели и кошельки
│   ├── rates.json              # локальный кэш курсов (для Core)
│   └── exchange_rates.json     # история измерений (для Parser)
├── valutatrade_hub/
│   ├── logging_config.py       # логи (actions.log / parser.log, ротация)
│   ├── decorators.py           # @log_action
│   ├── core/
│   │   ├── currencies.py       # Currency / FiatCurrency / CryptoCurrency
│   │   ├── exceptions.py       # доменные исключения
│   │   ├── models.py           # User, Wallet, Portfolio
│   │   ├── usecases.py         # бизнес-логика (register/login/buy/sell/get_rate)
│   │   └── utils.py            # JSON-хранилище, валидаторы
│   ├── infra/
│   │   ├── settings.py         # SettingsLoader (Singleton)
│   │   └── database.py         # (опционально)
│   ├── parser_service/
│   │   ├── config.py           # ParserConfig (env-ключ, URL, списки)
│   │   ├── api_clients.py      # CoinGeckoClient, ExchangeRateApiClient
│   │   ├── updater.py          # RatesUpdater.run_update()
│   │   ├── storage.py          # чтение/запись JSON (атомарно)
│   │   └── scheduler.py        # периодическое обновление
│   └── cli/
│       └── interface.py        # argparse, команды, перехват исключений
├── main.py
├── pyproject.toml
├── uv.lock
├── .env.example                # шаблон персонального ключа (в git)
├── .gitignore
└── README.md
```

## Установка

Требуется Python 3.12+ и [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ilyinavtest/finalproject_IlinAV_M26-555.git
cd finalproject_IlinAV_M26-555
uv sync
```

## Настройка

### API-ключ ExchangeRate-API

1. Зарегистрируйтесь на https://www.exchangerate-api.com/ (бесплатный тариф).
2. Скопируйте ключ из личного кабинета.
3. Скопируйте `.env.example` в `.env` и вставьте ключ:

```bash
cp .env.example .env
# откройте .env и укажите EXCHANGERATE_API_KEY=<ваш_ключ>
```

**Важно:** `.env` в `.gitignore`, ключ **никогда** не попадёт в репозиторий.
В коде ключ читается только через `os.getenv("EXCHANGERATE_API_KEY")`.

CoinGecko работает без ключа (публичный доступ).

## Запуск

Все команды — через `python main.py` или `uv run python main.py`.

### Регистрация и логин

```bash
uv run python main.py register --username alice --password 1234
uv run python main.py login --username alice --password 1234
```

> **Сессия — в памяти процесса.** Каждый запуск CLI — новый процесс, поэтому
> `login` и следующая команда должны быть в одном запуске (например, через
> интерактивный скрипт или через `update-rates`+`show-rates`, не требующие логина).

### Портфель

```bash
uv run python main.py show-portfolio
uv run python main.py show-portfolio --base EUR
```

### Покупка/продажа

```bash
uv run python main.py buy --currency BTC --amount 0.05
uv run python main.py sell --currency BTC --amount 0.01
```

### Курсы

```bash
uv run python main.py get-rate --from USD --to BTC
```

### Parser Service

Ручное обновление курсов:

```bash
uv run python main.py update-rates
uv run python main.py update-rates --source coingecko
uv run python main.py update-rates --source exchangerate
```

Просмотр кэша:

```bash
uv run python main.py show-rates
uv run python main.py show-rates --currency BTC
uv run python main.py show-rates --top 2
uv run python main.py show-rates --base EUR
```

Периодическое обновление (в отдельном терминале):

```bash
uv run python -m valutatrade_hub.parser_service.scheduler
```

## Кэш и TTL

- `data/rates.json` хранит **последний срез** по каждой паре (`BTC_USD`, `EUR_USD`, …).
- TTL задаётся в `pyproject.toml` → `[tool.valutatrade]` → `rates_ttl_seconds` (по умолчанию 300 сек).
- `get-rate` и `buy`/`sell`:
  - если курс свежий (< TTL) — используется из кэша;
  - если устарел — вызывается `RatesUpdater.run_update()`, затем повторное чтение;
  - если обновление не помогло — `ApiRequestError` с понятным сообщением.
- `data/exchange_rates.json` — журнал всех измерений (`id = <FROM>_<TO>_<ISO_UTC>`),
  с дедупликацией и атомарной записью (tmp → rename).

## Логи

- `logs/actions.log` — операции пользователей (`register`, `login`, `buy`, `sell`), через `@log_action`.
- `logs/parser.log` — работа Parser Service (запросы к API, обновление, ошибки).

Ротация: по 1 МБ, до 3 резервных копий. Формат (text/json) и уровень (INFO/DEBUG)
задаются в `pyproject.toml` → `[tool.valutatrade]`.

## Обработка ошибок

Доменные исключения (в `core/exceptions.py`):

- `InsufficientFundsError` — недостаточно средств.
- `CurrencyNotFoundError` — неизвестная валюта.
- `ApiRequestError` — сбой при обращении к внешнему API.

CLI перехватывает их в `main()` и выводит дружелюбные сообщения с подсказками.


## Возможные проблемы

### `'utf-8' codec can't decode byte 0xff` при запуске

Файлы `data/*.json` повреждены (например, сохранены в UTF-16 через `echo >` в PowerShell).
Перезапишите их в UTF-8:

```powershell
uv run python -c "from pathlib import Path; [Path(f'data/{n}').write_text('[]', encoding='utf-8') for n in ('users.json', 'portfolios.json', 'exchange_rates.json')]"
```

## Демо
1. Регистрация
2. Обновление курсов (Parser Service)
3. Просмотр кэша
4. Цикл login -> buy -> show-portfolio -> sell -> get-rate
5. Демонстрация ошибки: недостаточно средств
6. Демонстрация ошибки: неизвестная валюта

![asciinema](https://asciinema.org/a/Thw96dqxhU19olUa)

## Лицензия

Учебный проект (educational Python project). MIT.
