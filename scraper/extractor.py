"""Turning an HTML page into rows.

The idea: the website changes from client to client, but the shape of the job
is always the same. So the CSS selectors live in a config file, and this
module only knows how to apply them to the HTML.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup


@dataclass
class Field:
    """One column of the final spreadsheet.

    selector: CSS selector relative to the item (e.g. "h2 a").
    attribute: when the value sits in an attribute instead of the text
        (e.g. "href").
    """

    name: str
    selector: str
    attribute: str | None = None


@dataclass
class Config:
    """Everything that changes from one site to another."""

    url: str
    item_selector: str
    fields: list[Field]
    key_field: str
    next_page_selector: str | None = None
    pages: int = 1
    delay_seconds: float = 1.0
    output_file: str = "data.xlsx"
    sheet: str = "Data"
    headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        fields = [
            Field(
                name=f["name"],
                selector=f["selector"],
                attribute=f.get("attribute"),
            )
            for f in data["fields"]
        ]
        names = [f.name for f in fields]
        key = data.get("key_field", names[0])
        if key not in names:
            raise ValueError(f"key_field '{key}' is not a field. Fields: {names}")
        return cls(
            url=data["url"],
            item_selector=data["item_selector"],
            fields=fields,
            key_field=key,
            next_page_selector=data.get("next_page_selector"),
            pages=int(data.get("pages", 1)),
            delay_seconds=float(data.get("delay_seconds", 1.0)),
            output_file=data.get("output_file", "data.xlsx"),
            sheet=data.get("sheet", "Data"),
            headers=data.get("headers", {}),
        )


def _read_field(item, field: Field, base_url: str) -> str:
    """Read one field inside an item. Returns an empty string if missing."""
    target = item if field.selector in ("", ".") else item.select_one(field.selector)
    if target is None:
        return ""
    if field.attribute:
        value = target.get(field.attribute, "")
        if isinstance(value, list):  # attributes such as class come as a list
            value = " ".join(value)
        value = value.strip()
        # Relative links become absolute, otherwise the spreadsheet is useless.
        if field.attribute in ("href", "src") and value:
            value = urljoin(base_url, value)
        return value
    return " ".join(target.get_text(" ", strip=True).split())


def extract_items(html: str, config: Config, base_url: str) -> list[dict[str, str]]:
    """Apply the selectors from the config and return a list of rows."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for element in soup.select(config.item_selector):
        row = {
            field.name: _read_field(element, field, base_url)
            for field in config.fields
        }
        # An item without the key column is useless: nothing to compare later.
        if row.get(config.key_field):
            items.append(row)
    return items


def next_page(html: str, config: Config, base_url: str) -> str | None:
    """Find the address of the next page, when the config asks for it."""
    if not config.next_page_selector:
        return None
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one(config.next_page_selector)
    if link is None or not link.get("href"):
        return None
    return urljoin(base_url, link["href"])
