"""Avatars.

Default = colored-initials SVG generated locally with ZERO Telegram API calls
(safest for ban-avoidance). Real profile photos are handled in
``services/entity_service.py`` (lazy + throttled + disk-cached); this module
stays a pure function so it is trivially testable.
"""

# Deterministic, pleasant palette indexed by entity id.
_PALETTE = [
    "#6366f1", "#8b5cf6", "#ec4899", "#ef4444", "#f59e0b",
    "#10b981", "#06b6d4", "#3b82f6", "#14b8a6", "#f43f5e",
]


def _initials(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "#"
    parts = [p for p in name.split() if p]
    if not parts:
        return "#"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


def initials_svg(entity_id: int, display_name: str) -> bytes:
    """Return an SVG avatar (bytes) with the entity's initials on a color disc."""
    try:
        idx = abs(int(entity_id))
    except (TypeError, ValueError):
        idx = 0
    color = _PALETTE[idx % len(_PALETTE)]
    text = _escape(_initials(display_name))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" '
        'viewBox="0 0 96 96">'
        f'<rect width="96" height="96" rx="48" fill="{color}"/>'
        '<text x="50%" y="50%" dy=".34em" text-anchor="middle" '
        'font-family="Segoe UI, Roboto, Arial, sans-serif" font-weight="600" '
        f'font-size="38" fill="#ffffff">{text}</text>'
        '</svg>'
    )
    return svg.encode("utf-8")
