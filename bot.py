"""
Baseball Birthdays Bot — posts today's top 10 birthday players (by WAR) to Bluesky.
Run once via cron at 9AM: python bot.py
Dry-run test: DRY_RUN=1 python bot.py
"""

import logging
import os
import sys
from datetime import date

from dotenv import load_dotenv

import scraper
import bluesky_client

load_dotenv()

DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
BREF_URL = "https://www.baseball-reference.com/friv/birthdays.cgi"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def build_post(players: list[dict]) -> str:
    today = date.today()
    lines = []
    for p in players:
        if p["is_alive"]:
            age = today.year - p["birth_year"]
            lines.append(f"{p['name']} ({age})")
        else:
            lines.append(p["name"])

    text = "\n".join(lines)
    text += f"\n\nSee more here {BREF_URL}"

    # Bluesky limit is 300 graphemes; trim players from the bottom if needed
    while len(text) > 300 and len(lines) > 1:
        lines.pop()
        text = "\n".join(lines) + f"\n\nSee more here {BREF_URL}"

    return text


def main() -> None:
    if DRY_RUN:
        log.info("=== DRY RUN — no post will be sent ===")

    log.info("Fetching birthday data from Baseball Reference...")
    try:
        players = scraper.get_top_birthday_players(limit=10)
    except Exception as e:
        log.error("Failed to fetch birthday data: %s", e, exc_info=True)
        sys.exit(1)

    if not players:
        log.warning("No players found for today")
        sys.exit(0)

    for p in players:
        status = f"alive, born {p['birth_year']}" if p["is_alive"] else "deceased"
        log.info("  %-30s  WAR=%5.1f  %s", p["name"], p["war"], status)

    post_text = build_post(players)
    log.info("Post (%d chars):\n%s", len(post_text), post_text)

    bluesky_client.post_with_link(post_text, BREF_URL, dry_run=DRY_RUN)


if __name__ == "__main__":
    main()
