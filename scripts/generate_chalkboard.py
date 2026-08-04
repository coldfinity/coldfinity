#!/usr/bin/env python3
"""Generate a chalkboard SVG profile with the latest public commits.

Fetches the user's public repositories ordered by most recent push, then the
latest commit on each repo's default branch, and draws the whole profile as a
chalkboard: wood frame, textured green board, and chalk text. The texture is
built from plain SVG primitives (no filters) so GitHub renders it reliably.

Usage:
    generate_chalkboard.py [--output assets/chalkboard.svg]
"""

import argparse
import html
import json
import os
import random
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = os.environ.get("GH_USERNAME", "coldfinity")
MAX_ITEMS = 5
W, H = 1200, 1560
CX = W / 2

CHALK_FONT = "'Chalkboard SE', 'Chalkboard', 'Comic Sans MS', 'Segoe Print', 'Bradley Hand', cursive"
MONO_FONT = "'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', 'Menlo', 'Consolas', monospace"

CHALK = "#f2efe6"
CHALK_SOFT = "#d8e6d8"
CHALK_DIM = "#a9c9a9"
CHALK_YELLOW = "#f0d78c"


def api(path: str):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-chalkboard",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def when(iso: str) -> str:
    pushed = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - pushed).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    return f"{days} days ago"


def fetch_items() -> list[dict]:
    items = []
    repos = api(f"/users/{USER}/repos?sort=pushed&per_page=8")
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        name = repo["name"]
        if name == USER:  # skip the profile repo itself
            continue
        commits = api(f"/repos/{repo['full_name']}/commits?per_page=1")
        if not commits:
            continue
        commit = commits[0]
        message = commit["commit"]["message"].splitlines()[0].strip()
        if len(message) > 58:
            message = message[:55].rstrip() + "..."
        items.append(
            {
                "name": name,
                "url": repo["html_url"],
                "message": message,
                "age": when(commit["commit"]["committer"]["date"]),
            }
        )
        if len(items) >= MAX_ITEMS:
            break
    return items


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def wrap_words(text: str, size: int, max_width: int) -> list[str]:
    """Rough word-wrap using an average glyph width of ~0.5 * font size."""
    max_chars = max(int(max_width / (0.5 * size)), 12)
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > max_chars:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def text(
    x: float,
    y: float,
    s: str,
    size: int = 26,
    fill: str = CHALK,
    font: str = CHALK_FONT,
    weight: str = "normal",
    anchor: str = "middle",
    opacity: float = 0.92,
    italic: bool = False,
) -> str:
    style = f'font-style="italic"' if italic else ""
    return (
        f'<text x="{x:.0f}" y="{y:.0f}" font-family="{font}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
        f'fill-opacity="{opacity}" {style}>{esc(s)}</text>'
    )


def wood_grain() -> str:
    rng = random.Random(3)
    parts = []
    for _ in range(26):
        x = rng.uniform(20, 1180)
        y = rng.uniform(20, 1520)
        w = rng.uniform(1, 3)
        h = rng.uniform(60, 240)
        op = rng.uniform(0.04, 0.11)
        parts.append(
            f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.1f}" height="{h:.0f}" '
            f'fill="#2a1508" fill-opacity="{op:.2f}"/>'
        )
    return "\n".join(parts)


def board_texture() -> str:
    rng = random.Random(11)
    parts = []
    for _ in range(650):
        x = rng.uniform(72, 1128)
        y = rng.uniform(72, 1468)
        r = rng.uniform(0.4, 1.5)
        op = rng.uniform(0.03, 0.10)
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{CHALK}" '
            f'fill-opacity="{op:.3f}"/>'
        )
    return "\n".join(parts)


def smudges() -> str:
    rng = random.Random(7)
    parts = []
    for _ in range(14):
        x = rng.uniform(180, 1020)
        y = rng.uniform(140, 1400)
        rx = rng.uniform(70, 230)
        ry = rng.uniform(8, 34)
        rot = rng.uniform(-24, 24)
        op = rng.uniform(0.015, 0.045)
        parts.append(
            f'<ellipse cx="{x:.0f}" cy="{y:.0f}" rx="{rx:.0f}" ry="{ry:.0f}" '
            f'transform="rotate({rot:.0f} {x:.0f} {y:.0f})" fill="{CHALK}" '
            f'fill-opacity="{op:.3f}"/>'
        )
    return "\n".join(parts)


def streaks() -> str:
    rng = random.Random(13)
    parts = []
    for _ in range(10):
        y = rng.uniform(90, 1450)
        x1 = rng.uniform(80, 220)
        x2 = rng.uniform(980, 1120)
        w = rng.uniform(1, 3)
        op = rng.uniform(0.015, 0.035)
        parts.append(
            f'<line x1="{x1:.0f}" y1="{y:.0f}" x2="{x2:.0f}" y2="{y:.0f}" '
            f'stroke="{CHALK}" stroke-width="{w:.1f}" stroke-opacity="{op:.3f}"/>'
        )
    return "\n".join(parts)


def screws() -> str:
    rng = random.Random(17)
    parts = []
    for x, y in [(52, 52), (1148, 52), (52, 1492), (1148, 1492)]:
        parts.append(
            f'<circle cx="{x}" cy="{y}" r="9" fill="#d7c79d" stroke="#6f4f2a" stroke-width="2"/>'
        )
        ang = rng.uniform(0, 90)
        dx = 5 * (1 if rng.random() < 0.5 else -1)
        parts.append(
            f'<line x1="{x - dx}" y1="{y}" x2="{x + dx}" y2="{y}" '
            f'stroke="#6f4f2a" stroke-width="2" transform="rotate({ang:.0f} {x} {y})"/>'
        )
    return "\n".join(parts)


def chalk_pieces() -> str:
    pieces = [
        (420, 1487, 62, 9, CHALK),
        (494, 1488, 72, 9, CHALK_YELLOW),
        (576, 1487, 54, 9, CHALK_SOFT),
        (880, 1488, 66, 9, CHALK),
    ]
    parts = []
    for x, y, w, h, color in pieces:
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{color}" '
            f'fill-opacity="0.95" transform="rotate({random.Random(x).uniform(-5, 5):.1f} {x + w / 2:.0f} {y + h / 2:.0f})"/>'
        )
    return "\n".join(parts)


def render_items(items: list[dict]) -> str:
    if not items:
        return text(210, 800, "no public commits right now", size=22, anchor="start", fill=CHALK_SOFT)
    parts = []
    y = 800
    for item in items:
        name = esc(item["name"])
        detail = f"{esc(item['message'])} · {esc(item['age'])}"
        parts.append(
            f'<text x="210" y="{y}" font-family="{CHALK_FONT}" font-size="22" '
            f'text-anchor="start" fill-opacity="0.92">'
            f'<tspan fill="{CHALK}">▸ </tspan>'
            f'<tspan font-weight="bold" fill="{CHALK_YELLOW}">{name}</tspan>'
            f'<tspan fill="{CHALK_SOFT}"> — {detail}</tspan>'
            f'</text>'
        )
        y += 76
    return "\n".join(parts)


def build_svg(items: list[dict]) -> str:
    defn = []
    definition = wrap_words(
        "n. the limit of a system as its temperature approaches absolute zero "
        "— also, a mathematician who never stopped coding",
        24,
        820,
    )
    def_lines = "\n".join(
        text(CX, 236 + i * 32, line, size=24, fill=CHALK_SOFT)
        for i, line in enumerate(definition)
    )

    body = f"""
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <defs>
    <linearGradient id="wood" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#7a5230"/>
      <stop offset="0.22" stop-color="#8f6338"/>
      <stop offset="0.5" stop-color="#744e2c"/>
      <stop offset="0.78" stop-color="#8f6338"/>
      <stop offset="1" stop-color="#6f4828"/>
    </linearGradient>
    <linearGradient id="trayWood" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#8f6338"/>
      <stop offset="1" stop-color="#5d3c20"/>
    </linearGradient>
    <radialGradient id="board" cx="0.5" cy="0.42" r="0.85">
      <stop offset="0" stop-color="#2a5540"/>
      <stop offset="0.55" stop-color="#1f422f"/>
      <stop offset="1" stop-color="#122a1d"/>
    </radialGradient>
    <radialGradient id="vignette" cx="0.5" cy="0.45" r="0.82">
      <stop offset="0.58" stop-color="#000000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0.30"/>
    </radialGradient>
  </defs>

  <rect x="18" y="18" width="1164" height="1504" rx="10" fill="url(#wood)"/>
  {wood_grain()}
  <rect x="34" y="34" width="1132" height="1472" rx="8" fill="#241409" fill-opacity="0.55"/>
  <rect x="60" y="60" width="1080" height="1420" rx="4" fill="url(#board)"/>
  {board_texture()}
  {streaks()}
  {smudges()}
  <rect x="60" y="60" width="1080" height="1420" rx="4" fill="url(#vignette)"/>

  {text(CX, 150, "cold\u221efinity", size=84, weight="bold", opacity=0.95)}
  {def_lines}

  <text x="{CX}" y="360" font-family="{MONO_FONT}" font-size="34" fill="{CHALK}" text-anchor="middle" fill-opacity="0.94">
    <tspan>lim</tspan><tspan baseline-shift="sub" font-size="20">T → 0</tspan><tspan> S(T) = S</tspan><tspan baseline-shift="sub" font-size="20">0</tspan>
  </text>
  <line x1="430" y1="378" x2="770" y2="378" stroke="{CHALK}" stroke-width="2" stroke-opacity="0.55"/>
  {text(CX, 412, "coldfinity: the state where noise has been frozen out.", size=19, fill=CHALK_DIM)}

  {text(CX, 500, "\u2207 interests", size=30, fill=CHALK_YELLOW, weight="bold")}
  {text(CX, 550, "\u25b8 machine learning", size=24, weight="bold")}
  {text(CX, 582, "models, theory, and the math underneath", size=21, fill=CHALK_SOFT)}
  {text(CX, 636, "\u25b8 quantitative finance", size=24, weight="bold")}
  {text(CX, 668, "statistical arbitrage \u00b7 stochastic processes \u00b7 time series", size=21, fill=CHALK_SOFT)}

  {text(CX, 740, "\u27f6 currently working on", size=30, fill=CHALK_YELLOW, weight="bold")}
  {render_items(items)}

  {text(CX, 1210, "\u25a1 axiom", size=30, fill=CHALK_YELLOW, weight="bold")}
  {text(CX, 1270, "\u201cMarkets are stochastic. Pick your battles.\u201d", size=28, italic=True, opacity=0.95)}
  {text(CX, 1350, "\u2500\u2500\u2500\u2500\u2500\u2500  0 K  \u2500\u2500\u2500\u2500\u2500\u2500", size=18, fill=CHALK_DIM, font=MONO_FONT)}

  <rect x="120" y="1482" width="960" height="26" rx="3" fill="url(#trayWood)"/>
  <rect x="120" y="1482" width="960" height="4" fill="#000000" fill-opacity="0.25"/>
  {chalk_pieces()}
  {screws()}
</svg>
"""
    return body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("assets/chalkboard.svg"))
    args = parser.parse_args()

    items = fetch_items()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_svg(items))
    print(f"wrote {args.output} ({len(items)} recent commits)")


if __name__ == "__main__":
    main()
