#!/usr/bin/env python3
"""Generate the animated matrix contribution graph SVG.

Accepts a GitHub contribution calendar (GraphQL `contributionCalendar` shape,
or a flat list of {"date": "YYYY-MM-DD", "count": N}) and renders a
self-contained animated SVG: the last ~52 weeks of contributions as a grid,
overlaid with falling matrix rain. No external resources — the file works
standalone in any <img> tag.

Usage:
    generate_matrix.py --input contributions.json [--output matrix.svg] [--seed 42]
"""

import argparse
import json
import random
import sys

GLYPHS = list(
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホ"
    "マミムメモヤユヨラリルレロワヲン0123456789"
)

BG = "#0a0f0a"
GRID_EMPTY = "#161b22"
GRID_COLORS = ["#0e4429", "#006d32", "#26a641", "#39d353"]
RAIN_DIM = "#2ea043"
RAIN_HEAD = "#7ef29a"
CAPTION = "#4c8f5f"

CELL = 9
GAP = 2
PITCH = CELL + GAP
MAX_WEEKS = 53
DAYS_PER_WEEK = 7

WIDTH = 800
HEIGHT = 220
GRID_X = 44
GRID_Y = 94
CAPTION_Y = 34
FOOTER_Y = 198
RAIN_X0 = 34
RAIN_PITCH = 20
RAIN_COLS = 37

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def load_days(raw):
    """Normalize the input JSON into a list of day dicts."""
    if isinstance(raw, dict) and "weeks" in raw:
        days = []
        for week in raw["weeks"]:
            for day in week.get("contributionDays", []):
                days.append(day)
        return days
    if isinstance(raw, list):
        return raw
    raise ValueError("unsupported input shape: expected contributionCalendar or list")


def level_of(day, max_count):
    level = day.get("level")
    if level:
        return LEVELS.get(level, 0)
    count = int(day.get("contributionCount", day.get("count", 0)) or 0)
    if count <= 0:
        return 0
    if max_count <= 0:
        return 1
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.5:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def chunk_into_weeks(days):
    """Chunk the day list into GitHub-style weeks (oldest first)."""
    weeks = []
    for i in range(0, len(days), DAYS_PER_WEEK):
        weeks.append(days[i : i + DAYS_PER_WEEK])
    return weeks[-MAX_WEEKS:]


def build_grid(days):
    total = sum(
        int(d.get("contributionCount", d.get("count", 0)) or 0) for d in days
    )
    max_count = max(
        (int(d.get("contributionCount", d.get("count", 0)) or 0) for d in days),
        default=0,
    )
    weeks = chunk_into_weeks(days)
    rows = []
    for w_idx, week in enumerate(weeks):
        for d_idx in range(DAYS_PER_WEEK):
            day = week[d_idx] if d_idx < len(week) else {}
            level = level_of(day, max_count)
            x = GRID_X + w_idx * PITCH
            y = GRID_Y + d_idx * PITCH
            rows.append((x, y, level))
    return rows, total


def build_rain(rng):
    cols = []
    x = RAIN_X0
    for _ in range(RAIN_COLS):
        glyphs = [rng.choice(GLYPHS) for _ in range(rng.randint(2, 5))]
        head = rng.random() < 0.5
        cols.append(
            {
                "x": x,
                "duration": round(rng.uniform(2.5, 5.0), 2),
                "delay": round(rng.uniform(0, 7), 2),
                "head": head,
                "glyphs": glyphs,
            }
        )
        x += RAIN_PITCH
    return cols


def render_svg(days, total, seed):
    rng = random.Random(seed)
    grid, total = build_grid(days)
    rain = build_rain(rng)

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-label="contribution matrix">'
    )
    parts.append(
        "<style>\n"
        "  @keyframes fall {\n"
        "    0%   { transform: translateY(-34px); opacity: 0; }\n"
        "    8%   { opacity: 1; }\n"
        "    88%  { opacity: 1; }\n"
        "    100% { transform: translateY(235px); opacity: 0; }\n"
        "  }\n"
        "  .col {\n"
        "    animation-name: fall;\n"
        "    animation-timing-function: linear;\n"
        "    animation-iteration-count: infinite;\n"
        "    will-change: transform;\n"
        "  }\n"
        "  @keyframes flicker {\n"
        "    0%, 100% { opacity: 1; }\n"
        "    91% { opacity: 0.93; }\n"
        "    93% { opacity: 1; }\n"
        "    96% { opacity: 0.95; }\n"
        "  }\n"
        "  #rain { animation: flicker 4s linear infinite; }\n"
        "  @keyframes gridpulse {\n"
        "    0%, 100% { opacity: 0.55; }\n"
        "    50% { opacity: 0.85; }\n"
        "  }\n"
        "  #grid { animation: gridpulse 6s ease-in-out infinite; }\n"
        "</style>"
    )
    parts.append(f'<rect width="{WIDTH}" height="{HEIGHT}" fill="{BG}"/>')

    parts.append(
        f'<text x="{GRID_X}" y="{CAPTION_Y}" fill="{CAPTION}" font-family="monospace" '
        f'font-size="13">~ last 52 weeks &#183; {total} contributions</text>'
    )
    parts.append(
        f'<text x="{WIDTH - GRID_X}" y="{CAPTION_Y}" fill="{CAPTION}" '
        f'font-family="monospace" font-size="13" text-anchor="end">matrix // coldfinity@github</text>'
    )

    parts.append(f'<g id="grid" fill="{GRID_EMPTY}">')
    for x, y, level in grid:
        if level > 0:
            parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{GRID_COLORS[level - 1]}"/>')
        else:
            parts.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}"/>')
    parts.append("</g>")

    parts.append(f'<g id="rain">')
    for col in rain:
        style = f"animation-duration:{col['duration']}s;animation-delay:{col['delay']}s"
        parts.append(f'<g class="col" style="{style}">')
        head_fill = RAIN_HEAD if col["head"] else RAIN_DIM
        for idx, glyph in enumerate(col["glyphs"]):
            y = idx * 18
            opacity = 0.75 if idx == 0 else round(rng.uniform(0.1, 0.4), 2)
            fill = head_fill if idx == 0 else RAIN_DIM
            parts.append(
                f'<text x="{col["x"]}" y="{y}" fill="{fill}" opacity="{opacity}" '
                f'font-family="monospace" font-size="14">{glyph}</text>'
            )
        parts.append("</g>")
    parts.append("</g>")

    parts.append(
        f'<text x="{GRID_X}" y="{FOOTER_Y}" fill="{CAPTION}" font-family="monospace" '
        f'font-size="12">$ matrix --auto-update  nightly  </text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="path to contributions JSON")
    parser.add_argument("--output", default="-", help="output SVG path (default: stdout)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for the rain")
    args = parser.parse_args(argv)

    with open(args.input, encoding="utf-8") as fh:
        raw = json.load(fh)
    days = load_days(raw)
    if not days:
        print("error: no contribution days found in input", file=sys.stderr)
        return 1

    svg = render_svg(days, 0, args.seed)
    if args.output == "-":
        print(svg)
    else:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print(f"wrote {args.output} ({len(days)} days)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
