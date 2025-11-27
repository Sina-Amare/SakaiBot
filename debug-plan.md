# Debug Investigation Plan for CLI Issues

## Investigation Date
2024 - Pre-fix analysis

## Issues to Investigate

### Issue 1: Invalid format warning on every action
**Symptom:** `Loaded 'active_command_to_topic_map' had an invalid format and was normalized.`

#### Root Cause Analysis

**Where is it loaded?**
- `src/core/settings.py:load_user_settings()` (lines 24-74)
- Specifically at lines 44-54 where it validates and normalizes the command map

**What format is expected vs actual?**
- **Expected format:** `Dict[Any, List[str]]` where keys are topic IDs (int or None) and values are lists of command strings
  ```python
  {
    None: ["cmd1", "cmd2"],      # Main chat
    123: ["cmd3", "cmd4"]         # Topic ID 123
  }
  ```
- **Actual format issue:** The normalization function `normalize_command_mappings()` is being called and returning a different structure than what was loaded
- **Why it triggers:** Line 52-53 compares `normalized != loaded_value` which will ALWAYS trigger if the loaded data has any minor differences (like ordering, case, whitespace)

**Why does normalization happen repeatedly?**
- Every time settings are loaded, normalization runs and compares
- The comparison at line 52 uses `!=` which checks if dicts are different
- Even if data is valid, minor differences (dict ordering in Python < 3.7, or other artifacts) trigger the warning
- **Root cause:** The warning is logged EVERY time normalization produces a different output, even if the difference is benign

**Solution:**
- Only log warning if there are actual invalid entries (has_invalid_keys flag)
- Don't warn on successful normalization that just cleaned up format
- Store normalized format to prevent repeated normalization warnings

---

### Issue 2: Monitoring fails to start - 'NoneType' object is not callable
**Symptom:** `Error: Failed to start monitoring: 'NoneType' object is not callable`

#### Root Cause Analysis

**Which function/method is None?**
Looking at `src/cli/menu_handlers/monitor_handler.py:30-42`:
- `toggle_monitoring()` calls `await _start_monitoring(verbose=True)` at line 42
- But there's no check if `_start_monitoring` was imported successfully

**Why is it None?**
Checking imports at line 16:
```python
from src.cli.commands.monitor import _start_monitoring, _show_monitoring_status
```

The imports look correct, but the error suggests one of these is None. Possible causes:
1. Circular import causing the function to not be fully initialized
2. The function exists but returns None and is being called incorrectly
3. Import path issue

Looking at the actual `_start_monitoring` function (lines 33-198 in monitor.py), it's properly defined as `async def _start_monitoring(verbose: bool):`

**Actual issue:** The error "NoneType object is not callable" likely comes from within `_start_monitoring`, not the function itself. Looking at line 97-101:
```python
event_handlers = EventHandlers(
    client=client,
    processor_instance=processor,
    config=config,
    ffmpeg_path=config.ffmpeg_path_resolved
)
```

If `EventHandlers` or `processor` is None, this would fail. Let me check where `processor` is defined... 

**Looking earlier in the function (lines 33-96):** There's no visible initialization of `processor` or `EventHandlers` in the visible code. The function jumps from validation (lines 38-73) to registering handlers (line 104) without showing the initialization code in between.

**Root Cause:** The code between lines 73-100 is not visible in the collapsed view, but the error suggests that either:
1. `processor` is not being initialized properly
2. `EventHandlers` class initialization is failing
3. Some dependency is None when `_start_monitoring` tries to use it

**Solution:**
- Need to expand the full function to see what's being initialized
- Likely need to add defensive checks before calling methods
- Ensure all dependencies are properly initialized before use

---

### Issue 3: Settings configuration crash - 'int' object has no attribute 'get'
**Symptom:** `AttributeError: 'int' object has no attribute 'get'` at `settings.get('selected_target_group', {}).get('title', 'None')`

#### Root Cause Analysis

**What is `settings.get('selected_target_group')`?**
From `src/core/settings.py:19-20`:
```python
"selected_target_group": None,  # Default is None
```

But looking at usage in `src/cli/commands/group.py:120`:
```python
settings['selected_target_group'] = selected_group['id']  # Saves as INT
```

And in `src/cli/commands/group.py:78`:
```python
settings['selected_target_group'] = None  # Clears to None
```

**Why is it returning an int instead of dict?**
- **Legacy format:** Old code saved just the group ID (int)
- **New format:** New code expects a dict with `{'id': ..., 'title': ..., 'is_forum': ...}`
- **Mixed state:** The settings file has the old format (int), but the display code expects the new format (dict)

**Where is the data corruption happening?**
- It's not "corruption" - it's a format migration issue
- `group.py:120` saves as int: `settings['selected_target_group'] = selected_group['id']`
- But `monitor_handler.py:84` reads as dict: `settings.get('selected_target_group', {}).get('title', 'None')`

**Solution:**
- Use the `normalize_selected_group()` function consistently
- Update the display code to handle both formats:
  ```python
  from src.cli.utils import normalize_selected_group
  target_group = normalize_selected_group(settings.get('selected_target_group'))
  title = target_group.get('title', 'None') if target_group else 'None'
  ```
- OR: Use the default `{}` fallback but check type first:
  ```python
  target = settings.get('selected_target_group', {})
  if isinstance(target, dict):
      title = target.get('title', 'None')
  else:
      title = f"Group {target}" if target else 'None'
  ```

---

### Issue 4: Command mappings table should show topic names
**Current behavior:** `Topic ID: 2`
**Wanted behavior:** `Topic ID: 2 (General Discussion)`

#### Root Cause Analysis

**Where are topic names stored?**
- Topics are fetched from Telegram forums using the client
- Topic info includes: `id`, `title`, and other metadata
- Topics are displayed in `src/cli/commands/group.py` when listing topics

**How to map topic_id → topic_name?**
Looking at `src/cli/commands/group.py:261`:
```python
target = f"Topic ID: {topic_id}"
```

The code needs to:
1. Fetch the forum topics from the selected group
2. Build a mapping of topic_id → topic_title
3. Use that mapping when displaying the table

**Solution approach:**
1. When listing mappings, check if target group is set
2. If it's a forum, fetch the topics
3. Create a `topic_id_to_name` dict
4. Update line 261 to:
   ```python
   topic_name = topic_id_to_name.get(topic_id, "Unknown Topic")
   target = f"Topic ID: {topic_id} ({topic_name})"
   ```

**Code location:**
- File: `src/cli/commands/group.py`
- Function: `map()` command, specifically the `action == 'list'` block (lines 246-268)
- Need to add topic fetching before the table display

---

## Summary of Root Causes

| Issue | Root Cause | Severity | Fix Complexity |
|-------|------------|----------|----------------|
| #1 Format warning | Over-aggressive normalization comparison | Low | Easy |
| #2 NoneType callable | Missing initialization or import issue | High | Medium |
| #3 Int has no .get() | Mixed old/new format for selected_target_group | Medium | Easy |
| #4 Missing topic names | Not fetching topic metadata for display | Low | Medium |

## Fix Priority

1. **Issue #3** (Highest impact) - Causes crashes, easy fix
2. **Issue #2** (High impact) - Prevents monitoring, needs investigation
3. **Issue #1** (Low impact) - Annoying but harmless, easy fix
4. **Issue #4** (Enhancement) - User experience improvement

## Next Steps

1. Create fixes for each issue in order of priority
2. Test each fix independently
3. Run automated tests
4. Manual verification
5. Commit with descriptive messages

## Files to Modify

1. `src/core/settings.py` - Fix format warning (Issue #1)
2. `src/cli/commands/monitor.py` - Fix NoneType error (Issue #2)
3. `src/cli/menu_handlers/monitor_handler.py` - Fix int.get() error (Issue #3)
4. `src/cli/commands/group.py` - Add topic names to display (Issue #4)

## Testing Strategy

- Unit tests: Run `pytest tests/unit/ -v`
- Manual testing:
  - Load CLI and check for format warnings
  - Try to start monitoring
  - View monitor settings
  - List command mappings in a forum group
