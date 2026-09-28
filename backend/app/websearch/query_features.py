from urllib.parse import quote_plus

BANGS = {
    "!g": "https://www.google.com/search?q={query}",
    "!w": "https://en.wikipedia.org/wiki/Special:Search?search={query}",
    "!yt": "https://www.youtube.com/results?search_query={query}",
    "!gh": "https://github.com/search?q={query}",
    "!r": "https://www.reddit.com/search/?q={query}",
    "!a": "https://www.amazon.com/s?k={query}",
}

DISCUSSION_SITES = (
    "reddit.com",
    "stackoverflow.com",
    "stackexchange.com",
    "news.ycombinator.com",
    "github.com",
)


def resolve_bang(query):
    parts = query.strip().split(maxsplit=1)
    if not parts or parts[0].lower() not in BANGS:
        return None
    target = BANGS[parts[0].lower()]
    rest = parts[1] if len(parts) > 1 else ""
    return target.format(query=quote_plus(rest))


def discussion_query(query):
    sites = " OR ".join(f"site:{site}" for site in DISCUSSION_SITES)
    return f"{query} ({sites})"


def is_discussion_url(url):
    value = (url or "").lower()
    return any(site in value for site in DISCUSSION_SITES)
