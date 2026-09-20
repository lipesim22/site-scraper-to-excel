"""Web scraper: reads a website, extracts the items and saves them to Excel.

Usage:
    python -m scraper.main examples/books.yaml
    python -m scraper.main examples/books.yaml --pages 3
    python -m scraper.main examples/books.yaml --dry-run   (saves nothing)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
import yaml

from .extractor import Config, extract_items, next_page
from .spreadsheet import existing_keys, save

USER_AGENT = "SiteScraper/1.0 (portfolio project; contact via GitHub)"

log = logging.getLogger("scraper")


def load_config(path: Path) -> Config:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Config.from_dict(data)


def may_scrape(url: str, agent: str = USER_AGENT) -> bool:
    """Check the site's robots.txt. If there is no robots.txt, allow it.

    Respecting robots.txt is the least you owe a website, and it keeps your IP
    from being blocked. When the site says no, the program stops and says so.
    """
    parts = urlparse(url)
    robots = f"{parts.scheme}://{parts.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots)
    try:
        parser.read()
    except Exception:  # no robots.txt, or the site is down
        log.warning("Could not read %s. Moving on.", robots)
        return True
    return parser.can_fetch(agent, url)


def download(url: str, headers: dict[str, str], attempts: int = 3) -> str:
    """Download the page, retrying on temporary failures."""
    headers = {"User-Agent": USER_AGENT, **headers}
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or response.encoding
            return response.text
        except requests.RequestException as error:
            if attempt == attempts:
                raise
            wait = 2 ** attempt
            log.warning("Download failed (%s). Retrying in %ss.", error, wait)
            time.sleep(wait)
    return ""


def scrape(config: Config, dry_run: bool = False) -> list[dict[str, str]]:
    """Walk through the configured pages and return the new items."""
    path = Path(config.output_file)
    already_saved = existing_keys(path, config.sheet, config.key_field)
    if already_saved:
        log.info("The file already has %d items. Skipping duplicates.", len(already_saved))

    url = config.url
    new_items: list[dict[str, str]] = []
    seen: set[str] = set()

    for page in range(1, config.pages + 1):
        if not may_scrape(url):
            log.error("robots.txt does not allow scraping %s. Stopping.", url)
            break

        log.info("Page %d of %d: %s", page, config.pages, url)
        html = download(url, config.headers)
        items = extract_items(html, config, url)
        log.info("Found %d items on this page.", len(items))

        for item in items:
            key = item[config.key_field].strip()
            if key in already_saved or key in seen:
                continue
            seen.add(key)
            new_items.append(item)

        following = next_page(html, config, url)
        if page < config.pages:
            if not following:
                log.info("No next page. Finishing.")
                break
            url = following
            time.sleep(config.delay_seconds)  # be polite to the server

    log.info("New items: %d", len(new_items))

    if dry_run:
        for item in new_items[:5]:
            log.info("Sample: %s", item)
        log.info("Dry run: nothing was saved.")
        return new_items

    if new_items:
        columns = [field.name for field in config.fields]
        save(path, config.sheet, columns, new_items)
        log.info("Wrote %d rows to %s", len(new_items), path)
    else:
        log.info("No new items. The spreadsheet is unchanged.")
    return new_items


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape a website into Excel")
    parser.add_argument("config", type=Path, help="the .yaml file with site and selectors")
    parser.add_argument("--pages", type=int, help="how many pages to walk")
    parser.add_argument("--output", type=Path, help="path of the Excel file")
    parser.add_argument("--dry-run", action="store_true", help="show items without saving")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )

    if not args.config.exists():
        log.error("Config file not found: %s", args.config)
        return 2

    config = load_config(args.config)
    if args.pages:
        config.pages = args.pages
    if args.output:
        config.output_file = str(args.output)

    try:
        scrape(config, dry_run=args.dry_run)
    except requests.RequestException as error:
        log.error("Could not reach the website: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
