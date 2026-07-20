#!/usr/bin/env python3
"""
Daily data collector for the Gold Price Tracker.

Fetches three things once a day and appends one row to data/gold_data.csv:
  1. CME Globex gold futures change value & % (currently contract GCQ6 / Aug 2026)
  2. Coimbatore 24K (Pure Gold) rate per 1 gram, via livechennai.com
  3. USD/INR forex rate, via the free Frankfurter API (ECB-sourced, no key needed)

Designed to run under GitHub Actions on a daily schedule. Any single source
failing does NOT stop the others - it is logged and left blank for that day.
Rows older than RETENTION_DAYS are dropped so the file stays ~1 year deep.
"""

import csv
import datetime as dt
import os
import re
import sys

import requests
import yfinance as yf
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "..", "data")
DATA_FILE = os.path.join(DATA_DIR, "gold_data.csv")

# --- CONFIG -------------------------------------------------------------
# CME Globex gold futures contract, in Yahoo Finance's symbol format:
# letter month-code + 2-digit year + ".CMX". GCQ6 (Aug 2026) = "GCQ26.CMX".
# Month codes: F=Jan G=Feb H=Mar J=Apr K=May M=Jun N=Jul Q=Aug U=Sep V=Oct X=Nov Z=Dec.
# When this contract expires/rolls, update this one line to the next month
# you want to track (e.g. "GCZ26.CMX" for the Dec 2026 contract).
CME_SYMBOL = "GCQ26.CMX"

CHENNAI_URL = "https://www.livechennai.com/gold_silverrate_Coimbatore.asp"
HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

FRANKFURTER_URL = "https://api.frankfurter.dev/v2/rate/USD/INR"

RETENTION_DAYS = 365
FIELDNAMES = [
    "date",
    "cme_symbol",
    "cme_price",
    "cme_change",
    "cme_change_pct",
    "chennai_24k_price",
    "chennai_diff_pct",
    "usd_inr",
    "usd_inr_diff",
]
# -------------------------------------------------------------------------


def fetch_cme():
    """Return (last_price, change_value, change_pct) for CME_SYMBOL."""
    ticker = yf.Ticker(CME_SYMBOL)
    hist = ticker.history(period="5d")
    closes = hist["Close"].dropna()
    if len(closes) < 2:
        raise RuntimeError(f"Not enough Yahoo Finance history for {CME_SYMBOL}")
    last = float(closes.iloc[-1])
    prev = float(closes.iloc[-2])
    change = last - prev
    pct = (change / prev * 100) if prev else 0.0
    return round(last, 2), round(change, 2), round(pct, 2)


def fetch_chennai_24k():
    """Scrape today's 24K (Pure Gold), 1 gram rate for Coimbatore from LiveChennai."""
    resp = requests.get(CHENNAI_URL, headers=HTTP_HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for table in soup.find_all("table"):
        table_text = table.get_text(" ", strip=True)
        if "Pure Gold" in table_text and "24" in table_text:
            for row in table.find_all("tr"):
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if cells and re.match(r"^\d{1,2}/[A-Za-z]{3}/\d{4}$", cells[0]):
                    return float(cells[1].replace(",", ""))
    raise RuntimeError("24K rate table not found on LiveChennai page (site layout may have changed)")


def fetch_usd_inr():
    """Latest USD -> INR rate from Frankfurter (free, no API key)."""
    resp = requests.get(FRANKFURTER_URL, timeout=20)
    resp.raise_for_status()
    return float(resp.json()["rate"])


def load_existing_rows():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, newline="") as f:
        return list(csv.DictReader(f))


def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = load_existing_rows()
    today = dt.date.today().isoformat()

    if rows and rows[-1].get("date") == today:
        print(f"Row for {today} already exists - skipping (run again tomorrow).")
        return

    cme_price = cme_change = cme_pct = ""
    try:
        cme_price, cme_change, cme_pct = fetch_cme()
    except Exception as exc:  # noqa: BLE001 - keep collecting other sources
        print(f"WARNING: CME fetch failed: {exc}", file=sys.stderr)

    chennai_price = ""
    try:
        chennai_price = fetch_chennai_24k()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: Chennai fetch failed: {exc}", file=sys.stderr)

    usd_inr = ""
    try:
        usd_inr = fetch_usd_inr()
    except Exception as exc:  # noqa: BLE001
        print(f"WARNING: Forex fetch failed: {exc}", file=sys.stderr)

    prev_chennai = safe_float(rows[-1].get("chennai_24k_price")) if rows else None
    prev_usd_inr = safe_float(rows[-1].get("usd_inr")) if rows else None

    chennai_diff_pct = ""
    if chennai_price != "" and prev_chennai:
        chennai_diff_pct = round((chennai_price - prev_chennai) / prev_chennai * 100, 2)

    usd_inr_diff = ""
    if usd_inr != "" and prev_usd_inr is not None:
        usd_inr_diff = round(usd_inr - prev_usd_inr, 4)

    new_row = {
        "date": today,
        "cme_symbol": CME_SYMBOL,
        "cme_price": cme_price,
        "cme_change": cme_change,
        "cme_change_pct": cme_pct,
        "chennai_24k_price": chennai_price,
        "chennai_diff_pct": chennai_diff_pct,
        "usd_inr": usd_inr,
        "usd_inr_diff": usd_inr_diff,
    }
    rows.append(new_row)

    cutoff = dt.date.today() - dt.timedelta(days=RETENTION_DAYS)
    rows = [r for r in rows if dt.date.fromisoformat(r["date"]) >= cutoff]

    with open(DATA_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Appended row for {today}: {new_row}")


if __name__ == "__main__":
    main()
