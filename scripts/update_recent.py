#!/usr/bin/env python3
"""Update the "currently working on" section of README.md from GitHub's API.

Fetches the user's public repositories ordered by most recent push, then the
latest commit on each repo's default branch. Only the block between the
<!-- RECENT:START --> and <!-- RECENT:END --> markers is rewritten, so the
rest of the README stays untouched.
"""

import json
import html
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = os.environ.get("GH_USERNAME", "coldfinity")
MAX_ITEMS = 5
README = Path(__file__).resolve().parent.parent / "README.md"
START = "<!-- RECENT:START -->"
END = "<!-- RECENT:END -->"


def api(path: str):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-readme-bot",
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


def collect() -> list[str]:
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
        name = html.escape(name)
        message = html.escape(message)
        age = html.escape(when(commit["commit"]["committer"]["date"]))
        items.append(
            f'<li><a href="{repo["html_url"]}">'
            f'<font color="#eef6ee">{name}</font></a> '
            f'<font color="#d6e8d6">— {message} · {age}</font></li>'
        )
        if len(items) >= MAX_ITEMS:
            break
    return items or ['<li><font color="#d6e8d6">no public commits right now</font></li>']


def main() -> None:
    readme = README.read_text()
    if START not in readme or END not in readme:
        sys.exit(f"missing markers {START!r}/{END!r} in {README}")

    block = "\n".join(collect())
    updated = re.sub(
        rf"(?s){re.escape(START)}.*?{re.escape(END)}",
        f"{START}\n{block}\n{END}",
        readme,
        count=1,
    )
    if updated != readme:
        README.write_text(updated)
        print("README updated")
    else:
        print("README already up to date")


if __name__ == "__main__":
    main()
