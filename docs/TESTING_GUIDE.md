# SakaiBot Testing Guide - Persian Translation & Analysis

## Quick Testing Checklist

### ✅ Prerequisites

- Monitoring is running (`/analyze` commands work only when monitoring is active)
- You're in a group chat that SakaiBot is monitoring
- You're an authorized user

---

## 🧪 Test Cases

### 1. **Persian Analysis (Default)**

Test the default Persian output with all three analysis types:

```
/analyze=500
/analyze=fun=500
/analyze=romance=500
/analyze=general=500
```

**Expected:**

- ✅ Output in Persian (فارسی)
- ✅ Proper RTL text display (Persian reads right-to-left)
- ✅ URLs, English words, and numbers display correctly
- ✅ HTML formatting preserved (`<b>`, `<i>`, `<code>`)
- ✅ Persian numbers (۰-۹) used in statistics

---

### 2. **English Analysis (With `en` Flag)**

Test English output:

```
/analyze=500 en
/analyze=fun=500 en
/analyze=romance=500 en
/analyze=general=500 en
```

**Expected:**

- ✅ Output in English
- ✅ No translation delay (skips translation step)
- ✅ Same analysis quality as before

---

### 3. **Different Message Counts**

Test with various message counts:

```
/analyze=100          # Small sample
/analyze=500          # Medium
/analyze=1000         # Large
/analyze=fun=200      # Small with type
/analyze=romance=1000 # Large with type
```

**Expected:**

- ✅ Bot fetches correct number of messages
- ✅ Analysis reflects the conversation size
- ✅ Larger samples take longer (expected)

---

### 4. **Translation Quality Check**

For Persian output, verify:

- **Tone matching:**

  - `fun` → Casual Persian (خودمونی style)
  - `romance` → Semi-formal, warm
  - `general` → Professional

- **Text quality:**
  - ✅ Natural Persian (not literal translation)
  - ✅ Humor translated appropriately
  - ✅ Cultural context adapted
  - ✅ No English words (except technical terms/names)

---

### 5. **RTL Display Verification**

Check these mixed-direction elements display correctly:

- **URLs in Persian text** → Should not break RTL flow
- **English words in Persian** → Should be inline and readable
- **Numbers** → Should display correctly (Persian: ۱۲۳۴)
- **Emojis** → Should work normally
- **Code blocks** → Should preserve formatting

**Test in multiple clients:**

- Telegram Desktop
- Telegram Web
- Telegram Android/iOS
- Telegram Mobile Web

---

### 6. **Queue System Testing**

SakaiBot has queues for **TTS** and **Image Generation** (but not for `/analyze` - those process immediately).

#### **TTS Queue Testing:**

Test Text-to-Speech queue by replying to messages:

1. **Reply to a message** with Persian/English text
2. Bot auto-generates voice
3. Check queue status updates

**Commands:**

- Reply to any message → Auto TTS
- Multiple rapid replies → Queue processes FIFO

**What to check:**

- ✅ Queue position updates shown
- ✅ "Processing..." status shown
- ✅ Audio sends after generation completes
- ✅ Multiple requests process in order

#### **Image Queue Testing:**

Test image generation with `/imagine`:

```
/imagine flux a beautiful sunset
/imagine sdxl a cat in space
```

Then rapidly send multiple requests:

```
/imagine flux request 1
/imagine flux request 2
/imagine flux request 3
```

**Expected:**

- ✅ Each gets a queue position number
- ✅ "Position in queue: X/Y" updates
- ✅ Flux and SDXL have separate queues
- ✅ Requests process FIFO per model
- ✅ Status messages update from PENDING → PROCESSING → COMPLETED

**Check:**

- Queue position accuracy
- Proper FIFO ordering
- Model separation (flux vs sdxl)

#### **Analyze Commands (No Queue):**

**Note:** `/analyze` commands do NOT use a queue system.

- They process **immediately** when sent
- If monitoring is stopped while processing, command fails
- **Cannot run multiple `/analyze` at once** in same bot instance
- Second `/analyze` will wait for first to complete

---

### 7. **Error Handling**

Test error cases:

```
/analyze=50000        # Too many messages (over limit)
/analyze=abc          # Invalid number
/analyze=fun          # Missing message count
```

**Expected:**

- ✅ Clear error messages
- ✅ No crashes
- ✅ Helpful guidance to user

---

### 7. **Performance Testing**

Monitor performance metrics:

```
/analyze=1000
```

**Check:**

- ✅ English analysis completes (<30s typically)
- ✅ Persian translation adds ~10-45s
- ✅ Total time reasonable (<90s for 1000 messages)
- ✅ No timeout errors

---

## 📝 What to Report

### ✅ Success Criteria:

- Persian output displays correctly on all clients
- Translation sounds natural to Persian speakers
- English `en` flag works properly
- No encoding errors
- Performance is acceptable

### ❌ Issues to Report:

- RTL display broken on any client
- Translation sounds unnatural/literal
- Timeout errors
- Encoding/character corruption
- Missing HTML formatted
- Wrong tone (casual vs formal mismatch)

---

## 🎯 Priority Tests

**Minimum tests before deployment:**

1. ✅ `/analyze=500` → Persian output displays correctly
2. ✅ `/analyze=500 en` → English output works
3. ✅ `/analyze=fun=200` → Casual tone in Persian
4. ✅ `/analyze=romance=200` → Warm tone in Persian
5. ✅ Test on Desktop + Mobile

---

## 💡 Tips

- **First test in a small test group** with ~100-500 messages
- **Check console logs** for any errors
- **Compare Persian vs English** for same conversation to verify translation quality
- **Test with real conversations** (not artificial test messages)
- **Have a native Persian speaker review** translation quality

---

## 🔧 Troubleshooting

**"Translation timeout" errors:**

- Increase timeout in `src/ai/translation.py` (currently 45s)
- Check API rate limits (250 Flash requests/day on free tier)

**RTL display broken:**

- Check `src/utils/rtl_fixer.py` is applying fixes
- Verify `message_sender.py` calls RTL fixer

**Poor translation quality:**

- Check which prompt is being used (FUN/ROMANCE/GENERAL)
- Verify tone matches in `src/ai/prompts.py`

**Encoding errors:**

- Ensure `prompts.py` is UTF-8 encoded
- Check for `UnicodeDecodeError` in logs

---

**Status:** Ready for testing! 🚀

Start with `/analyze=200` in a test group and verify Persian output displays correctly.
