# Progress

Cancionero Pagano was started on 2026-10-12 from a copy of
[cancionero](https://github.com/fonsthefons/cancionero) (same program, new
songs and tags). That book's history stays in its own repository.

## 2026-10-12: new book from Want.txt

Decisions (asked before starting):
- Fresh git history; public repo `fonsthefons/cancionero-pagano` with GitHub Pages; push as I go.
- A song saved twice by the same artist is added once, from its most recent line.
  Different artists stay separate (three Hallelujahs).
- Tab / Power / Guitar Pro / Official lines: use a chords version; if none, skip and report.
- Proper titles (apostrophes back, no "(ver N)"), unified artist spellings;
  "Misc Musicals - Les Misérables - Stars" → *Stars* by *Les Misérables*.
- Exact UG version; if it's gone, the best rated chords version (reported in Checked.txt).
- Spotify link, else YouTube, as in cancionero.
- The date the song was saved goes in the song file as `added:` (not shown).
- Title "Cancionero Pagano"; tags only `english` (English) and `spanish` (Español).
- Ultimate Guitar only, everywhere (Cifra Club, LaCuerda, generic reader, DuckDuckGo chord search removed).
- If UG blocks: back off and resume.

### Phase 1: repository
- `rm -rf .git`, `git init -b main`.
- `.gitignore`: also `.claude/` (local Claude Code settings).

### Phase 2: songs and tags removed
- Deleted every file in `songs/`.
- `tags.yaml`: only `english` and `spanish` (flat tags).
- `song_template.md`, `author_aliases.yaml` (UG names → book names, e.g.
  Los Delincuentes → Los Delinqüentes), new `title_fixes.yaml`.

### Phase 3: scripts for Ultimate Guitar
- `importer/search.py`: UG's own search only, Chords pages only, with version
  number, votes, rating and live/studio; `find_versions()` picks an exact
  version (studio first when UG has a live one with the same number).
- `importer/sites/`: only `ultimate_guitar.py`; other links are refused with a
  clear message (`site_for` raises `SiteError`). `importer/read.py` checks the
  site before downloading.
- `importer/websearch.py`: the DuckDuckGo search, now only used by
  `spotify.py` / `youtube.py` to find links.
- `importer/titles.py`: apostrophes back on common contractions, overrides from
  `title_fixes.yaml`, "Misc ..." artists → show as author (or "Traditional").
- `importer/language.py`: English or Spanish from common words in the lyrics.
- `add_songs.py`: rewritten for UG's saved-songs list (artist / title (ver N) /
  date [kind]); repeats removed; exact version or best; title, author, language
  tag, link, `added:` date; skips songs already in the book (re-runnable);
  waits and retries when UG or the web search says "too many requests"
  (1, 5, 15, 30, 60 min); writes Checked.txt as it goes; `--limit N`.
- `add_song.py`: UG link / UG search / paste; suggests the language tag; writes `added:` (today).
- `builder/songs.py`: `added` is an allowed field.
- `web/template.html`: title "Cancionero Pagano".
- `web/js/core.js`: saved settings use the prefix `cancionero-pagano.` instead
  of `cancionero.`: both books live on fonsthefons.github.io and would
  otherwise share the Sing Session, transpositions and settings.
- README rewritten for this book.
- Tested: `scratch/pagano_list_check.py` (Want.txt → 406 lines, 19 repeats,
  387 songs); `add_songs.py --limit 4` into `scratch/pagano_test_songs` (4 added,
  exact versions, Spotify links).

## Blocked

(nothing yet)
