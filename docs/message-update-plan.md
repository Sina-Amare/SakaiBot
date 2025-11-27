# Message Update Implementation Plan

## Overview

This document tracks all static bot messages that need to be updated to follow the new Telegram message style guide.

## Files to Update

### ✅ Already Good (Minimal Changes Needed)

#### 1. `src/telegram/handlers/image_handler.py`
- ✅ Line 69-73: Invalid command error - **GOOD** (has emoji, clear format)
- ✅ Line 84-86: Invalid model error - **GOOD** (has emoji, lists models)
- ✅ Line 96: Prompt error - **GOOD** (has emoji)
- ✅ Line 109-113: Rate limit error - **GOOD** (has emoji, clear info)
- ✅ Line 158: Processing status - **GOOD** (has emoji)
- ✅ Line 160: Queue position - **GOOD** (has emoji)
- ✅ Line 173: Request not found - **GOOD** (has emoji)
- ✅ Line 185: Error display - **GOOD**
- ✅ Line 202: Queue update - **GOOD**
- ✅ Line 299: Enhancing prompt - **GOOD** (has emoji)
- ✅ Line 317: Generating image - **GOOD** (has emoji)
- ✅ Line 395: Sending image - **GOOD** (has emoji)
- ✅ Line 407-411: Enhancement notes - **GOOD** (has emoji)
- ✅ Line 413: Caption header - **GOOD** (has emoji, markdown)

#### 2. `src/telegram/handlers/ai_handler.py`
- ✅ Line 59-63: Rate limit error - **GOOD** (has emoji, clear structure)
- ✅ Line 67: Processing message - **GOOD** (has emoji)
- ✅ Line 105: Completion message - **GOOD** (has emoji, timestamp)
- ✅ Line 136: Prompt usage - **NEEDS MINOR UPDATE** (add emoji)
- ✅ Line 143: Invalid prompt - **GOOD** (has emoji)
- ✅ Line 155: Empty response warning - **GOOD** (has emoji)
- ✅ Line 167: Translate usage - **NEEDS MINOR UPDATE** (add emoji)
- ✅ Line 171: Invalid language - **GOOD** (has emoji)
- ✅ Line 177: Invalid text - **GOOD** (has emoji)
- ✅ Line 189: Empty translation - **GOOD** (has emoji)
- ✅ Line 202: Invalid number - **GOOD** (has emoji)
- ✅ Line 207: Invalid mode - **GOOD** (has emoji)
- ✅ Line 232: No messages found - **NEEDS MINOR UPDATE** (add emoji)
- ✅ Line 242: Empty analysis - **GOOD** (has emoji)
- ✅ Line 260: Invalid number - **GOOD** (has emoji)
- ✅ Line 266: Invalid question - **GOOD** (has emoji)
- ✅ Line 291: No messages for tellme - **NEEDS MINOR UPDATE** (add emoji)
- ✅ Line 300: Empty tellme response - **GOOD** (has emoji)
- ✅ Line 334: Prompt usage - **NEEDS UPDATE** (no emoji)
- ✅ Line 345: Translate usage - **NEEDS UPDATE** (no emoji)
- ✅ Line 356: Invalid mode - **NEEDS UPDATE** (no emoji)
- ✅ Line 364: Analyze usage - **NEEDS UPDATE** (no emoji)
- ✅ Line 376: Tellme usage - **NEEDS UPDATE** (no emoji)

#### 3. `src/telegram/handlers/tts_handler.py`
- ✅ Line 51-54: Processing TTS - **GOOD** (has emoji)
- ✅ Line 75-84: Successful conversion - **GOOD** (has emoji, formatted)
- ✅ Line 99: TTS error - **GOOD** (has emoji)
- ✅ Line 103: Queue processing - **GOOD** (has emoji)
- ✅ Line 139-144: Please provide text - **GOOD** (has emoji, clear usage)
- ✅ Line 168-173: Processing message - **GOOD** (has emoji)
- ✅ Line 229-237: Success with voice info - **GOOD** (has emoji, structured)
- ✅ Line 262-270: Error display - **GOOD** (has emoji)
- ✅ Line 280-296: Queue status - **GOOD** (has emoji, formatted)
- ✅ Line 310: TTS error - **GOOD** (has emoji)

#### 4. `src/telegram/handlers/stt_handler.py`
- ✅ Line 58-62: Processing voice - **GOOD** (has emoji, step indicator)
- ✅ Line 94-98: Transcribed + AI processing - **GOOD** (has emoji, markdown)
- ✅ Line 140-143: Final response - **GOOD** (has emoji, markdown)
- ✅ Line 156: STT error - **GOOD** (has emoji)
- ✅ Line 158: File not found - **NEEDS UPDATE** (remove "STT Error:" duplicate)
- ✅ Line 162: Unexpected error - **NEEDS UPDATE** (remove "STT Error:" duplicate)

#### 5. `src/telegram/handlers.py`
- ✅ Line 230-234: STT usage - **NEEDS UPDATE** (no emoji)
- ✅ Line 239-243: Not a voice message - **NEEDS UPDATE** (no emoji)

#### 6. `src/telegram/commands/self_commands.py`
- ✅ All messages - **EXCELLENT** (already uses emojis, HTML formatting, well-structured)

#### 7. `src/utils/error_handler.py`
- ✅ Lines 14-20: Error messages - **GOOD** (has emojis)
- ✅ Lines 43-57: Image-specific errors - **GOOD** (has emojis, descriptive)

### 📝 Messages That Need Updates

#### Priority 1: High-Impact User-Facing Messages

**src/telegram/handlers/ai_handler.py**
- Line 136: `"Usage: /prompt=<your question or instruction>"` 
  - → `"❓ **Usage:** `/prompt=<your question or instruction>`"`
  
- Line 167: `"Usage: /translate=<lang>=<text> or reply with /translate=<lang>"`
  - → `"🌐 **Usage:** `/translate=<lang>=<text>` or reply with `/translate=<lang>`"`
  
- Line 232: `"No text messages found in the specified history to analyze."`
  - → `"📭 No text messages found in the specified history to analyze."`
  
- Line 291: `"No text messages found in history to answer your question."`
  - → `"📭 No text messages found in history to answer your question."`
  
- Line 334-335: Usage message
  - → `"❓ **Usage:** `/prompt=<your question or instruction>`"`
  
- Line 345: Usage message
  - → `"🌐 **Usage:** `/translate=<lang>[,source_lang] [text]` or reply with `/translate=<lang>`"`
  
- Line 356: Invalid mode message
  - → `"❌ **Invalid analysis mode.** Valid modes: general, fun, romance"`
  
- Line 364: Usage message  
  - → `"📊 **Usage:** `/analyze=<number_between_1_and_{max_limit}>` or `/analyze=<mode>=<number>` (mode: fun, romance, general)"`
  
- Line 376: Usage message
  - → `"💬 **Usage:** `/tellme=<number_of_messages>=<your_question>`"`

**src/telegram/handlers/stt_handler.py**
- Line 158: Remove duplicate "STT Error:" prefix
  - → `"⚠️ File not found - {e}"`
  
- Line 162: Remove duplicate "STT Error:" prefix  
  - → `"⚠️ An unexpected error occurred - {e}"`

**src/telegram/handlers.py**
- Line 232: `"Please use /stt in reply to a voice message."`
  - → `"❌ Please use `/stt` in reply to a voice message."`
  
- Line 241: `"The replied message is not a voice note."`
  - → `"❌ The replied message is not a voice note."`

#### Priority 2: Categorization Handler Messages

**src/telegram/handlers/categorization_handler.py**
- Line 127: `"Could not process 'confirm'. Replied message not found."`
  - → `"❌ Could not process 'confirm'. Replied message not found."`

## Update Strategy

### Phase 1: Documentation ✅
- [x] Create style guide
- [x] Document all messages needing updates
- [x] Categorize by priority

### Phase 2: Implementation
1. Update high-impact messages (handlers)
2. Test each handler individually
3. Run full test suite
4. Commit changes

### Phase 3: Validation
1. Run pytest tests
2. Manual testing with real Telegram client
3. Verify emoji rendering
4. Check markdown formatting

## Testing Checklist

- [ ] Image generation: `/image=flux=test`
- [ ] Image queue status updates
- [ ] Invalid image commands
- [ ] Rate limit messages
- [ ] AI prompt: `/prompt=test`
- [ ] Translation: `/translate=en=test`
- [ ] Analysis: `/analyze=10`
- [ ] Tellme: `/tellme=10=what was said?`
- [ ] STT: Reply to voice with `/stt`
- [ ] TTS: `/tts=test`
- [ ] Invalid commands
- [ ] Error scenarios
- [ ] All emojis display correctly
- [ ] Markdown renders properly

## Notes

- Most messages are already well-formatted with emojis
- Changes are minimal and focused on consistency
- Priority is on user-facing command usage messages
- Error messages are already excellent
- Self-commands (auth, help, status) are perfect

## Summary

**Total Messages to Update: ~12**
- High priority: 9 messages (usage/error messages)
- Low priority: 3 messages (minor improvements)

**Files Affected: 3**
- `src/telegram/handlers/ai_handler.py` (9 updates)
- `src/telegram/handlers/stt_handler.py` (2 updates)
- `src/telegram/handlers.py` (2 updates)
- `src/telegram/handlers/categorization_handler.py` (1 update)

Most messages are already excellent and follow best practices!
