"""Чистое ядро бота: действие → текст ответа + раскладка кнопок.

Здесь нет ни vkbottle, ни сети. Всё, что бот умеет, описано одной функцией
`route`, поэтому поведение целиком проверяется тестами и воспроизводится
локально в mock-режиме — ровно так же, как в реальном ВКонтакте.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .services import Catalog, Service

MENU = "menu"
SERVICES = "services"
PRICE = "price"
SERVICE_PREFIX = "service:"
MANAGER = "manager"
HELP = "help"
BACK = "back"
START = "start"


@dataclass(frozen=True)
class Button:
    """Кнопка в терминах ВК, без привязки к библиотеке."""

    label: str
    payload: str


@dataclass(frozen=True)
class Reply:
    """Ответ бота: текст и кнопки под ним."""

    text: str
    buttons: tuple[tuple[Button, ...], ...] = field(default_factory=tuple)

    def labels(self) -> list[list[str]]:
        return [[button.label for button in row] for row in self.buttons]

    def payloads(self) -> list[str]:
        return [button.payload for row in self.buttons for button in row]


def main_menu(catalog: Catalog) -> Reply:
    return Reply(
        text=(
            f"Здравствуйте! Это бот компании «{catalog.company}».\n\n"
            "Выберите, что вас интересует:\n"
            "• «Услуги» — полный список с ценами\n"
            "• «Прайс-лист» — цены кратко, одним сообщением\n"
            "• «Связаться с менеджером» — оставим заявку\n\n"
            "Можно написать мне название услуги текстом — например, «окна»."
        ),
        buttons=(
            (Button("📋 Услуги", SERVICES),),
            (Button("💰 Прайс-лист", PRICE),),
            (Button("✉️ Связаться с менеджером", MANAGER),),
            (Button("❓ Помощь", HELP),),
        ),
    )


def services_list(catalog: Catalog) -> Reply:
    lines = [f"Наши услуги:\n"]
    for number, service in enumerate(catalog.services, 1):
        lines.append(f"{number}. {service.name} — {service.price_text}")
    lines.append("\nНажмите на услугу, чтобы увидеть подробное описание.")
    return Reply(
        text="\n".join(lines),
        buttons=(
            tuple(
                Button(f"{service.name} · {service.price:,} ₽".replace(",", " "), SERVICE_PREFIX + service.id)
                for service in catalog.services
            ),
            (Button("← В меню", MENU),),
        ),
    )


def price_list(catalog: Catalog) -> Reply:
    header = f"Прайс-лист «{catalog.company}»\n" + "─" * 28
    rows = [
        f"{service.name}\n    {service.price_text}\n    срок: {service.duration}"
        for service in catalog.services
    ]
    total_min = min(service.price for service in catalog.services)
    footer = (
        f"\nУслуг в каталоге: {len(catalog.services)}\n"
        f"Самая доступная: от {total_min:,} ₽".replace(",", " ")
    )
    return Reply(
        text="\n\n".join([header, *rows, footer]),
        buttons=(
            (Button("📋 Все услуги", SERVICES),),
            (Button("← В меню", MENU),),
        ),
    )


def service_card(catalog: Catalog, service: Service) -> Reply:
    body = [f"🧹 {service.name}", "", service.description, ""]
    body.append(f"Стоимость: {service.price_text}")
    if service.duration:
        body.append(f"Срок выполнения: {service.duration}")
    if service.includes:
        body.append("")
        body.append("Что входит:")
        body.extend(f"  • {point}" for point in service.includes)
    body.append("")
    body.append("Менеджер ответит и подберёт удобное время.")

    return Reply(
        text="\n".join(body),
        buttons=(
            (Button("💰 Весь прайс", PRICE),),
            (Button("📋 Все услуги", SERVICES),),
            (Button("✉️ Связаться с менеджером", MANAGER),),
            (Button("← В меню", MENU),),
        ),
    )


def manager_contact(catalog: Catalog) -> Reply:
    return Reply(
        text=(
            "Оставьте заявку — менеджер свяжется с вами в рабочее время "
            "(пн–сб, 9:00–20:00) и назовёт точную стоимость.\n\n"
            "Что удобнее?\n"
            f"• Написать в сообщения сообщества «{catalog.company}»\n"
            "• Позвонить: +7 (900) 123-45-67\n"
            "• Telegram: @chistyy_dom"
        ),
        buttons=(
            (Button("← В меню", MENU),),
        ),
    )


def help_text() -> Reply:
    return Reply(
        text=(
            "Как пользоваться ботом:\n\n"
            "1. Нажмите «Услуги» — откроется список.\n"
            "2. Выберите услугу — увидите описание, цену и сроки.\n"
            "3. «Прайс-лист» — все цены одним сообщением.\n"
            "4. «Связаться с менеджером» — контакты и форма заявки.\n\n"
            "Можно написать название услуги обычным текстом: «окна», "
            "«химчистка», «офис»."
        ),
        buttons=((Button("← В меню", MENU),),),
    )


def unknown(catalog: Catalog, query: str = "") -> Reply:
    hint = f"\n\nНе понял запрос: «{query}»." if query else ""
    return Reply(
        text=f"Такого пункта у меня нет.{hint}\nВот меню:", buttons=main_menu(catalog).buttons
    )


def route(action: str, catalog: Catalog, argument: str = "") -> Reply:
    """Главная точка входа: что делает бот на любое действие.

    action   — payload кнопки
    argument — текст сообщения пользователя

    Текст важнее служебного действия: пока пользователь не нажал кнопку,
    в `action` лежит MENU по умолчанию, и проверять его первым нельзя —
    тогда любое сообщение открывало бы меню вместо ответа.
    """
    action = (action or "").strip()
    argument = (argument or "").strip()

    if argument:
        found = catalog.find(argument)
        if found:
            return service_card(catalog, found)
        cleaned = argument.lower().strip("!").lstrip("/")
        if cleaned in START_ALIASES:
            return main_menu(catalog)
        return unknown(catalog, argument)

    if action.startswith(SERVICE_PREFIX):
        service = catalog.get(action[len(SERVICE_PREFIX):])
        return service_card(catalog, service) if service else unknown(catalog, action)

    if action == SERVICES:
        return services_list(catalog)
    if action == PRICE:
        return price_list(catalog)
    if action == MANAGER:
        return manager_contact(catalog)
    if action == HELP:
        return help_text()

    return main_menu(catalog)


START_ALIASES = ("start", "начать", "старт", "menu", "меню", "привет", "hi", "hello")


def parse_callback(payload: str | None) -> str:
    """Приводит payload кнопки к действию, которое понимает `route`."""
    if not payload:
        return MENU
    text = str(payload).strip()
    if ":" in text:
        head, _, tail = text.partition(":")
        if head in (SERVICE_PREFIX.rstrip(":"), "service", "svc"):
            return SERVICE_PREFIX + tail
        return head
    return text or MENU
