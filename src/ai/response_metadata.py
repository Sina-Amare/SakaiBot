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
        web_search_requested: Whether web search was requested by user
        web_search_applied: Whether web search was actually used
        fallback_reason: Explanation if a feature fell back to normal mode
        model_used: Name of the AI model that generated the response
    """
    response_text: str
    thinking_requested: bool = False
    thinking_applied: bool = False
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
    
    Only shows indicators when features were requested.
    Shows success or fallback message based on what actually happened.
    
    Args:
        metadata: The response metadata with execution status
        
    Returns:
        Formatted footer string, or empty string if no indicators needed
    """
    footer_parts = []
    
    # Thinking status
    if metadata.thinking_requested:
        if metadata.thinking_applied:
            footer_parts.append("🧠 **Deep Thinking Applied**")
        else:
            reason = metadata.fallback_reason or "unavailable"
            footer_parts.append(f"⚠️ Thinking mode {reason}, used standard response")
    
    # Web search status  
    if metadata.web_search_requested:
        if metadata.web_search_applied:
            footer_parts.append("🌐 **Web Search Used**")
        else:
            footer_parts.append("⚠️ Web search unavailable (billing required)")
    
    # Model info - only show if we have other indicators
    if footer_parts and metadata.model_used:
        footer_parts.append(f"**Model:** {metadata.model_used}")
    
    if not footer_parts:
        return ""
    
    # Unicode directional controls for LTR display
    LRE = '\u202A'  # Left-to-Right Embedding
    PDF = '\u202C'  # Pop Directional Formatting
    
    footer_content = " | ".join(footer_parts)
    return f"\n\n───────────────────────────\n{LRE}{footer_content}{PDF}"
