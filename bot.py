"""
Baseball Birthdays Bot — posts today's top 7 birthday players (by WAR) plus
up to 3 additional active players to Bluesky.
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


def _format_player(p: dict) -> str:
    if p["is_alive"]:
        age = date.today().year - p["birth_year"]
        return f"{p['name']} ({age})"
    return p["name"]


def build_post(top: list[dict], others: list[dict]) -> str:
    lines = [_format_player(p) for p in top]
    text = "\n".join(lines)

    if others:
        text += "\n\nOther Active Players:\n"
        text += "\n".join(_format_player(p) for p in others)

    text += f"\n\nSee more here {BREF_URL}"

    # Bluesky limit is 300 graphemes; trim others first, then top if needed
    while len(text) > 300 and others:
        others.pop()
        text = build_post(top, others)  # rebuild cleanly

    while len(text) > 300 and len(top) > 1:
        top.pop()
        text = build_post(top, others)

    return text


def main() -> None:
    if DRY_RUN:
        log.info("=== DRY RUN — no post will be sent ===")

    log.info("Fetching birthday data from Baseball Reference...")
    try:
        top, others = scraper.get_birthday_players(top_n=7, other_active=3)
    except Exception as e:
        log.error("Failed to fetch birthday data: %s", e, exc_info=True)
        sys.exit(1)

    if not top:
        log.warning("No players found for today")
        sys.exit(0)

    log.info("Top 7 by WAR:")
    for p in top:
        status = f"alive, born {p['birth_year']}" if p["is_alive"] else "deceased"
        log.info("  %-30s  WAR=%5.1f  %s", p["name"], p["war"], status)

    log.info("Other active players:")
    for p in others:
        log.info("  %-30s  WAR=%5.1f  born %d", p["name"], p["war"], p["birth_year"])

    post_text = build_post(top, others)
    log.info("Post (%d chars):\n%s", len(post_text), post_text)

    bluesky_client.post_with_link(post_text, BREF_URL, dry_run=DRY_RUN)


if __name__ == "__main__":
    main()
