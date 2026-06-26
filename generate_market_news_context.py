from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from typing import Any

from market_wrap_common import load_json, write_json


USER_AGENT = "Mozilla/5.0"
UTC = dt.timezone.utc
GOOGLE_NEWS_BASE = "https://news.google.com/rss/search"
SOURCE_PRIORITY = {"Reuters": 0, "AP": 1, "The Associated Press": 1, "Guardian": 2, "MarketWatch": 3}
QUERY_MAP = {
    "us": [
        '("Wall Street" OR "US stocks" OR "S&P 500" OR Nasdaq OR Dow) (Reuters OR AP OR Guardian OR MarketWatch) when:2d',
        '(semiconductors OR AI OR yields OR oil) ("US stocks" OR Nasdaq OR "S&P 500") (Reuters OR AP OR Guardian OR MarketWatch) when:2d',
    ],
    "europe": [
        '("European shares" OR FTSE OR DAX OR CAC OR "STOXX 600") (Reuters OR AP OR Guardian OR MarketWatch) when:2d',
        '(oil OR rates OR euro OR bunds) (FTSE OR DAX OR CAC OR "European shares") (Reuters OR AP OR Guardian OR MarketWatch) when:2d',
    ],
}
BOILERPLATE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"sign up for",
        r"newsletter",
        r"all rights reserved",
        r"cookie",
        r"advertisement",
        r"skip to main content",
        r"watch live",
        r"follow us on",
    ]
]


class ParagraphExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._capture_depth = 0
        self._buffer: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "li", "h2"}:
            self._capture_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "li", "h2"} and self._capture_depth > 0:
            self._capture_depth -= 1
            text = self._normalize("".join(self._buffer))
            self._buffer.clear()
            if len(text) >= 60 and not self._looks_like_boilerplate(text):
                self.paragraphs.append(text)

    def handle_data(self, data: str) -> None:
        if self._capture_depth > 0:
            self._buffer.append(data)

    @staticmethod
    def _normalize(text: str) -> str:
        text = html.unescape(text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _looks_like_boilerplate(text: str) -> bool:
        return any(pattern.search(text) for pattern in BOILERPLATE_PATTERNS)


def parse_args() -> argparse.Namespace:
    root = pathlib.Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--market", choices=["all", "us", "europe"], default="all")
    parser.add_argument("--output-dir", default=str(root / "output"))
    return parser.parse_args()


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_bytes(url: str) -> tuple[str, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.geturl(), response.read()


def parse_google_rss(query: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
    rss_text = fetch_text(f"{GOOGLE_NEWS_BASE}?{params}")
    root = ET.fromstring(rss_text)
    items: list[dict[str, Any]] = []

    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        description = re.sub(r"\s+", " ", html.unescape(description)).strip()
        pub_date_raw = (item.findtext("pubDate") or "").strip()
        source_node = item.find("source")
        source_name = (source_node.text or "").strip() if source_node is not None and source_node.text else "Unknown"

        published_at = None
        if pub_date_raw:
            published_at = email.utils.parsedate_to_datetime(pub_date_raw).astimezone(UTC)

        items.append(
            {
                "title": title,
                "google_news_url": link,
                "description": description,
                "published_at": published_at.isoformat() if published_at else None,
                "source_name": source_name,
            }
        )

    return items


def normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def extract_article_text(page_html: str) -> tuple[str, bool]:
    parser = ParagraphExtractor()
    parser.feed(page_html)
    paragraphs = parser.paragraphs
    used_description_fallback = False

    if not paragraphs:
        meta_match = re.search(
            r'<meta[^>]+(?:property|name)=["\'](?:og:description|description)["\'][^>]+content=["\']([^"\']+)["\']',
            page_html,
            flags=re.IGNORECASE,
        )
        if meta_match:
            paragraphs = [html.unescape(meta_match.group(1))]
            used_description_fallback = True

    excerpt_parts: list[str] = []
    total_length = 0
    for paragraph in paragraphs:
        excerpt_parts.append(paragraph)
        total_length += len(paragraph)
        if total_length >= 900 or len(excerpt_parts) >= 4:
            break

    return "\n".join(excerpt_parts).strip(), used_description_fallback


def prioritize_articles(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def sort_key(item: dict[str, Any]) -> tuple[int, str]:
        source_name = item.get("source_name", "Unknown")
        published_at = item.get("published_at") or ""
        return (SOURCE_PRIORITY.get(source_name, 99), published_at)

    return sorted(items, key=sort_key)


def derive_context_stem(payload: dict[str, Any]) -> str:
    return "us_market_news_context" if payload["marketKey"] == "us" else "europe_market_news_context"


def collect_market_context(payload: dict[str, Any]) -> dict[str, Any]:
    market_key = payload["marketKey"]
    candidates: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()

    for query in QUERY_MAP[market_key]:
        for item in parse_google_rss(query):
            dedupe_key = (item["title"].casefold(), item["source_name"].casefold())
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            candidates.append(item)

    articles: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for item in prioritize_articles(candidates):
        if len(articles) >= 5:
            break

        try:
            resolved_url, page_bytes = fetch_bytes(item["google_news_url"])
        except Exception:
            continue

        normalized_url = normalize_url(resolved_url)
        if normalized_url in seen_urls:
            continue

        page_html = page_bytes.decode("utf-8", errors="ignore")
        excerpt, used_description_fallback = extract_article_text(page_html)
        if len(excerpt) < 160:
            description = item.get("description", "")
            if len(description) < 120:
                continue
            excerpt = description
            used_description_fallback = True

        seen_urls.add(normalized_url)
        articles.append(
            {
                "title": item["title"],
                "source_name": item["source_name"],
                "url": resolved_url,
                "published_at": item.get("published_at"),
                "excerpt": excerpt,
                "used_description_fallback": used_description_fallback,
            }
        )

    return {
        "marketKey": market_key,
        "summaryDate": payload["summaryDate"],
        "generatedAt": dt.datetime.now(UTC).isoformat(),
        "articles": articles,
        "fallbackUsed": len(articles) < 2,
    }


def write_context(output_dir: pathlib.Path, payload: dict[str, Any], context: dict[str, Any]) -> None:
    stem = derive_context_stem(payload)
    dated_path = output_dir / f"{payload['summaryDate']}_{stem}.json"
    latest_path = output_dir / f"latest_{stem}.json"
    write_json(dated_path, context)
    write_json(latest_path, context)


def main() -> None:
    args = parse_args()
    output_dir = pathlib.Path(args.output_dir)
    markets = ["us", "europe"] if args.market == "all" else [args.market]

    for market_key in markets:
        payload_stem = "latest_us_market_wrap.json" if market_key == "us" else "latest_europe_market_snapshot.json"
        payload = load_json(output_dir / payload_stem)

        try:
            context = collect_market_context(payload)
        except Exception as exc:
            context = {
                "marketKey": payload["marketKey"],
                "summaryDate": payload["summaryDate"],
                "generatedAt": dt.datetime.now(UTC).isoformat(),
                "articles": [],
                "fallbackUsed": True,
                "error": str(exc),
            }

        write_context(output_dir, payload, context)
        print(f"Generated news context for {market_key}: {len(context.get('articles', []))} article(s)")


if __name__ == "__main__":
    main()
