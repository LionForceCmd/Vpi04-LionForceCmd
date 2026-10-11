"""Настройки бота: токен из окружения и загрузка каталога."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .services import Catalog, CatalogError

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

TOKEN_ENV = "VK_TOKEN"
CATALOG_ENV = "VK_CATALOG"


class TokenMissing(RuntimeError):
    """Токен не задан — бот не может подключиться к сообществу."""


@dataclass(frozen=True)
class Settings:
    token: str
    catalog: Catalog
    group_id: str = ""

    @classmethod
    def load(
        cls,
        token: str | None = None,
        catalog_path: Path | None = None,
        env: dict | None = None,
    ) -> "Settings":
        env = os.environ if env is None else env

        token = token or env.get(TOKEN_ENV, "").strip()
        if not token:
            raise TokenMissing(
                f"Не найден токен сообщества.\n"
                f"Создайте файл .env рядом с ботом или задайте переменную окружения:\n"
                f"  {TOKEN_ENV}=vk1.a.bCDEF...\n"
                f"Токен берётся в VK: Управление сообществом → Работа с API."
            )

        path = Path(catalog_path or env.get(CATALOG_ENV) or DATA_DIR / "services.json")
        try:
            catalog = Catalog.load(path)
        except CatalogError as exc:
            raise TokenMissing(str(exc)) from exc

        return cls(token=token, catalog=catalog, group_id=env.get("VK_GROUP_ID", "").strip())


def load_dotenv(path: Path | None = None) -> None:
    """Читает .env без внешних зависимостей. Переопределяет уже заданные — нет."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and value and key not in os.environ:
            os.environ[key] = value
