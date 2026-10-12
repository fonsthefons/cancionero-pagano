"""Importing songs into the book (used by add_song.py and add_songs.py).

    search.py    find chord pages on Ultimate Guitar (with version numbers)
    read.py      read a song from its Ultimate Guitar link
    fetch.py     download a web page (falls back to a headless browser when a
                 site blocks simple downloads)
    sites/       the Ultimate Guitar reader, turning its page into a Draft
    chords.py    chord names: Spanish notation (Do, RE, mi...) to letters,
                 rewriting chord lines without moving any chord off its letter
    clean.py     tidy the song text: spaces instead of tabs, no odd characters,
                 no section labels, an "Intro:" at the top
    language.py  is the song in English or Spanish? (its tag)
    titles.py    Ultimate Guitar's titles with their apostrophes back
    websearch.py web search, used by spotify.py and youtube.py for links
"""
