#!/usr/bin/env python3
"""Фаза 2: карикатуры выпуска: data/digest.json -> docs/<date>/img/<id>.png"""
import base64, json, os, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
DIGEST = ROOT / "data" / "digest.json"

# Стиль ЗАФИКСИРОВАН здесь, а не в промптах агента: все карикатуры выпуска цельные.
STYLE = ("flat vector editorial caricature, minimalist shapes, soft pastel palette, "
         "clean outlines, single humorous metaphor scene, no readable text, "
         "no letters, no logos, 16:9")


def gen_pollinations(prompt: str, out: Path):
    url = "https://image.pollinations.ai/prompt/" + requests.utils.quote(prompt)
    r = requests.get(url, params={"width": 1280, "height": 720, "model": "flux",
                                  "nologo": "true", "seed": 42}, timeout=240)
    r.raise_for_status()
    out.write_bytes(r.content)


def gen_openai(prompt: str, out: Path):
    r = requests.post("https://api.openai.com/v1/images/generations",
                      headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                      json={"model": "gpt-image-1", "prompt": prompt, "size": "1536x1024"},
                      timeout=300)
    r.raise_for_status()
    out.write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))


def main() -> int:
    data = json.loads(DIGEST.read_text(encoding="utf-8"))
    img_dir = ROOT / "docs" / data["date"] / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    provider = "openai" if os.environ.get("OPENAI_API_KEY") else "pollinations"
    gen = gen_openai if provider == "openai" else gen_pollinations
    print(f"provider={provider}")

    for it in data["items"]:
        out = img_dir / f"{it['id']}.png"
        if out.exists() and out.stat().st_size > 10_000:
            print(f"  SKIP {it['id']} (уже есть)")
            continue
        prompt = STYLE + ", scene: " + it["image_prompt"]
        for attempt in (1, 2, 3):
            try:
                gen(prompt, out)
                print(f"  OK   {it['id']} -> {out.relative_to(ROOT)} ({out.stat().st_size//1024} KB)")
                break
            except Exception as exc:
                print(f"  retry {attempt}: {exc}", file=sys.stderr)
                time.sleep(5 * attempt)
        else:
            print(f"ERROR: {it['id']} не сгенерировался", file=sys.stderr)
            return 1
        time.sleep(2)  # вежливая пауза для бесплатного провайдера
    return 0


if __name__ == "__main__":
    sys.exit(main())