"""Find chord pages on Ultimate Guitar for a song title + artist.

Uses Ultimate Guitar's own search page (no account or key needed), which
embeds its results as JSON. Only "Chords" sheets are kept (tabs, Guitar Pro,
Power, Official and Pro versions can't be shown as chords over lyrics), and
only those whose title has every word of the song's title and whose artist
has every word of the artist, when one is given.

Each result carries Ultimate Guitar's version number ("ver 3" on the site),
its votes and rating, and whether it is a live performance: Ultimate Guitar
numbers live versions separately, so two results can share a number.
"""

import html
import json
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass

from .fetch import FetchError, download

MAX_RESULTS = 8
MAX_PAGES = 3  # search result pages read (50 results each)


@dataclass
class Result:
    url: str
    artist: str
    song: str
    version: int = 1
    votes: int = 0
    rating: float = 0.0
    live: bool = False

    site_name = "Ultimate Guitar"

    @property
    def label(self):
        text = f"{self.artist} - {self.song} (ver {self.version}{', live' if self.live else ''})"
        return text + (f", rated {self.rating:.1f} by {self.votes}" if self.votes else "")


def plain_words(text):
    text = unicodedata.normalize("NFD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return [w for w in re.split(r"[^a-z0-9]+", text) if len(w) > 2 or w.isdigit()]


def search_page(query, page=1):
    """(results as Ultimate Guitar gives them, number of pages)."""
    url = "https://www.ultimate-guitar.com/search.php?search_type=title&value=" + urllib.parse.quote(query)
    if page > 1:
        url += f"&page={page}"
    try:
        text = download(url)
    except FetchError as e:
        if "404" in str(e):  # Ultimate Guitar answers "nothing found" with a 404
            return [], 0
        raise
    store = re.search(r'class="js-store"\s+data-content="([^"]*)"', text)
    if not store:
        return [], 0
    try:
        data = json.loads(html.unescape(store.group(1)))["store"]["page"]["data"]
        return data.get("results") or [], (data.get("pagination") or {}).get("total") or 1
    except (KeyError, TypeError, json.JSONDecodeError):
        return [], 0


def to_result(raw):
    performance = (raw.get("recording") or {}).get("performance")
    return Result(
        url=raw["tab_url"],
        artist=raw.get("artist_name") or "",
        song=raw.get("song_name") or "",
        version=raw.get("version") or 1,
        votes=raw.get("votes") or 0,
        rating=raw.get("rating") or 0.0,
        live=bool(performance),
    )


def chord_results(title, artist="", query=None, stop=None):
    """Every matching Chords result, reading up to MAX_PAGES pages of the search
    for `query` (default "artist title"). `stop(results)` ends the reading early."""
    title_words, artist_words = plain_words(title), plain_words(artist)
    results, seen = [], set()
    query = query or f"{artist} {title}".strip()
    page, pages = 1, 1
    while page <= min(pages, MAX_PAGES):
        found, pages = search_page(query, page)
        for raw in found:
            if raw.get("type") != "Chords" or not raw.get("tab_url") or raw["tab_url"] in seen:
                continue
            if raw.get("tab_access_type") not in (None, "public"):
                continue
            result = to_result(raw)
            if not all(w in plain_words(result.song) for w in title_words):
                continue
            if artist_words and not all(w in plain_words(result.artist) for w in artist_words):
                continue
            seen.add(result.url)
            results.append(result)
        if stop and stop(results):
            break
        page += 1
    return results


def best_first(results, title):
    """Exact title first, studio before live, then most votes."""
    title_words = plain_words(title)
    return sorted(results, key=lambda r: (plain_words(r.song) != title_words, r.live, -r.votes))


def search(title, artist=""):
    """Best chord pages for the song, best first. When "artist title" finds
    nothing, the title alone is searched (Ultimate Guitar may spell the artist
    differently)."""
    results = chord_results(title, artist, stop=lambda found: len(found) >= MAX_RESULTS)
    if not results and artist:
        results = chord_results(title, artist, query=title, stop=lambda found: len(found) >= MAX_RESULTS)
    return best_first(results, title)[:MAX_RESULTS]


def find_versions(title, artist, version=None):
    """(the wanted version or None, every matching chord page best first).

    `version` is Ultimate Guitar's version number; when two pages share it,
    the studio one (not live) with the most votes is taken."""

    def has_version(found):
        return version is not None and any(r.version == version and not r.live for r in found)

    results = chord_results(title, artist, stop=has_version)
    if not results and artist:
        results = chord_results(title, artist, query=title, stop=has_version)
    ordered = best_first(results, title)
    title_words = plain_words(title)
    wanted = None
    if version is not None:
        same = [r for r in ordered if r.version == version and plain_words(r.song) == title_words]
        wanted = same[0] if same else None
    return wanted, ordered
