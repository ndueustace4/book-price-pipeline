# Book & Quote Data Pipeline

An end-to-end data automation project: scrapers collect data from two public scraping-practice sites, a cleaning step turns it into typed records, PostgreSQL stores it with a price history, a FastAPI service exposes it, and a React dashboard lets you explore it. A GitHub Actions workflow tests the code and refreshes the data every day.

## What it does

- **Static scraper** (`requests` + BeautifulSoup) walks all 50 pages of [books.toscrape.com](https://books.toscrape.com/) and collects about 1,000 books (title, price, rating, stock).
- **JavaScript scraper** (Playwright + headless Chromium) loads [quotes.toscrape.com/js](https://quotes.toscrape.com/js/), a page that is empty without JavaScript, and collects 100 quotes with authors and tags.
- **Cleaning** converts raw strings to typed values (prices to numbers, star classes to ratings), drops unusable records and removes duplicates.
- **Storage** in PostgreSQL (Neon). Books are upserted, and every run adds a row to a `price_history` table, so price changes can be tracked over time.
- **REST API** (FastAPI) with search, filters, sorting, pagination and a stats endpoint, plus quote endpoints.
- **Dashboard** (React + Vite): stats cards, a filterable books table, a price-history panel and a quotes browser.
- **Automation**: tests run on every push, and the scrapers run daily on a schedule.

## Architecture

```mermaid
flowchart LR
    A[books.toscrape.com] -->|requests + BeautifulSoup| C[Clean and validate]
    B[quotes.toscrape.com/js] -->|Playwright| C
    C --> D[(PostgreSQL / Neon)]
    D --> E[FastAPI]
    E --> F[React dashboard]
    G[GitHub Actions: tests + daily run] --> C
```

## Built to survive site changes

Scraping breaks quietly when a site changes its layout, so the scrapers are designed to fail loudly and be easy to fix:

- All CSS selectors live in one `SELECTORS` dictionary per scraper, so a layout change is a one-place edit.
- If a page loads but no expected elements are found, the scraper raises a clear `StructureChangedError` instead of saving an empty result.
- Malformed items are skipped and logged, and requests use timeouts, retries with backoff and a polite delay between pages.
- Unit tests run the parsers against saved HTML fixtures, including a test that simulates a layout change.

## Tech stack

Python, requests, BeautifulSoup, Playwright, PostgreSQL (Neon), psycopg, FastAPI, React, Vite, pytest, Docker, GitHub Actions.

## API

| Endpoint | Description |
| --- | --- |
| `GET /books` | Search, filter by price, rating and stock, sort, paginate |
| `GET /books/{id}` | One book with its latest price |
| `GET /books/{id}/price-history` | Price snapshots over time |
| `GET /stats` | Totals, average price, price range, counts by rating |
| `GET /quotes` | Search quotes by text, author or tag |
| `GET /quotes/authors` | Authors with quote counts |
| `GET /health` | Health check |

Interactive docs are available at `/docs` when the API is running. Sort columns are allow-listed and all values are passed as query parameters, so the API is not open to SQL injection.

## Run it locally

You need Python 3.12+, Node 20+ and a PostgreSQL database (a free Neon project works).

```bash
# 1. Install
python -m venv .venv
.venv\Scripts\activate          # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 2. Configure: create a .env file containing your database URL
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# 3. Collect data
python run_books.py             # about 1,000 books; add "2 --dry" to test without the database
python run_quotes.py            # 100 quotes

# 4. Start the API
uvicorn api.main:app --reload   # http://127.0.0.1:8000/docs

# 5. Start the dashboard (second terminal)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

## Tests and CI

```bash
pytest
```

The tests cover parsing, cleaning, duplicate handling, structure-change detection and API input validation. The GitHub Actions workflow runs them on every push, then runs the scrapers daily, and also builds the three Docker images (API, dashboard, scraper) to confirm they build.

## Docker

```bash
docker compose up --build                                  # API on :8000, dashboard on :8080
docker compose --profile scrape run --rm scraper           # run both scrapers once
```

## Project structure

```
scrapers/     books.py, quotes_js.py     one module per source, selectors kept in config
pipeline/     clean.py, db.py, quotes_db.py
api/          main.py, quotes.py         FastAPI app
frontend/     React + Vite dashboard
tests/        parser, cleaning and API tests with HTML fixtures
.github/      workflow: tests, scheduled scrape, Docker builds
```

## Notes

The data sources are public sites built for scraping practice, and the scrapers use a delay between requests. If you point this at a real site, check its `robots.txt` and terms of service first. Prices on the practice site never change, so the price history stays flat; the pipeline is built to record changes if the source has them.
