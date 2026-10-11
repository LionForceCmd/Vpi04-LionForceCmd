"""Адаптер ВКонтакте: Long Poll API и обработка событий.

Весь код бота живёт в `core`. Здесь только доставка: событие ВК превращается
в действие, ответ превращается в сообщение с клавиатурой.
"""

from __future__ import annotations

from .config import Settings
from .core import MENU, parse_callback, route
from .keyboards import keyboard_json


def handle_event(
    event: "MessageEventMin",  # noqa: F821
    settings: Settings,
) -> tuple[str, str]:
    """Главный обработчик: принимает событие ВК, возвращает (текст, клавиатура).

    Работает и для обычного сообщения, и для нажатия на кнопку —
    различие только в том, откуда берётся действие.
    """
    payload = event.payload or {}
    if payload:
        action = parse_callback(payload.get("command"))
        argument = ""
    else:
        action = MENU
        argument = (event.text or "").strip()

    reply = route(action, settings.catalog, argument)
    return reply.text, keyboard_json(reply)


def register(bot, settings: Settings) -> None:
    """Вешает обработчики на бота и печатает стартовое сообщение в личку сообщества."""
    async def on_message_event(event) -> None:
        text, keyboard = handle_event(event, settings)
        await event.send_message(text, keyboard=keyboard)

    async def on_message(message) -> None:
        if message.text is None:
            return
        reply = route(MENU, settings.catalog, message.text.strip())
        await message.answer(reply.text, keyboard=keyboard_json(reply))

    bot.on.raw_event("message_event", on_message_event)
    bot.on.message(on_message)
    return None


def build(settings: Settings):
    """Создаёт бота с Long Poll API — сервера с HTTPS не нужно."""
    from vkbottle.bot import Bot

    return Bot(settings.token)
