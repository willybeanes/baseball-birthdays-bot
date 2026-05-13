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


def _parse_all_players() -> list[dict]:
    """
    Fetches the birthdays page and returns every player row sorted by WAR desc.
    Does NOT check vitality — call check_vitality() on individual players.
    Each entry: {name, birth_year, war, player_url}
    """
    html = _fetch(BASE_URL + "/friv/birthdays.cgi")
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", id="birthday_stats")
    if not table:
        raise RuntimeError("Could not find birthday_stats table on baseball-reference")

    players = []
    for row in table.find("tbody").find_all("tr"):
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
    return players


def check_vitality(player: dict) -> bool:
    """Fetch a player's page and return True if they are alive."""
    log.info("Checking vitality: %s", player["name"])
    alive = _is_player_alive(player["player_url"])
    time.sleep(0.5)
    return alive


def get_birthday_players(top_n: int = 7, other_active: int = 3) -> tuple[list[dict], list[dict]]:
    """
    Returns two lists:
      - top: the top `top_n` players by WAR (any status), with is_alive set
      - others: the next `other_active` alive players by WAR not already in top

    Each entry: {name, birth_year, war, is_alive}
    """
    all_players = _parse_all_players()

    # Check vitality for the top N
    top = all_players[:top_n]
    for player in top:
        player["is_alive"] = check_vitality(player)

    top_urls = {p["player_url"] for p in top}

    # Walk remaining players by WAR, checking vitality until we have enough alive ones
    others = []
    for player in all_players[top_n:]:
        if player["player_url"] in top_urls:
            continue
        player["is_alive"] = check_vitality(player)
        if player["is_alive"]:
            others.append(player)
        if len(others) == other_active:
            break

    return top, others
