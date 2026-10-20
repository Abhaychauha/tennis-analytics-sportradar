"""Shared helpers for the three Sportradar collectors."""
import logging
import os
import time

import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("collector")

ACCESS_LEVEL = os.getenv("SPORTRADAR_ACCESS_LEVEL", "trial")   # trial | production
LANGUAGE = os.getenv("SPORTRADAR_LANGUAGE", "en")
REQUEST_DELAY = 1.2      # trial keys: ~1 request per second
MAX_RETRIES = 4


def api_url(endpoint):
    """Build https://api.sportradar.com/tennis/{access}/v3/{lang}/{endpoint}.json"""
    return (f"https://api.sportradar.com/tennis/{ACCESS_LEVEL}"
            f"/v3/{LANGUAGE}/{endpoint}.json")


def get_api_key():
    """Read the single Sportradar key from .env (SPORTRADAR_API_KEY)."""
    key = (os.getenv("SPORTRADAR_API_KEY") or "").strip().strip("\"'")
    if not key:
        raise SystemExit("Set SPORTRADAR_API_KEY in your .env file")
    if key.startswith("http") or "{" in key:
        raise SystemExit("SPORTRADAR_API_KEY looks like a URL. Paste only the "
                         "key string from the Sportradar console.")
    return key


def fetch_json(endpoint):
    """GET one Sportradar endpoint; retry on 429 / network errors."""
    api_key = get_api_key()
    url = api_url(endpoint)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params={"api_key": api_key}, timeout=30)
            if resp.status_code == 429:
                wait = 2 ** attempt
                log.warning("Rate limited (429). Sleeping %ss", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            time.sleep(REQUEST_DELAY)
            return resp.json()
        except requests.RequestException as exc:
            log.error("Attempt %s/%s failed for %s: %s",
                      attempt, MAX_RETRIES, endpoint, exc)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not fetch {endpoint} after {MAX_RETRIES} tries")


def get_connection():
    return psycopg2.connect(
        host=os.getenv("PG_HOST", "localhost"),
        port=os.getenv("PG_PORT", "5432"),
        dbname=os.getenv("PG_DATABASE", "tennis_db"),
        user=os.getenv("PG_USER", "postgres"),
        password=os.getenv("PG_PASSWORD", ""),
    )


def bulk_upsert(cur, sql, rows):
    """Run an INSERT ... VALUES %s ... ON CONFLICT statement for many rows."""
    if rows:
        execute_values(cur, sql, rows, page_size=500)
    log.info("Upserted %s rows", len(rows))


def run_collector(name, endpoint, transform, load):
    """Fetch -> transform -> load inside one DB transaction."""
    log.info("=== %s ===", name)
    try:
        payload = fetch_json(endpoint)
        data = transform(payload)
        conn = get_connection()
        try:
            with conn, conn.cursor() as cur:   # commits or rolls back
                load(cur, data)
        finally:
            conn.close()
        log.info("%s finished OK", name)
    except (psycopg2.Error, RuntimeError, KeyError) as exc:
        log.exception("%s FAILED: %s", name, exc)
