"""
Scrapes baseball-reference birthday data and checks player vitality.
"""

import logging
import time

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
BASE_URL = "https://www.baseball-reference.com"


def _fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def _is_player_alive(player_url: str) -> bool:
    """Fetch a player's page and return False if a death date is present."""
    try:
        html = _fetch(BASE_URL + player_url)
        return 'id="necro-death"' not in html
    except Exception as e:
        log.warning("Could not fetch player page %s: %s", player_url, e)
        return True  # assume alive if we can't check


def get_top_birthday_players(limit: int = 10) -> list[dict]:
    """
    Returns the top `limit` players by career WAR whose birthday is today.
    Each entry: {name, birth_year, war, is_alive}
    """
    html = _fetch(BASE_URL + "/friv/birthdays.cgi")
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", id="birthday_stats")
    if not table:
        raise RuntimeError("Could not find birthday_stats table on baseball-reference")

    players = []
    for row in table.find("tbody").find_all("tr"):
        # Skip mid-table header rows
        if "thead" in row.get("class", []):
            continue

        name_cell = row.find("td", {"data-stat": "player"})
        birth_cell = row.find("td", {"data-stat": "birth_year"})
        war_cell = row.find("td", {"data-stat": "WAR"})

        if not name_cell or not birth_cell:
            continue

        link = name_cell.find("a")
        if not link:
            continue

        name = link.get_text(strip=True).strip("*#+").strip()
        player_url = link.get("href", "")

        try:
            birth_year = int(birth_cell.get_text(strip=True))
        except ValueError:
            continue

        try:
            war = float(war_cell.get_text(strip=True))
        except (ValueError, AttributeError):
            war = 0.0

        players.append({
            "name": name,
            "birth_year": birth_year,
            "war": war,
            "player_url": player_url,
        })

    players.sort(key=lambda p: p["war"], reverse=True)
    top = players[:limit]

    for i, player in enumerate(top):
        log.info("Checking vitality: %s", player["name"])
        player["is_alive"] = _is_player_alive(player["player_url"])
        if i < len(top) - 1:
            time.sleep(0.5)

    return top
