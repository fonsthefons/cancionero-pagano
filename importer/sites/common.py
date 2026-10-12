"""What site readers return."""

from dataclasses import dataclass


class SiteError(Exception):
    pass


@dataclass
class Draft:
    """A song as read from a site, before cleaning."""

    title: str | None
    artist: str | None
    text: str
    marked: bool  # chords wrapped as [ch]Am[/ch]
    capo: str | None = None


@dataclass
class Follow:
    """The song is on another page (e.g. a list of versions)."""

    url: str
