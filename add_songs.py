"""Add a whole list of songs from Ultimate Guitar to the book, without questions.

    venv/bin/python add_songs.py Want.txt --report Checked.txt

The list is Ultimate Guitar's list of saved songs ("My tabs"), copied as text:
for each song the artist (left out when it's the same as the song above), the
title, with "(ver N)" for a version other than the first, and the date it was
saved, sometimes followed by the kind of page (Tab, Power, Guitar Pro,
Official):

    Passenger
    Golden Leaves (ver 3)
    Jan 28, 2015
    All The Little Lights
    Feb 9, 2015

Lines "Title - Artist" (no dates) also work.

For each song it:
- skips repeats: a song listed twice by the same artist is added once, from its
  most recently saved line;
- finds that exact version on Ultimate Guitar; if it's gone, or the line is a
  tab / Official page, takes the best rated chords version instead (and says so);
- cleans the song (importer/clean.py), gives it its title and author
  (importer/titles.py, title_fixes.yaml, author_aliases.yaml), tags it
  English or Spanish (importer/language.py), finds a Spotify link (or a
  YouTube one) and writes songs/<title>_<author>.md with the saved date.
Songs already in the book (same title and author) are skipped, so the script
can be run again after an interruption. When it can't add a song it says why.
Then the book is rebuilt once. With --report FILE the results are added to
that file under "claude-added:" and "claude-uncertain:".
"""

import argparse
import datetime
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import yaml

import build
from add_song import alias_for, free_path, load_aliases, slug, song_file
from builder.lyrics import is_chord_line
from builder.songs import SongError, load_song
from importer.clean import clean_song
from importer.fetch import Blocked, FetchError
from importer.language import detect
from importer.read import read_song_any_way
from importer.search import find_versions, plain_words
from importer.sites import SiteError
from importer.spotify import find_tracks
from importer.titles import book_names, load_fixes
from importer.websearch import SearchBusy
from importer.youtube import find_video

MAX_VERSIONS = 4  # chord pages read per song before giving up
MIN_PAIRS = 4  # chord lines over lyrics needed for a page to count
PAUSE = 15  # seconds between songs, so the web search doesn't get busy
WAITS = [60, 300, 900, 1800, 3600]  # seconds to wait when a site says "too many requests"

DATE_RE = re.compile(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})\s*(.*)")
VERSION_RE = re.compile(r"\s*\(ver (\d+)\)\s*$")
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


@dataclass
class Wanted:
    artist: str  # as Ultimate Guitar writes it
    title: str  # as Ultimate Guitar writes it, without "(ver N)"
    version: int | None = None  # None: any version
    added: str | None = None  # ISO date
    kind: str = ""  # "", "Tab", "Power", "Guitar Pro", "Official"...
    line: int = 0

    @property
    def label(self):
        version = f" (ver {self.version})" if self.version and self.version > 1 else ""
        kind = f" [{self.kind}]" if self.kind else ""
        return f"{self.artist} - {self.title}{version}{kind}"


# ---------- reading the list ----------

def iso_date(month, day, year):
    return datetime.date(int(year), MONTHS.index(month) + 1, int(day)).isoformat()


def read_list(path):
    """[Wanted] from Ultimate Guitar's saved-songs list or "Title - Artist" lines."""
    lines = [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines()]
    numbered = [(n, line) for n, line in enumerate(lines, start=1) if line and not line.startswith("#")]
    if not any(DATE_RE.fullmatch(line) for _, line in numbered):
        wanted = []
        for n, line in numbered:
            title, _, artist = line.partition(" - ")
            wanted.append(Wanted(artist.strip(), title.strip(), line=n))
        return wanted

    wanted, block, artist = [], [], ""
    for n, line in numbered:
        date = DATE_RE.fullmatch(line)
        if not date:
            block.append((n, line))
            continue
        if len(block) >= 2:
            artist = block[-2][1]
        if not block or not artist:
            print(f"Line {n}: a date with no song above it, skipped.", file=sys.stderr)
            block = []
            continue
        if len(block) > 2:
            print(f"Lines {block[0][0]}-{block[-3][0]}: not understood, skipped.", file=sys.stderr)
        line_no, title = block[-1]
        version = VERSION_RE.search(title)
        wanted.append(Wanted(
            artist=artist,
            title=VERSION_RE.sub("", title).strip(),
            version=int(version.group(1)) if version else 1,
            added=iso_date(*date.group(1, 2, 3)),
            kind=date.group(4).strip(),
            line=line_no,
        ))
        block = []
    return wanted


def book_key(title, author):
    return " ".join(plain_words(title)), " ".join(plain_words(author))


def names(item, aliases, fixes):
    """(book title, book author) for a list item."""
    title, author = book_names(item.artist, item.title, fixes)
    return title, alias_for(author, aliases)


def without_repeats(wanted, aliases, fixes):
    """One item per song and author: the most recently saved one (the later line
    on the same date). Returns (kept in list order, [(dropped, kept)])."""
    chosen = {}
    for item in wanted:
        key = book_key(*names(item, aliases, fixes))
        best = chosen.get(key)
        if best is None or (item.added or "", item.line) >= (best.added or "", best.line):
            chosen[key] = item
    kept = set(id(item) for item in chosen.values())
    dropped = [(item, chosen[book_key(*names(item, aliases, fixes))]) for item in wanted if id(item) not in kept]
    return [item for item in wanted if id(item) in kept], dropped


# ---------- choosing a version ----------

def chord_pairs(body):
    lines = body.split("\n")
    return sum(1 for i in range(1, len(lines)) if is_chord_line(lines[i - 1]) and lines[i].strip()
               and not is_chord_line(lines[i]))


def patiently(action, what):
    """Run action(); when a site says "too many requests", wait and try again."""
    for wait in WAITS + [None]:
        try:
            return action()
        except (Blocked, SearchBusy) as e:
            if wait is None:
                raise
            print(f"    {what}: {e}; waiting {wait // 60} min", flush=True)
            time.sleep(wait)


def choose(item):
    """(result, draft, cleaned, note) to use, or a reason why not."""
    exact = item.version if not item.kind else None  # tabs / Official: any chords version
    wanted, results = patiently(lambda: find_versions(item.title, item.artist, exact), "Ultimate Guitar search")
    if not results:
        return f'no chords on Ultimate Guitar for "{item.title}" by {item.artist}'
    order = [wanted] + [r for r in results if r is not wanted] if wanted else results
    note = ""
    if item.kind:
        note = f"the list has a {item.kind} page; used chords ver {order[0].version}"
    elif exact and not wanted:
        note = f"ver {exact} not found on Ultimate Guitar; used ver {order[0].version} instead"
    tried = []
    for result in order[:MAX_VERSIONS]:
        try:
            draft = patiently(lambda: read_song_any_way(result.url), "Ultimate Guitar page")
        except (FetchError, SiteError, OSError) as e:
            tried.append(f"ver {result.version}: {e}")
            continue
        cleaned = clean_song(draft.text, draft.marked, ask=lambda line: False)
        if chord_pairs(cleaned.body) < MIN_PAIRS:
            tried.append(f"ver {result.version}: hardly any chords over lyrics")
            continue
        if result is not order[0]:
            note = (note + "; " if note else "") + f"ver {order[0].version} unusable, used ver {result.version}"
        return result, draft, cleaned, note
    return "no usable chords page (" + "; ".join(tried) + ")"


# ---------- writing ----------

def book_songs(songs_dir):
    """{(title words, author words): path} of the songs in the book."""
    found = {}
    for path in songs_dir.glob("*.md"):
        try:
            song = load_song(path)
        except (SongError, yaml.YAMLError):
            continue
        found[book_key(song.title, song.autor or "")] = path
    return found


def find_link(title, artist):
    try:
        tracks = patiently(lambda: find_tracks(title, artist), "web search")
        if tracks:
            return tracks[0].url
        return patiently(lambda: find_video(title, artist), "web search") or ""
    except FetchError:
        return ""


def add_one(item, title, author, songs_dir):
    """('added', path, details) or ('uncertain', None, reason)."""
    try:
        chosen = choose(item)
    except FetchError as e:
        return "uncertain", None, f"Ultimate Guitar didn't answer ({e}); run again later"
    if isinstance(chosen, str):
        return "uncertain", None, chosen
    result, draft, cleaned, note = chosen

    capo = draft.capo or cleaned.capo
    language, sure = detect(cleaned.body)
    link = find_link(title, author)

    path = free_path(songs_dir, slug(title) + "_" + slug(author))
    path.write_text(song_file(title, author, capo, link, {language: []}, cleaned.body, item.added),
                    encoding="utf-8")
    try:
        load_song(path)
    except SongError as e:
        path.unlink()
        return "uncertain", None, f"the song file came out invalid ({e})"
    details = [f"ver {result.version} from {result.url}"]
    if note:
        details.append(note)
    if not sure:
        details.append(f"language unclear, tagged {language}: check it")
    if not link:
        details.append("no Spotify/YouTube link found")
    if cleaned.notes:
        details.append("notes: " + "; ".join(cleaned.notes))
    return "added", path, "; ".join(details)


# ---------- report ----------

def record(report_file, section, entries):
    """Add entries under 'section:' in report_file (creating the section at the end)."""
    if not entries:
        return
    path = Path(report_file)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    header = f"{section}:"
    if header in [line.strip() for line in lines]:
        start = [line.strip() for line in lines].index(header)
        end = start + 1
        while end < len(lines) and lines[end].strip() and not lines[end].strip().endswith(":"):
            end += 1
        lines[end:end] = entries
    else:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", header] + entries
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Add a list of songs from Ultimate Guitar to the book.")
    parser.add_argument("list", type=Path, help="Ultimate Guitar's saved-songs list, or Title - Artist lines")
    parser.add_argument("--report", type=Path, help="add the results to this file (e.g. Checked.txt)")
    parser.add_argument("--songs-dir", type=Path, default=build.SONGS_DIR, help=argparse.SUPPRESS)
    parser.add_argument("--no-build", action="store_true", help="don't rebuild index.html afterwards")
    parser.add_argument("--limit", type=int, help="add at most this many songs (to try it out)")
    args = parser.parse_args()

    aliases, fixes = load_aliases(), load_fixes()
    songs, repeats = without_repeats(read_list(args.list), aliases, fixes)
    if not songs:
        print("No songs in the list.")
        return 1
    for item, kept in repeats:
        print(f"Repeat: {item.label} (line {item.line}) -> using line {kept.line}")

    added, uncertain, todo = [], [], []
    in_book = book_songs(args.songs_dir)
    for item in songs:
        title, author = names(item, aliases, fixes)
        if book_key(title, author) in in_book:
            continue
        todo.append((item, title, author))
    print(f"{len(songs)} songs in the list, {len(songs) - len(todo)} already in the book, {len(todo)} to add.")
    if args.limit is not None:
        todo = todo[:args.limit]

    for n, (item, title, author) in enumerate(todo, start=1):
        if n > 1:
            time.sleep(PAUSE)
        print(f"[{n}/{len(todo)}] {item.label} -> {title} ({author})", flush=True)
        status, path, details = add_one(item, title, author, args.songs_dir)
        print(f"    {status.upper()}: {path.name if path else ''} {details}", flush=True)
        if status == "added":
            added.append(f"{path.stem}  ({item.label}; {details})")
        else:
            uncertain.append(f"{item.label}  (line {item.line}; {details})")
        if args.report:  # as we go, so an interruption loses nothing
            record(args.report, "claude-added" if status == "added" else "claude-uncertain",
                   [added[-1] if status == "added" else uncertain[-1]])

    print(f"\nAdded {len(added)}, uncertain {len(uncertain)}.")
    if args.report:
        print(f"Results added to {args.report}.")
    if added and not args.no_build and args.songs_dir == build.SONGS_DIR:
        build.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
