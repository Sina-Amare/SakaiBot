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
    """
    response_text: str
    thinking_requested: bool = False
    thinking_applied: bool = False
    thinking_summary: Optional[str] = None
    web_search_requested: bool = False
    web_search_applied: bool = False
    fallback_reason: Optional[str] = None
    model_used: str = ""
    
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


def build_response_parts(metadata: AIResponseMetadata) -> tuple:
    """
    Build header and footer parts for AI response display.
    
    Returns:
        Tuple of (header: str, footer: str)
        - header: Thinking block to prepend (or empty string)
        - footer: Metadata line to append (or empty string)
    """
    header_parts = []
    footer_parts = []
    
    # Unicode directional controls for LTR display
    LRE = '\u202A'  # Left-to-Right Embedding
    PDF = '\u202C'  # Pop Directional Formatting
    
    # Thinking status - goes in HEADER
    if metadata.thinking_requested:
        if metadata.thinking_applied:
            if metadata.thinking_summary:
                header_parts.append(
                    f"```\n💭 Thought Process:\n{metadata.thinking_summary}\n```"
                )
            footer_parts.append("🧠 **Deep Thinking Applied**")
        else:
            reason = metadata.fallback_reason or "unavailable"
            footer_parts.append(f"⚠️ Thinking mode {reason}, used standard response")
    
    # Web search status - goes in footer
    if metadata.web_search_requested:
        if metadata.web_search_applied:
            footer_parts.append("🌐 **Web Search Used**")
        else:
            footer_parts.append("⚠️ Web search unavailable (billing required)")
    
    # Model info - only show if we have other indicators
    if footer_parts and metadata.model_used:
        footer_parts.append(f"**Model:** {metadata.model_used}")
    
    # Build header string (thinking block at top)
    header = ""
    if header_parts:
        header = "\n".join(header_parts) + "\n\n"
    
    # Build footer string (metadata at bottom)
    footer = ""
    if footer_parts:
        footer_content = " | ".join(footer_parts)
        footer = f"\n\n───────────────────────────\n{LRE}{footer_content}{PDF}"
    
    return (header, footer)
