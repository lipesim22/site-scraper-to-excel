"""Tests for the scraper.

They use an HTML page stored in this repository, so they run without an
internet connection and always give the same result.
"""

from pathlib import Path

import pytest

from scraper.extractor import Config, extract_items, next_page
from scraper.spreadsheet import existing_keys, save

PAGE = Path(__file__).parent / "sample_page.html"

CONFIG = Config.from_dict(
    {
        "url": "https://example.com/products",
        "item_selector": "article.product",
        "key_field": "title",
        "fields": [
            {"name": "title", "selector": "h2 a"},
            {"name": "price", "selector": ".price"},
            {"name": "link", "selector": "h2 a", "attribute": "href"},
        ],
        "next_page_selector": "a.next",
    }
)


@pytest.fixture
def html() -> str:
    return PAGE.read_text(encoding="utf-8")


def test_extracts_every_item(html):
    items = extract_items(html, CONFIG, CONFIG.url)
    assert len(items) == 3
    assert items[0]["title"] == "Electric Coffee Maker"
    assert items[0]["price"] == "$49.90"


def test_relative_link_becomes_absolute(html):
    items = extract_items(html, CONFIG, CONFIG.url)
    assert items[0]["link"] == "https://example.com/products/coffee-maker"


def test_missing_field_becomes_empty_string(html):
    config = Config.from_dict(
        {
            "url": CONFIG.url,
            "item_selector": "article.product",
            "fields": [
                {"name": "title", "selector": "h2 a"},
                {"name": "brand", "selector": ".brand-that-does-not-exist"},
            ],
        }
    )
    items = extract_items(html, config, config.url)
    assert items[1]["brand"] == ""


def test_item_without_key_is_dropped(html):
    # The fourth product in the sample page has no title.
    items = extract_items(html, CONFIG, CONFIG.url)
    assert "" not in [item["title"] for item in items]


def test_finds_the_next_page(html):
    assert next_page(html, CONFIG, CONFIG.url) == "https://example.com/products?p=2"


def test_config_rejects_an_invalid_key_field():
    with pytest.raises(ValueError):
        Config.from_dict(
            {
                "url": "https://example.com",
                "item_selector": ".x",
                "key_field": "does-not-exist",
                "fields": [{"name": "title", "selector": "h2"}],
            }
        )


def test_spreadsheet_saves_and_does_not_duplicate(tmp_path):
    path = tmp_path / "output.xlsx"
    columns = ["title", "price"]
    items = [
        {"title": "Coffee Maker", "price": "$49.90"},
        {"title": "Blender", "price": "$59.00"},
    ]

    assert save(path, "Products", columns, items) == 2
    assert existing_keys(path, "Products", "title") == {"Coffee Maker", "Blender"}

    # Second run: one new item is added, the old ones are already there.
    save(path, "Products", columns, [{"title": "Mixer", "price": "$80.00"}])
    assert existing_keys(path, "Products", "title") == {
        "Coffee Maker",
        "Blender",
        "Mixer",
    }


def test_missing_spreadsheet_has_no_keys(tmp_path):
    assert existing_keys(tmp_path / "nothing.xlsx", "Products", "title") == set()

