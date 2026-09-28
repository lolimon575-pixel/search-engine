DISCUSSION_SITES = (
    "reddit.com",
    "stackoverflow.com",
    "stackexchange.com",
    "news.ycombinator.com",
    "github.com",
)


def discussion_query(query):
    sites = " OR ".join(f"site:{site}" for site in DISCUSSION_SITES)
    return f"{query} ({sites})"


def is_discussion_url(url):
    value = (url or "").lower()
    return any(site in value for site in DISCUSSION_SITES)
