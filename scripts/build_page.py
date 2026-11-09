#!/usr/bin/env python3
"""Фаза 2: data/digest.json -> docs/<date>/index.html + docs/index.html (архив)."""
import json, sys
from pathlib import Path
from jinja2 import Template

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
DIGEST = ROOT / "data" / "digest.json"


def main() -> int:
    data = json.loads(DIGEST.read_text(encoding="utf-8"))
    d = data["date"]
    issue_dir = DOCS / d
    issue_dir.mkdir(parents=True, exist_ok=True)

    missing = [it["id"] for it in data["items"]
               if not (issue_dir / "img" / f"{it['id']}.png").exists()]
    if missing:
        print(f"WARN: нет картинок для {missing} — сначала запустите gen_image.py", file=sys.stderr)

    html = Template((ROOT / "templates" / "digest.html.j2").read_text(encoding="utf-8")) \
        .render(date=d, items=data["items"])
    (issue_dir / "index.html").write_text(html, encoding="utf-8")

    issues = sorted((p.name for p in DOCS.iterdir()
                     if p.is_dir() and (p / "index.html").exists()), reverse=True)
    index = Template((ROOT / "templates" / "index.html.j2").read_text(encoding="utf-8")) \
        .render(issues=issues)
    (DOCS / "index.html").write_text(index, encoding="utf-8")

    print(f"OK: docs/{d}/index.html + архив ({len(issues)} вып.)")
    print(f"preview: python -m http.server 8000 -d docs  ->  http://localhost:8000/{d}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())