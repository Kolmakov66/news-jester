#!/usr/bin/env python3
"""Фаза 1: свежие новости из RSS -> data/news.json (через requests)."""
import argparse, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
import requests
import feedparser

FEEDS = [
    "https://news.google.com/rss?hl=ru",
    "https://habr.com/ru/rss/news/",
    "https://lenta.ru/rss/news",
    "https://www.theverge.com/rss/index.xml",
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
}
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "news.json"
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")


def clean_html(t: str) -> str:
    return SPACE_RE.sub(" ", TAG_RE.sub(" ", t or "")).strip()


def fetch_feed(url: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as exc:
        print(f"  SKIP {url}: {exc}", file=sys.stderr)
        return None
    if not feed.entries:
        print(f"  SKIP {url}: пустой", file=sys.stderr)
        return None
    return feed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--feed", default=None, help="один фид URL (по умолчанию перебирается список)")
    p.add_argument("--max-age", type=int, default=24, help="макс. возраст новости, часов")
    p.add_argument("--limit", type=int, default=15)
    a = p.parse_args()

    urls = [a.feed] if a.feed else FEEDS
    feed = used = None
    for url in urls:
        print(f"TRY {url}")
        feed = fetch_feed(url)
        if feed:
            used = url
            break
    if feed is None:
        print("ERROR: ни один фид не ответил", file=sys.stderr)
        return 1

    now = datetime.now(timezone.utc)
    items, seen = [], set()
    for e in feed.entries:
        st = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
        if st is None:
            continue
        pub = datetime(*st[:6], tzinfo=timezone.utc)
        age_h = (now - pub).total_seconds() / 3600
        if age_h > a.max_age:
            continue
        title = clean_html(e.get("title", ""))
        key = hashlib.md5(re.sub(r"\W+", "", title.lower()).encode()).hexdigest()
        if not title or key in seen:
            continue
        seen.add(key)
        src = e.get("source")
        items.append({
            "id": key,
            "title": title,
            "url": e.get("link", ""),
            "source": clean_html(src.get("title", "")) if isinstance(src, dict)
                      else urlparse(used).netloc,
            "published_at": pub.isoformat(),
            "age_hours": round(age_h, 1),
            "summary": clean_html(e.get("summary", ""))[:600],
        })
        if len(items) >= a.limit:
            break

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"fetched_at": now.isoformat(), "feed": used, "items": items},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK: кандидатов={len(items)}, feed={used} -> {OUT.relative_to(ROOT)}")
    for it in items:
        print(f"  [{it['age_hours']:>5}h] {it['title'][:80]}")
    if not items:
        print("WARN: фид ответил, но свежих новостей за --max-age нет; попробуйте --max-age 72",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())