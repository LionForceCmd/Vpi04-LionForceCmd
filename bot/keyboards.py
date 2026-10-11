"""Перевод кнопок ядра в формат ВКонтакте.

Здесь и появляется зависимость от vkbottle, но только здесь: `to_vk` —
единственная функция, которая знает про библиотеку.
"""

from __future__ import annotations

from .core import Reply


def to_vk(reply: Reply) -> "Keyboard":  # noqa: F821
    """Собирает inline-клавиатуру ВКонтакте из раскладки ядра."""
    from vkbottle.tools.keyboard import Callback, Keyboard

    keyboard = Keyboard(inline=True)
    for row in reply.buttons:
        keyboard.row()
        for button in row:
            keyboard.add(Callback(button.label, payload=button.payload))
    return keyboard


def keyboard_json(reply: Reply) -> str:
    """Та же раскладка в виде JSON-строки — так её ждёт messages.send."""
    return to_vk(reply).get_json()
