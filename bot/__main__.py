"""Точка входа.

    python -m bot            — запустить настоящего бота (нужен токен)
    python -m bot mock       — прогнать диалог локально, без токена и сети
    python -m bot check      — проверить каталог и настройки
"""

from __future__ import annotations

import argparse
import sys

from .config import ROOT, Settings, TokenMissing, load_dotenv


def cmd_mock() -> int:
    from .mock import main as mock_main

    return mock_main()


def cmd_check() -> int:
    from .config import TOKEN_ENV
    from .services import Catalog

    print("Проверка окружения\n")
    print(f"  Python           {sys.version.split()[0]}")
    print(f"  Корень проекта   {ROOT}")

    try:
        catalog = Catalog.load()
        print(f"  [ok]  Каталог    «{catalog.company}», услуг: {len(catalog.services)}")
        for service in catalog.services:
            print(f"          · {service.name:<24} {service.price:>6} ₽  ({service.id})")
    except Exception as exc:  # noqa: BLE001
        print(f"  [ошибка] Каталог: {exc}")
        return 1

    load_dotenv()
    import os

    token = os.environ.get(TOKEN_ENV, "").strip()
    if token:
        masked = token[:6] + "..." + token[-4:] if len(token) > 12 else "***"
        print(f"  [ok]  {TOKEN_ENV:<14} {masked}")
    else:
        print(f"  [нет]  {TOKEN_ENV:<14} не задан — бот не подключится к ВКонтакте")
        print("          Создайте .env:  VK_TOKEN=vk1.a.bCDEF...")

    try:
        import vkbottle  # noqa: F401

        print("  [ok]  vkbottle    установлен")
    except ImportError:
        print("  [нет]  vkbottle    не установлен (для реального запуска: pip install -r requirements.txt)")

    print("\nПроверить бота без токена:  python -m bot mock")
    return 0


def cmd_run() -> int:
    from .handlers import build, register

    load_dotenv()
    try:
        settings = Settings.load()
    except TokenMissing as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 2

    print(f"Бот «{settings.catalog.company}» подключается к сообществу…")
    print("Long Poll API. Для остановки — Ctrl+C.")

    bot = build(settings)
    register(bot, settings)
    bot.run_forever()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bot", description="ВК-бот с каталогом услуг")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "mock", "check"])
    args = parser.parse_args(argv)
    return {"run": cmd_run, "mock": cmd_mock, "check": cmd_check}[args.command]()


if __name__ == "__main__":
    raise SystemExit(main())
