import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, Timeout


URL = "https://blog.python.org/"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
TIMEOUT_SECONDS = 12


def fetch_html(url: str) -> Optional[str]:
    """Fetch HTML with resilience for 404, timeout, and connection issues."""
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        if response.status_code == 404:
            print(f"Error: 404 Not Found for URL: {url}")
            return None
        response.raise_for_status()
        return response.text
    except Timeout:
        print(f"Error: Connection Timed Out while requesting {url}")
        return None
    except ConnectionError:
        print(f"Error: Connection issue while requesting {url}")
        return None
    except requests.HTTPError as exc:
        print(f"HTTP error while requesting {url}: {exc}")
        return None
    except requests.RequestException as exc:
        print(f"Unexpected request error while requesting {url}: {exc}")
        return None


def clean_text(raw_text: Optional[str]) -> Optional[str]:
    """Strip HTML noise, normalize encoding artifacts, and clean whitespace."""
    if raw_text is None:
        return None

    text = str(raw_text)
    text = re.sub(r"<[^>]+>", " ", text)

    replacements = {
        "\u2019": "'",
        "\u2018": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "-",
        "\u2013": "-",
        "\xa0": " ",
        "â€™": "'",
        "â€œ": '"',
        "â€\x9d": '"',
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _record_from_parts(
    source_url: str,
    title: Optional[str],
    date: Optional[str],
    body: Optional[str],
) -> Optional[Dict[str, Optional[str]]]:
    if not any([title, date, body]):
        return None
    return {
        "source_url": source_url,
        "title": title,
        "date": date,
        "content": body,
    }


def extract_posts(html: str, source_url: str) -> List[Dict[str, Optional[str]]]:
    """
    Extract nested HTML into records. Supports:
    - Current blog.python.org (Astro): article.post-card with h3, time, p
    - Legacy Blogger-style: div.content, h2/h3, h2.date-header span, div.post-body
    """
    soup = BeautifulSoup(html, "html.parser")
    records: List[Dict[str, Optional[str]]] = []

    for article in soup.select("article.post-card, article"):
        if article.select_one("div.content"):
            continue
        title_tag = article.select_one("h3 a, h3, h2")
        time_tag = article.select_one("time")
        body_tag = article.select_one("p")

        title = clean_text(title_tag.get_text(" ", strip=True)) if title_tag else None
        if time_tag is not None:
            raw_date = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)
            date = clean_text(raw_date)
        else:
            date = None
        body = clean_text(body_tag.get_text(" ", strip=True)) if body_tag else None

        rec = _record_from_parts(source_url, title, date, body)
        if rec:
            records.append(rec)

    if records:
        return records

    for container in soup.select("div.content"):
        title_tag = container.select_one("h3.post-title, h2")
        date_tag = container.select_one("h2.date-header span")
        body_tag = container.select_one("div.post-body")

        title = clean_text(title_tag.get_text(" ", strip=True)) if title_tag else None
        date = clean_text(date_tag.get_text(" ", strip=True)) if date_tag else None
        body = clean_text(body_tag.get_text(" ", strip=True)) if body_tag else None

        rec = _record_from_parts(source_url, title, date, body)
        if rec:
            records.append(rec)

    return records


def to_dataframe(records: List[Dict[str, Optional[str]]]) -> pd.DataFrame:
    """Convert extracted records into a structured DataFrame."""
    df = pd.DataFrame(records, columns=["source_url", "title", "date", "content"])
    return df.fillna("N/A")


def export_outputs(df: pd.DataFrame, output_dir: Path) -> None:
    """Export final cleaned dataset to CSV, JSON, HTML table, and Markdown table."""
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "cleaned_web_data.csv"
    json_path = output_dir / "cleaned_web_data.json"
    html_path = output_dir / "cleaned_web_data.html"
    md_path = output_dir / "cleaned_web_data.md"

    df.to_csv(csv_path, index=False, encoding="utf-8")
    df.to_json(json_path, orient="records", indent=2, force_ascii=False)

    html_doc = (
        "<!DOCTYPE html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>Cleaned web data</title>"
        "<style>table{border-collapse:collapse;width:100%;font-family:system-ui,sans-serif;font-size:14px;}"
        "th,td{border:1px solid #ccc;padding:8px;text-align:left;vertical-align:top;}"
        "th{background:#f4f4f4;}</style></head><body>\n"
        f"{df.to_html(index=False, escape=True, border=0)}"
        "\n</body></html>\n"
    )
    html_path.write_text(html_doc, encoding="utf-8")

    try:
        md_path.write_text(df.to_markdown(index=False), encoding="utf-8")
    except ImportError:
        md_path.write_text(
            "(Install `tabulate` to generate Markdown: pip install tabulate)\n",
            encoding="utf-8",
        )

    print(f"Saved CSV: {csv_path}")
    print(f"Saved JSON: {json_path}")
    print(f"Saved HTML table: {html_path}")
    print(f"Saved Markdown table: {md_path}")


def run_pipeline(url: str = URL) -> None:
    html = fetch_html(url)
    if html is None:
        print("Pipeline stopped: no HTML retrieved.")
        return

    records = extract_posts(html, url)
    if not records:
        print("Pipeline finished: no records found for the target selectors.")
        return

    df = to_dataframe(records)
    export_outputs(df, OUTPUT_DIR)
    with pd.option_context("display.max_columns", None, "display.width", None, "display.max_colwidth", 48):
        print("\n--- Table preview (console) ---\n")
        print(df.to_string(index=False))
    print(f"\nPipeline complete. Extracted {len(df)} rows.")


if __name__ == "__main__":
    run_pipeline()
