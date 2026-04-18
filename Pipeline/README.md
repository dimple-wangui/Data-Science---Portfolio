# Web data extraction pipeline

This folder contains a small **Python pipeline** that turns unstructured HTML from a public blog into **structured, cleaned datasets** you can analyze or share.

## What it does

1. **Fetches** the Python Insider homepage (`https://blog.python.org/`) with a short timeout.
2. **Parses** the page with **BeautifulSoup**, pulling post titles, dates, and short excerpts from nested elements (current Astro layout: `article` cards with `h3`, `time`, and `p`; legacy Blogger markup is supported as a fallback).
3. **Cleans** text with **regular expressions** (`re`): strips stray tags, normalizes common encoding quirks, and collapses whitespace; missing fields are handled explicitly.
4. **Structures** the results in a **pandas** `DataFrame` with columns: `source_url`, `title`, `date`, `content`.
5. **Exports** the same data in several formats under `output/`:
   - `cleaned_web_data.csv` — spreadsheet-friendly
   - `cleaned_web_data.json` — APIs and apps
   - `cleaned_web_data.html` — browser-friendly table
   - `cleaned_web_data.md` — Markdown table (requires `tabulate`)

The script also prints a **table preview** to the console when it runs.

## Resilience

Network handling covers **404** responses, **connection timeouts**, and other common request failures so a bad response does not crash the whole run.

## How to run

From the **repository root** (parent of this folder):

```bash
python -m pip install -r requirements.txt
python Pipeline/web_data_pipeline.py
```

Generated files appear in **`Pipeline/output/`**. Re-run the script anytime to refresh them.

## Files

| File | Role |
|------|------|
| `web_data_pipeline.py` | Main script: fetch → parse → clean → DataFrame → export |
| `output/` | Generated datasets (created on first successful run) |

Dependency versions for this portfolio live in **`../requirements.txt`** at the repo root.
