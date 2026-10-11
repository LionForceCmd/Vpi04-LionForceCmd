"""Тесты бота. Не нужны ни токен, ни сеть, ни vkbottle."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot import core
from bot.config import Settings, TokenMissing, load_dotenv
from bot.core import MENU, PRICE, SERVICES, Button, parse_callback, route
from bot.mock import SCENARIO, MockSession, run
from bot.services import Catalog, CatalogError, Service


class TestCatalog(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog.load()

    def test_loads_all_services(self):
        self.assertGreaterEqual(len(self.catalog.services), 5)
        self.assertEqual(self.catalog.company, "Чистый Дом")

    def test_get_by_id(self):
        self.assertIsNotNone(self.catalog.get("himchistka"))

    def test_get_unknown_id_returns_none(self):
        self.assertIsNone(self.catalog.get("net-takoy"))

    def test_find_by_partial_name(self):
        found = self.catalog.find("мойка окон")
        self.assertIsNotNone(found)
        self.assertEqual(found.id, "okna")

    def test_find_by_keyword(self):
        cases = {
            "тараканы": "dezinsection",
            "диван": "himchistka",
            "муравьи": "dezinsection",
            "после ремонта": "remont",
            "стёкла": "okna",
        }
        for needle, expected in cases.items():
            self.assertEqual(self.catalog.find(needle).id, expected, needle)

    def test_longer_keyword_wins(self):
        """«уборка офиса» — это офис, а не уборка квартиры."""
        self.assertEqual(self.catalog.find("уборка офиса").id, "uborka-ofisa")
        self.assertEqual(self.catalog.find("уборка квартиры").id, "uborka-kvartiry")

    def test_unknown_text_returns_none(self):
        self.assertIsNone(self.catalog.find("абракадабра"))

    def test_find_by_full_id(self):
        self.assertEqual(self.catalog.find("himchistka").id, "himchistka")

    def test_find_empty_needle(self):
        self.assertIsNone(self.catalog.find("   "))

    def test_price_text_is_formatted(self):
        self.assertEqual(self.catalog.get("himchistka").price_text, "2 500 ₽ за 1 диван")

    def test_missing_file(self):
        with self.assertRaises(CatalogError):
            Catalog.load(Path("нет-такого-файла.json"))

    def test_duplicate_ids_rejected(self):
        raw = {"company": "X", "services": [
            {"id": "a", "name": "A", "price": 1, "description": "d"},
            {"id": "a", "name": "B", "price": 2, "description": "d"},
        ]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(raw, fh, ensure_ascii=False)
            path = Path(fh.name)
        with self.assertRaises(CatalogError):
            Catalog.load(path)
        path.unlink()

    def test_empty_catalog_rejected(self):
        raw = {"company": "X", "services": []}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
            json.dump(raw, fh, ensure_ascii=False)
            path = Path(fh.name)
        with self.assertRaises(CatalogError):
            Catalog.load(path)
        path.unlink()


class TestRouting(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog.load()

    def test_main_menu_has_all_four_buttons(self):
        labels = [b.label for row in route(MENU, self.catalog).buttons for b in row]
        self.assertEqual(len(labels), 4)
        self.assertTrue(any("Услуги" in x for x in labels))
        self.assertTrue(any("Прайс" in x for x in labels))
        self.assertTrue(any("менеджер" in x.lower() for x in labels))

    def test_services_button_lists_every_service(self):
        reply = route(SERVICES, self.catalog)
        payloads = [p for p in reply.payloads() if p.startswith("service:")]
        self.assertEqual(len(payloads), len(self.catalog.services))
        for service in self.catalog.services:
            self.assertIn(service.name, reply.text)
            self.assertIn(f"{service.price:,}".replace(",", " "), reply.text)

    def test_price_list_contains_every_price(self):
        text = route(PRICE, self.catalog).text
        for service in self.catalog.services:
            self.assertIn(service.name, text)
            self.assertIn(f"{service.price:,}".replace(",", " "), text)

    def test_service_card_shows_description_and_price(self):
        service = self.catalog.get("himchistka")
        text = route(f"service:{service.id}", self.catalog).text
        self.assertIn(service.name, text)
        self.assertIn(service.description, text)
        self.assertIn("2 500", text)
        for point in service.includes[:2]:
            self.assertIn(point, text)

    def test_service_card_has_manager_button(self):
        reply = route("service:okna", self.catalog)
        self.assertIn(core.MANAGER, reply.payloads())

    def test_manager_reply_gives_contacts(self):
        text = route(core.MANAGER, self.catalog).text
        self.assertIn("менеджер", text.lower())
        self.assertIn("+7", text)

    def test_unknown_service_falls_back_to_menu(self):
        reply = route("service:нет-такой", self.catalog)
        self.assertIn("меню", reply.text.lower())

    def test_free_text_finds_service(self):
        self.assertIn("Мойка окон", route(MENU, self.catalog, "мойка окон").text)

    def test_text_wins_over_default_action(self):
        """Пока пользователь не нажал кнопку, action == MENU. Текст всё равно должен ответить."""
        self.assertIn("Химчистка мебели", route(MENU, self.catalog, "химчистка").text)

    def test_office_text_not_swallowed_by_apartment_cleaning(self):
        self.assertIn("Уборка офиса", route(MENU, self.catalog, "уборка офиса").text)

    def test_start_aliases_open_menu(self):
        for alias in ("/start", "начать", "меню", "Привет"):
            self.assertIn("Выберите", route(MENU, self.catalog, alias).text)

    def test_garbage_shows_menu_and_repeats_query(self):
        reply = route(MENU, self.catalog, "абракадабра")
        self.assertIn("абракадабра", reply.text)
        self.assertEqual(len(reply.buttons), 4)

    def test_every_reply_has_buttons(self):
        for action in (MENU, SERVICES, PRICE, core.MANAGER, core.HELP, "service:okna"):
            self.assertTrue(route(action, self.catalog).buttons, action)


class TestPayload(unittest.TestCase):
    def test_plain_payload(self):
        self.assertEqual(parse_callback("services"), "services")

    def test_service_payload(self):
        self.assertEqual(parse_callback("service:okna"), "service:okna")

    def test_alt_service_prefix(self):
        self.assertEqual(parse_callback("svc:okna"), "service:okna")

    def test_empty_payload(self):
        self.assertEqual(parse_callback(None), MENU)


class TestMockRun(unittest.TestCase):
    def test_full_scenario_produces_a_reply_per_step(self):
        catalog = Catalog.load()
        session = run(catalog, verbose=False)
        self.assertEqual(len(session.log), len(SCENARIO))
        for text in session.log:
            self.assertTrue(text.strip())

    def test_mock_session_press_matches_core(self):
        catalog = Catalog.load()
        session = MockSession(catalog=catalog)
        self.assertEqual(session.press("price").text, route(PRICE, catalog).text)


class TestConfig(unittest.TestCase):
    def test_missing_token_raises(self):
        with self.assertRaises(TokenMissing):
            Settings.load(env={})

    def test_token_from_env(self):
        settings = Settings.load(env={"VK_TOKEN": "vk1.test.token"})
        self.assertEqual(settings.token, "vk1.test.token")

    def test_bad_catalog_raises(self):
        with self.assertRaises(TokenMissing):
            Settings.load(token="vk1.test", catalog_path=Path("нет.json"), env={})

    def test_dotenv_loader_reads_file(self):
        import os

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env"
            path.write_text("VK_TOKEN=vk1.from.dotenv\n# комментарий\n", encoding="utf-8")
            os.environ.pop("VK_TOKEN", None)
            load_dotenv(path)
            self.assertEqual(os.environ.get("VK_TOKEN"), "vk1.from.dotenv")
            os.environ.pop("VK_TOKEN", None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
