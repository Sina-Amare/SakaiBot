"""Response metadata for AI operations with execution status tracking."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AIResponseMetadata:
    """
    Metadata about how an AI request was processed.
    
    This class tracks what was requested vs what was actually applied,
    enabling dynamic status indicators in user-facing output.
    
    Attributes:
        response_text: The actual response content from the AI
        thinking_requested: Whether thinking mode was requested by user
        thinking_applied: Whether thinking mode was actually applied
        thinking_summary: Summary of the AI's thought process (if available)
        web_search_requested: Whether web search was requested by user
        web_search_applied: Whether web search was actually used
        fallback_reason: Explanation if a feature fell back to normal mode
        model_used: Name of the AI model that generated the response
        provider_used: Provider that generated the response
    """
    response_text: str
    thinking_requested: bool = False
    thinking_applied: bool = False
    thinking_summary: Optional[str] = None
    web_search_requested: bool = False
    web_search_applied: bool = False
    fallback_reason: Optional[str] = None
    model_used: str = ""
    provider_used: str = ""
    # Model fallback tracking (when Pro falls back to Flash)
    model_fallback_applied: bool = False
    model_fallback_reason: Optional[str] = None
    # Provider fallback tracking (when primary falls back to configured provider)
    provider_fallback_applied: bool = False
    provider_fallback_reason: Optional[str] = None
    # Live performance data. ``None`` means "not measured / not reported by
    # provider" — the footer hides the field rather than showing a placeholder
    # like ``Tokens: 0`` which would be wrong.
    latency_seconds: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    
    def __str__(self) -> str:
        """Return response text for backward compatibility."""
        return self.response_text
    
    def __len__(self) -> int:
        """Return length of response text for backward compatibility."""
        return len(self.response_text)
    
    def strip(self) -> str:
        """Return stripped response text for backward compatibility."""
        return self.response_text.strip()
    
    @property
    def has_thinking_fallback(self) -> bool:
        """Check if thinking was requested but not applied."""
        return self.thinking_requested and not self.thinking_applied
    
    @property
    def has_web_search_fallback(self) -> bool:
        """Check if web search was requested but not applied."""
        return self.web_search_requested and not self.web_search_applied
    
    @property
    def has_provider_fallback(self) -> bool:
        """Check if provider fallback was applied."""
        return self.provider_fallback_applied


def build_execution_footer(metadata: AIResponseMetadata) -> str:
    """
    Build footer showing actual execution status.
    
    DEPRECATED: Use build_response_parts() for new code.
    This wrapper maintains backward compatibility.
    """
    header, footer = build_response_parts(metadata)
    # For backward compat, combine them (header at start, footer at end)
    # But callers should update to use build_response_parts directly
    return footer  # Old behavior - just return footer


def _format_thinking_block(summary: str) -> str:
    """Render the model's raw reasoning as a real Telegram ``<blockquote>``.

    parse_mode='html' supports a proper ``<blockquote>`` element, which
    renders as an indented, vertically-bordered quote in Telegram clients.
    The previous ``▎`` line-prefix workaround existed because Markdown had
    no blockquote element; now that AI output is HTML, we use the real
    thing — visually cleaner and the bidi/RTL behavior is handled by
    Telegram's client rather than relying on a custom prefix per line.

    Markdown-special characters in the raw reasoning are softened so they
    can't leak as literal ``**`` / ``_`` / backticks, and HTML-special
    characters are entity-escaped so a ``<`` in the reasoning can't break
    message parsing. A trailing ``[...]`` from the truncation marker is
    rewritten to a styled ``<i>…</i>`` indicator.
    """
    cleaned = (
        summary.replace('`', "'")
        .replace('*', '')
        .replace('_', '')
    )
    # Escape unsafe characters in the reasoning text.
    cleaned = (
        cleaned.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    if not lines:
        return ""
    body = "\n".join(lines)
    # Style the upstream truncation marker (set by GeminiProvider when the
    # raw reasoning exceeds THINKING_SUMMARY_MAX_CHARS).
    body = body.replace("[...truncated]", "<i>… truncated</i>")
    return (
        f"💭 <b>Thought Process</b>\n"
        f"<blockquote>{body}</blockquote>"
    )


def build_response_parts(metadata: AIResponseMetadata) -> tuple:
    """Build header and footer parts for AI response display.

    Footer is laid out on two conditional lines:

    Line 1 - facts, joined by "  ·  ":
        <b>Model:</b> X  ·  <b>Time:</b> 4.2s  ·  <b>Tokens:</b> 312
        Each field appears only when populated. Tokens: 0 and Time: 0.0s
        are placeholder values, never shown.

    Line 2 - badges, joined by "  ·  ":
        🧠 Deep Thinking  ·  🌐 Web Search  ·  🔄 Fallback: ...
        Only the badges that actually fired show up.

    Returns:
        Tuple of (header, footer); either may be an empty string.
    """
    # Unicode directional controls for LTR display in RTL contexts.
    LRE = "\u202A"  # Left-to-Right Embedding
    PDF = "\u202C"  # Pop Directional Formatting

    # ---- Header: the thinking block ----
    header_parts: list = []
    if metadata.thinking_requested and metadata.thinking_applied:
        if metadata.thinking_summary:
            block = _format_thinking_block(metadata.thinking_summary)
            if block:
                header_parts.append(block)

    # ---- Footer line 1: live facts (only populated fields) ----
    fact_parts: list = []
    if metadata.model_used:
        fact_parts.append(f"<b>Model:</b> {metadata.model_used}")
    if metadata.latency_seconds is not None and metadata.latency_seconds > 0:
        fact_parts.append(f"<b>Time:</b> {metadata.latency_seconds:.1f}s")
    if metadata.output_tokens is not None and metadata.output_tokens > 0:
        # Show "in/out" when both are present so the user can see prompt
        # cost vs response cost; otherwise just the output count.
        if metadata.input_tokens is not None and metadata.input_tokens > 0:
            fact_parts.append(
                f"<b>Tokens:</b> {metadata.input_tokens}/"
                f"{metadata.output_tokens}"
            )
        else:
            fact_parts.append(f"<b>Tokens:</b> {metadata.output_tokens}")

    # ---- Footer line 2: status badges (only ones that fired) ----
    badge_parts: list = []
    if metadata.thinking_requested:
        if metadata.thinking_applied:
            badge_parts.append("🧠 Deep Thinking")
        else:
            reason = metadata.fallback_reason or "unavailable"
            badge_parts.append(f"⚠️ Thinking {reason}")
    if metadata.web_search_requested:
        if metadata.web_search_applied:
            badge_parts.append("🌐 Web Search")
        else:
            badge_parts.append("⚠️ Web Search unavailable")
    if metadata.model_fallback_applied:
        reason = metadata.model_fallback_reason or "Pro quota exceeded"
        badge_parts.append(f"⚡ Flash ({reason})")
    if metadata.provider_fallback_applied:
        provider = metadata.provider_used or "fallback"
        reason = metadata.provider_fallback_reason or "primary unavailable"
        badge_parts.append(f"🔄 Fallback: {provider} ({reason})")

    # ---- Assemble ----
    header = ("\n".join(header_parts) + "\n\n") if header_parts else ""

    footer_lines: list = []
    if fact_parts:
        footer_lines.append(f"{LRE}{'  ·  '.join(fact_parts)}{PDF}")
    if badge_parts:
        footer_lines.append(f"{LRE}{'  ·  '.join(badge_parts)}{PDF}")

    footer = ""
    if footer_lines:
        footer = "\n\n━━━━━━━━━━━━━━━━━━\n" + "\n".join(footer_lines)

    return (header, footer)
