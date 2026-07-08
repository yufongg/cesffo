import nh3

# SR-09: the course-content editor (module descriptions, reading material body,
# activity prompts) is a named high-risk stored-XSS surface. Allow a small set
# of formatting tags only — no script/style/iframe/event handlers/href javascript:.
ALLOWED_TAGS = {
    "p", "br", "strong", "em", "u", "s", "ul", "ol", "li",
    "h1", "h2", "h3", "h4", "blockquote", "code", "pre", "a",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "rel", "target"},
}


def sanitize_html(raw: str) -> str:
    """Strip any tag/attribute not on the allow-list. Safe to store and render."""
    if not raw:
        return raw
    return nh3.clean(raw, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, link_rel=None)


def strip_tags(raw: str) -> str:
    """Plain-text fields (titles, option text, tags): strip all markup."""
    if not raw:
        return raw
    return nh3.clean(raw, tags=set(), attributes={})
