"""Telegram HTML safety utilities.

Telegram's Bot API accepts only a tiny subset of HTML for message
formatting: ``<b>``, ``<i>``, ``<u>``, ``<s>``, ``<code>``, ``<pre>``,
``<blockquote>`` (plus ``<a href=…>`` and ``<span class="tg-spoiler">`` —
those two need attribute handling so they are intentionally *not* exposed
through this whitelist). Anything else is a parse error and the message is
rejected.

LLM outputs routinely contain unsupported tags (``<h2>``, ``<ul>``, ``<p>``)
and stray ``<``, ``>``, ``&`` from user-quoted chat content. This module
turns arbitrary LLM output into safe Telegram-HTML by stripping unknown
tags and entity-escaping ambiguous characters, then validating with
Telethon's parser as a final safety net.

**Deliberately no Markdown -> HTML conversion** — chat messages we analyze
routinely contain ``*``, ``_``, backticks, code, math, and usernames.
Converting ``*foo*`` to ``<i>foo</i>`` would corrupt direct-quote evidence
in analysis output, which is the worst possible failure mode for a tool
that exists to extract evidence from chats. Prompts ask for HTML; if a
model emits literal ``**word**`` anyway it ships as literal text — ugly,
but never destroys evidence.
"""

from __future__ import annotations

import re
from typing import Final

# Tags Telegram parses with no required attributes. The Telegram HTML spec
# also supports <a href>, <code class="language-…"> and the spoiler span,
# but those need careful attribute handling; not worth exposing through a
# simple whitelist.
_ALLOWED_TAGS: Final[frozenset] = frozenset({
    "b", "strong",
    "i", "em",
    "u", "ins",
    "s", "strike", "del",
    "code",
    "pre",
    "blockquote",
})

# Opening, closing, or attribute-bearing tag. Group 1 captures the slash on
# closing tags, group 2 the tag name. Critical: NO whitespace allowed
# between ``<`` and the slash-or-name. ``< b >`` (math notation, etc.) must
# NOT be treated as a tag — otherwise user-supplied "5 < 3" gets mangled
# into a stray ``<3>`` element.
_TAG_RE = re.compile(
    r"<(/?)([a-zA-Z][a-zA-Z0-9]*)([^>]*)>",
    re.DOTALL,
)

_VALID_ENTITY_RE: Final[re.Pattern] = re.compile(
    r"&(?:[a-zA-Z][a-zA-Z0-9]+|#\d+|#x[0-9a-fA-F]+);"
)


def _escape_chars(text: str) -> str:
    """Escape HTML specials while preserving already-valid entities."""
    if not text:
        return ""

    out: list[str] = []
    cursor = 0
    for m in _VALID_ENTITY_RE.finditer(text):
        if m.start() > cursor:
            out.append(text[cursor:m.start()].replace("&", "&amp;"))
        out.append(m.group(0))
        cursor = m.end()
    if cursor < len(text):
        out.append(text[cursor:].replace("&", "&amp;"))

    return "".join(out).replace("<", "&lt;").replace(">", "&gt;")


def sanitize_html(text: str) -> str:
    """Keep only Telegram-allowed tags; escape every other ``<``, ``>``, ``&``.

    Unsupported tags (e.g. ``<h1>``, ``<ul>``, ``<p>``) are escaped to
    literal text so the user sees them rather than the message failing to
    parse. Attribute content on allowed tags is dropped — Telegram only
    honors a few specific attributes (``<a href>``, ``<code class>``) and
    those are not in our whitelist.
    """
    if not text:
        return ""

    out: list[str] = []
    cursor = 0
    for m in _TAG_RE.finditer(text):
        start, end = m.span()
        is_closing = bool(m.group(1))
        tag_name = m.group(2).lower()

        # Escape any text before this tag.
        if start > cursor:
            out.append(_escape_chars(text[cursor:start]))

        if tag_name in _ALLOWED_TAGS:
            # Pass through, stripping any attributes.
            if is_closing:
                out.append(f"</{tag_name}>")
            else:
                out.append(f"<{tag_name}>")
        else:
            # Not allowed - escape the literal tag text.
            out.append(_escape_chars(m.group(0)))

        cursor = end

    # Trailing text after the last tag.
    if cursor < len(text):
        out.append(_escape_chars(text[cursor:]))

    return "".join(out)


def validate_or_escape(text: str) -> str:
    """Run text through Telethon's HTML parser; on failure, full-escape.

    The parser is forgiving but rejects unmatched tags, illegal nesting,
    and bad attributes. When that happens, abandon all formatting and ship
    the text as plain entity-escaped content so the message still sends —
    better than dropping the response entirely.
    """
    if not text:
        return ""
    try:
        from telethon.extensions import html as telethon_html
        telethon_html.parse(text)
        return text
    except Exception:
        return _escape_chars(text)


def clean_telegram_html(text: str) -> str:
    """Full pipeline: sanitize unknown tags, then validate-or-escape."""
    return validate_or_escape(sanitize_html(text))
