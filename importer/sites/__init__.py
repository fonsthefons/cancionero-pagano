"""Reading a song from its web page. This book takes its songs from Ultimate
Guitar only; its reader is a module with:

    NAME = "Ultimate Guitar"        # shown to the user
    DOMAINS = ("ultimate-guitar.com",)  # matched against the end of the link's host
    def parse(page, url) -> Draft   # or a Follow(url) to read another page

To support another site, add a module like it here and list it in SITES.
"""

import re
from urllib.parse import urlparse

from . import ultimate_guitar
from .common import Draft, Follow, SiteError

SITES = [ultimate_guitar]

__all__ = ["Draft", "Follow", "SiteError", "site_for", "saved_page_address", "SITES"]

CANONICAL_RE = re.compile(
    r"<link[^>]*rel=[\"']?canonical[^>]*href=[\"']([^\"']+)|<link[^>]*href=[\"']([^\"']+)[\"'][^>]*rel=[\"']?canonical"
    r"|<meta[^>]*og:url[^>]*content=[\"']([^\"']+)",
    re.IGNORECASE,
)


def saved_page_address(page):
    """The web address of a page saved from a browser: its canonical link, or
    else the first supported site it mentions."""
    match = CANONICAL_RE.search(page)
    if match:
        return next(group for group in match.groups() if group)
    for site in SITES:
        for domain in site.DOMAINS:
            if domain in page:
                return f"https://{domain}/"
    return ""


def site_for(url):
    """The reader for the link's site. Raises SiteError for other sites."""
    host = (urlparse(url).hostname or "").lower()
    for site in SITES:
        if any(host == d or host.endswith("." + d) for d in site.DOMAINS):
            return site
    raise SiteError("only Ultimate Guitar links can be read (ultimate-guitar.com)")
