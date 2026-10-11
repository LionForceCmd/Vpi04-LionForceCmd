"""Каталог услуг: модель данных и загрузка из JSON.

Модуль намеренно не зависит ни от vkbottle, ни от сети: всё, что можно проверить
офлайн, проверяется офлайн.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


class CatalogError(RuntimeError):
    """Каталог не найден или в нём нет обязательных полей."""


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    price: int
    price_unit: str
    duration: str
    description: str
    includes: tuple[str, ...] = field(default_factory=tuple)
    keywords: tuple[str, ...] = field(default_factory=tuple)

    @property
    def price_text(self) -> str:
        return f"{self.price:,}".replace(",", " ") + " ₽ " + self.price_unit

    def match(self, needle: str) -> int:
        """Длина самого длинного совпавшего ключевого слова, 0 если совпадений нет.

        Русские окончания мешают проверке `in`, поэтому слова перечислены
        явно в keywords. Приоритет отдаётся самому длинному совпадению:
        «уборка офиса» должна попасть в офис, а не в уборку квартиры.
        """
        needle = needle.strip().lower()
        if not needle:
            return 0
        if needle == self.id or needle in self.name.lower():
            return len(needle)
        best = 0
        for keyword in self.keywords:
            keyword = keyword.lower()
            if keyword in needle or needle in keyword:
                best = max(best, len(keyword))
        return best

    @classmethod
    def from_dict(cls, raw: dict) -> "Service":
        missing = [key for key in ("id", "name", "price", "description") if key not in raw]
        if missing:
            raise CatalogError(f"В услуге {raw.get('name', '?')} нет полей: {', '.join(missing)}")
        return cls(
            id=str(raw["id"]),
            name=str(raw["name"]),
            price=int(raw["price"]),
            price_unit=str(raw.get("price_unit", "")),
            duration=str(raw.get("duration", "")),
            description=str(raw["description"]),
            includes=tuple(raw.get("includes", [])),
            keywords=tuple(raw.get("keywords", [])),
        )


@dataclass(frozen=True)
class Catalog:
    """Компания и её услуги."""

    company: str
    services: tuple[Service, ...]
    currency: str = "₽"

    def get(self, service_id: str) -> Service | None:
        for service in self.services:
            if service.id == service_id:
                return service
        return None

    def find(self, needle: str) -> Service | None:
        """Ищет услугу по id, названию или ключевым словам.

        При нескольких совпадениях побеждает самое длинное ключевое слово,
        иначе «уборка офиса» ушла бы в «Уборку квартиры».
        """
        needle = needle.strip().lower()
        if not needle:
            return None
        best: Service | None = None
        best_score = 0
        for service in self.services:
            score = service.match(needle)
            if score > best_score:
                best, best_score = service, score
        return best

    @classmethod
    def load(cls, path: Path | None = None) -> "Catalog":
        path = path or DATA_DIR / "services.json"
        if not path.exists():
            raise CatalogError(f"Файл каталога не найден: {path}")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CatalogError(f"Каталог не читается как JSON: {exc}") from exc

        services = tuple(Service.from_dict(item) for item in raw.get("services", []))
        if not services:
            raise CatalogError("В каталоге нет ни одной услуги")

        seen: set[str] = set()
        for service in services:
            if service.id in seen:
                raise CatalogError(f"Повторяющийся id услуги: {service.id}")
            seen.add(service.id)

        return cls(
            company=str(raw.get("company", "Компания")),
            services=services,
            currency=str(raw.get("currency", "₽")),
        )
