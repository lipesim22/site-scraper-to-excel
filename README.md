# Site scraper to Excel

Reads a list page, pulls out the items you point it at, and writes them to an
Excel file. On the next run it only adds what is new.

Built for the job that starts with "every Monday I copy the prices / job ads /
listings from this site into a spreadsheet".

## What it does

- Selectors live in a `.yaml` file, so the same program works on a new site
  without touching the code.
- Walks through several pages, following the "next page" link.
- Never writes the same item twice: it compares by a key column.
- Checks the site's `robots.txt` and waits between pages.
- Turns relative links into full addresses.
- Retries with a growing delay when the connection fails.
- Logs what it is doing, line by line.

## Install

```bash
pip install -r requirements.txt
```

## Use

```bash
# real run
python -m scraper.main examples/books.yaml

# show what it found, save nothing
python -m scraper.main examples/books.yaml --dry-run

# change the number of pages or the output file
python -m scraper.main examples/books.yaml --pages 5 --output output/my_books.xlsx
```

## The config file

```yaml
url: "https://books.toscrape.com/"      # where to start
item_selector: "article.product_pod"    # the block that repeats on the page
key_field: "title"                      # column used to avoid duplicates
fields:                                 # one entry per spreadsheet column
  - name: "title"
    selector: "h3 a"
    attribute: "title"                  # without 'attribute', it takes the text
  - name: "price"
    selector: "p.price_color"
next_page_selector: "li.next a"         # optional
pages: 2
delay_seconds: 1.0                      # pause between pages
output_file: "output/books.xlsx"
sheet: "Books"
```

To find the selectors: open the site, right-click the item, choose "Inspect"
and look at the class of the block that repeats.

`examples/` has two files: `books.yaml`, which really works against
books.toscrape.com (a site made for scraping practice), and `job_board.yaml`,
a blank template to adapt.

## Tests

```bash
pytest -q
```

The tests use an HTML page stored in `tests/`, so they run offline and always
give the same result.

## Scheduling a run

**Windows (Task Scheduler)**

1. Open Task Scheduler and click "Create Basic Task".
2. Pick the frequency, for example every Monday at 8 am.
3. Under "Action", choose "Start a program".
4. Program: `python`
5. Arguments: `-m scraper.main examples/books.yaml`
6. Start in: the project folder.

**Linux or macOS (cron)**

```
0 8 * * 1 cd /path/to/project && python3 -m scraper.main examples/books.yaml
```

## Limits

- Works on pages that arrive complete from the server. Sites that build the
  list with JavaScript after loading need a different tool (Playwright).
- If the site changes its layout, the selectors need updating. That is a small
  edit in the `.yaml`.
- Only collect public data, and follow each site's terms of use.

## License

MIT.
