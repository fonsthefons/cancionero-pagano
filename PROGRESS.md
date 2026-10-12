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

### Phase 4: GitHub
- `gh repo create fonsthefons/cancionero-pagano --public --source . --push`.
- Pages: `gh api -X POST repos/fonsthefons/cancionero-pagano/pages` (main, /).
  Live at https://fonsthefons.github.io/cancionero-pagano/.

### Phase 5: import of Want.txt
- `venv/bin/python -u add_songs.py Want.txt --report Checked.txt` (background, about 3 h).
  Songs committed and pushed every 50.
- Result: **387 added, 0 uncertain**; every exact UG version was found. UG and
  the web search never asked to slow down.
- Tab / Power / Guitar Pro / Official lines got a chords version: Never Going
  Back Again, Angelyne, Moon River, Treat You Better, Be Mine, Feel, Ojalá.
- No Spotify/YouTube link found: Cuando Vuelva A Sevilla Por Primavera,
  Nubes De Pegatinas, Los Piratas Del Estrecho.
- Tags: 284 English, 103 Español; checked by author
  (`scratch/pagano_tag_check.py`), no author has mixed tags.

### Phase 6: fixes after the import
- `importer/language.py`: each word counts once (Passenger's "I Hate" was
  tagged Spanish because of its "la la la" chorus). Re-tagged with
  `scratch/pagano_fix_songs.py --write`: I Hate → english, C. Tangana's
  Me Maten → spanish.
- `add_song.py` `slug()`: apostrophes dropped ("dont_cry", not "don_t_cry");
  33 song files renamed by the same script. (Checked.txt still shows the old
  file names for those songs.)
- `builder/lyrics.py` CHORD_RE: chords with more than one ending (A7sus2,
  D7sus4, Am7b5, Emadd9, Dmaj7sus2, D7b9) are now recognised. Before, those
  lines showed as lyrics (no chord colour, no transposing). Checked with
  `scratch/pagano_chord_regex_check.py`: every line that changed is a real
  chord line, and no lyric line became one.
- Here I Am Lord: author "Traditional" → Dan Schutte (UG lists it under
  "Misc Praise Songs"); file renamed.

### Offline from the home screen
- Reported: the page opens offline from Safari's Reading List but not from a
  home screen icon (a home screen app doesn't use Safari's saved copy).
- New `sw.js` (service worker, repo root so it covers the whole site):
  network first, saved copy when offline or after 4 s without an answer.
  `web/js/offline.js` registers it (https or localhost only).
  `manifest.webmanifest` + Apple meta tags in `web/template.html` (name
  "Pagano", standalone). No icon image yet: iOS uses a screenshot.
- Tested with `scratch/offline_test.py` (Playwright, browsers downloaded into
  `scratch/ms-playwright` by `scratch/install_browsers.py`): load once, stop
  the server, reload → 387 songs in Chromium and WebKit. (Playwright's
  simulated offline mode in WebKit blocks requests before the service worker,
  so WebKit is tested with `--server-only`.)

### Still to check by hand (in Checked.txt)
- Songs with notes "Added Intro: with the first chord": the intro may need changing.
- "Unusual characters" notes are mostly `|` bar lines, which are fine.

## Blocked

(nothing)
