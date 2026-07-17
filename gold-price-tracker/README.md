# The Bullion Ledger — Gold Price Tracker

A mobile-friendly gold price dashboard: CME Globex gold futures (currently
contract GCQ6, Aug 2026), the Coimbatore 24K retail rate from LiveChennai.com,
and the USD/INR rate — collected once a day and kept for a rolling year.

There is no server. A GitHub Actions workflow runs on a daily timer, fetches
the three numbers, and appends one row to `data/gold_data.csv`. The page
(`index.html`) reads that CSV and draws the table. GitHub Pages hosts both
for free.

## Setup (10 minutes, one time)

1. **Create a new GitHub repository** (public — GitHub Pages + the free
   Actions minutes used here both require this on a free account).
2. **Upload these files**, keeping the folder structure:
   ```
   index.html
   README.md
   data/gold_data.csv
   scripts/collect_data.py
   scripts/requirements.txt
   .github/workflows/collect-data.yml
   ```
   Easiest way: on the repo's GitHub page, "Add file" → "Upload files", then
   drag the whole folder in (GitHub preserves the paths).
3. **Turn on GitHub Pages**: Settings → Pages → under "Build and deployment",
   set Source to "Deploy from a branch", branch `main`, folder `/ (root)` →
   Save. Your site will appear at `https://<your-username>.github.io/<repo-name>/`
   within a minute or two.
4. **Let the workflow write to the repo**: Settings → Actions → General →
   scroll to "Workflow permissions" → select "Read and write permissions" →
   Save. Without this, the daily job can fetch data but can't commit it back.
5. **Run it once manually** to seed the first row: go to the Actions tab →
   "Collect daily gold price data" → "Run workflow" → Run workflow. After it
   finishes (green check), refresh your GitHub Pages site — you should see
   one row of data. From here it runs automatically every day.

That's it — no local setup, no API keys, no server to maintain.

## What it shows

| Column | Source | Notes |
|---|---|---|
| CME Group — change value & percentage | Yahoo Finance, symbol `GCQ26.CMX` | Yahoo's format for CME Globex GCQ6 (Aug 2026). See "contract rollover" below. |
| Gold price — 24K, Coimbatore, ₹/1 gram + Difference % | [LiveChennai.com](https://www.livechennai.com/gold_silverrate_Coimbatore.asp) | Scraped from the public Coimbatore rate page you shared. |
| Forex — USD/INR + Difference | [Frankfurter API](https://frankfurter.dev) | Free, no key, ECB-sourced daily reference rate. |

The site defaults to the last 7 days. Use the 14D / 30D buttons, or "Custom"
to pick any date range — it filters whatever has accumulated in
`data/gold_data.csv`, up to the last 365 days.

## Things worth knowing (so nothing surprises you later)

- **"GCQ6" and contract rollover.** GCQ6 is currently the front-month
  contract, so it lines up with what CME actually calls the active month.
  Futures contracts expire, though — in a few weeks GCQ6 will stop trading
  and the "current" contract will roll to the next month. When that
  happens, open `scripts/collect_data.py` and change one line —
  `CME_SYMBOL = "GCQ26.CMX"` — to the new month (the file has the full
  month-code table in a comment right above it). Nothing else needs to change.
- **CME data isn't official CME Globex data.** CME's own market data is a
  paid product. This uses Yahoo Finance's public quote for the same
  contract as a free stand-in — it tracks the real futures price closely,
  but treat it as indicative rather than an official settlement price.
- **The LiveChennai scrape is best-effort.** It works by reading that
  page's HTML table, so if the site redesigns that page, the Coimbatore
  column can start coming back blank until the scraper is patched. When
  that happens, the row still gets written with the other two columns
  filled in and that one blank (shown as "—") — a single bad day never
  breaks the whole pipeline. Also note: your image labelled this column
  "chennai Gold price", but the link you gave was the **Coimbatore** rate
  page, so that's what's actually being pulled — I labelled it "Coimbatore"
  on the page to keep it accurate; rename it in `index.html` if you'd
  rather it say Chennai.
- **Where the data actually lives.** Since this is a static GitHub Pages
  site (no server, no device to leave running), "your local drive" in
  practice means the `data/gold_data.csv` file inside this repo — GitHub
  stores every day's row for you automatically. To get an actual local
  copy: `git pull` any time, or just open
  `https://raw.githubusercontent.com/<you>/<repo>/main/data/gold_data.csv`
  and save it. The footer link on the page does the same.
- **Retention.** The collector script drops rows older than 365 days each
  time it runs, so the file stays roughly one year deep indefinitely.
- **Time of day.** The workflow runs at 04:00 UTC (9:30 AM IST) by default —
  edit the `cron` line in `.github/workflows/collect-data.yml` to change it.

## Changing things later

- **Track a different CME month** → edit `CME_SYMBOL` in `scripts/collect_data.py`.
- **Change the default view (7 days)** → edit the `currentRange = 7` line
  near the bottom of the `<script>` in `index.html`.
- **Change collection time** → edit the `cron` schedule in the workflow file.
