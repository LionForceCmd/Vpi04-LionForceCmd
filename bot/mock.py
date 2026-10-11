"""Локальная симуляция диалога.

Позволяет прогнать все сценарии бота без токена, без сети и без vkbottle:
выводит сообщения так, как они выглядели бы в чате ВКонтакте, и рисует кнопки.
Именно этот прогон используется как доказательство работы в домашнем задании.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from .core import MENU, Reply, route
from .services import Catalog

BORDER = "─" * 64

SCENARIO: list[tuple[str, str]] = [
    ("Нажать", "start"),
    ("Нажать", "services"),
    ("Нажать", "service:himchistka"),
    ("Нажать", "price"),
    ("Нажать", "manager"),
    ("Нажать", "menu"),
    ("Написать", "окна"),
    ("Нажать", "services"),
    ("Нажать", "service:dezinsection"),
    ("Нажать", "help"),
    ("Написать", "абракадабра"),
]


@dataclass
class FakeEvent:
    """Минимальный аналог события ВКонтакте для проверки handlers.handle_event."""

    text: str | None = None
    payload: dict | None = None


@dataclass
class MockSession:
    """Прогон бота по списку действий."""

    catalog: Catalog
    log: list[str] = field(default_factory=list)

    def press(self, payload: str) -> Reply:
        from .handlers import handle_event
        from .config import Settings

        settings = Settings(token="mock-token", catalog=self.catalog)
        event = FakeEvent(payload={"command": payload} if payload != "start" else None,
                          text="/start" if payload == "start" else None)
        text, _ = handle_event(event, settings)
        reply = route(payload, self.catalog, "")
        self.log.append(reply.text)
        return reply

    def say(self, text: str) -> Reply:
        from .handlers import handle_event
        from .config import Settings

        settings = Settings(token="mock-token", catalog=self.catalog)
        _, _ = handle_event(FakeEvent(text=text), settings)
        reply = route(MENU, self.catalog, text)
        self.log.append(reply.text)
        return reply


def _print_banner(catalog: Catalog, title: str) -> None:
    print()
    print(BORDER)
    print(f"  {title}")
    print(BORDER)


def _print_turn(action: str, value: str, reply: Reply) -> None:
    verb = "ПОЛЬЗОВАТЕЛЬ" if action == "Нажать" else "ПОЛЬЗОВАТЕЛЬ"
    print()
    print("┌" + BORDER)
    print(f"│ {verb}  {action}: {value}")
    print("└" + BORDER)
    print()
    for line in reply.text.splitlines():
        print(f"  {line}")
    if reply.buttons:
        print()
        print("  ┌─ кнопки ─────────────────────────────────")
        for row in reply.buttons:
            labels = "  |  ".join(button.label for button in row)
            print(f"  │  [{labels}]")
        print("  └─────────────────────────────────────────")


def run(catalog: Catalog, verbose: bool = True) -> MockSession:
    session = MockSession(catalog=catalog)
    for action, value in SCENARIO:
        reply = session.press(value) if action == "Нажать" else session.say(value)
        if verbose:
            _print_turn(action, value, reply)

    if verbose:
        _print_banner(catalog, f"Прогон завершён: {len(session.log)} сообщений бота")
    return session


def main(argv: list[str] | None = None) -> int:
    catalog = Catalog.load()
    print(BORDER)
    print(f"  Мок-режим: бот компании «{catalog.company}»")
    print(f"  Услуг в каталоге: {len(catalog.services)}")
    print(f"  Токен и сеть не нужны — проверяется чистое ядро бота.")
    run(catalog)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
