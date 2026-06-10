# DatasetBrain UI Debugging Features

## Summary
Added comprehensive logging and debugging features to trace DatasetBrain initialization and UI state synchronization.

## Changes Made

### 1. Main Window Logging (src/dataset_collector/ui/main_window.py)

#### _get_databrain() Method - Enhanced with Full Traceback
```python
# NOW INCLUDES:
- print("[DATABRAIN] Attempting initialization...")
- print("[DATABRAIN] Import successful, creating instance...")
- print(f"[DATABRAIN] Instance created: {self._databrain}")
- print(f"[DATABRAIN] Enabled status: {self._databrain.enabled}")
- Full exception traceback to console AND stderr
- Traceback prints to stderr immediately (not just log file)
```

**Output Example:**
```
[DATABRAIN] Attempting initialization...
[DATABRAIN] Import successful, creating instance...
[DATABRAIN] Instance created: <DatasetBrain object>
[DATABRAIN] Enabled status: True
[DATABRAIN] Search engine updated
[DATABRAIN] Setting in settings panel
[DATABRAIN] Settings panel now has: <DatasetBrain object>
```

#### Forced Initialization on Startup
- Added call to `_get_databrain()` at end of `__init__()`
- DatasetBrain no longer lazy-loaded - initializes during app startup
- All UI panels receive instance immediately after creation

```python
print("[MAINWINDOW] Forcing DatasetBrain initialization on startup...")
self._get_databrain()
print(f"[MAINWINDOW] DatasetBrain after init: {self._databrain}")
```

### 2. Settings Panel Logging (src/dataset_collector/ui/widgets/settings_panel.py)

#### set_databrain() Method
```python
print(f"[SETTINGS] set_databrain called with: {databrain}")
print(f"[SETTINGS] DatasetBrain received, enabled={databrain.enabled}")
```

#### _refresh_enhanced_search_status() Method
```python
# NOW INCLUDES:
- [SETTINGS] _refresh_enhanced_search_status called
- [SETTINGS] Has _databrain attr: True/False
- [SETTINGS] _databrain value: <object>
- [SETTINGS] _databrain is None: True/False
- [SETTINGS] Getting model status...
- [SETTINGS] Model status: {status dict}
- [SETTINGS] Setting status to 'Installed [OK]' or 'Not installed'
- [SETTINGS] Cache stats: {cache stats dict}
```

### 3. Debug Button in Settings Panel

#### New UI Component
- Button: "Test DatasetBrain (Debug)" in Enhanced Search section
- Styled with subdued colors (#3a3a3a background)
- Available in Settings tab

#### Test Button Functionality
Clicking the button displays:

```
DatasetBrain Debug Info:

Object: <DatasetBrain instance>
Enabled: True

Model Status:
- Installed: True
- Size: 174.7 MB
- Path: C:\Users\...\cache\models--sentence-transformers--...
- Embedding Dim: 384

Cache:
- Total Cached: 0 datasets
- Total Size: 0.0 MB

Components:
- model_manager: <ModelManager>
- embeddings_cache: <EmbeddingsCache>
- behavior_tracker: <UserBehaviorTracker>
```

### 4. Exception Handling Improvements

#### Before:
```python
except Exception as e:
    error_msg = f"Failed to initialize DatasetBrain: {e}"
    self._logger.error(error_msg)  # Silent swallowing
```

#### After:
```python
except Exception as e:
    error_msg = f"Failed to initialize DatasetBrain: {e}"
    print(f"[DATABRAIN ERROR] {error_msg}")
    print("[DATABRAIN] Full traceback:")
    import traceback
    traceback.print_exc()
    self._logger.error(error_msg)
    import sys
    sys.stderr.write(f"\n[DATABRAIN INITIALIZATION FAILED]\n{error_msg}\n")
    traceback.print_exc(file=sys.stderr)
```

## How to Use These Features

### 1. Check Console Output During App Startup
```
[MAINWINDOW] Forcing DatasetBrain initialization on startup...
[DATABRAIN] Attempting initialization...
[DATABRAIN] Import successful, creating instance...
[DATABRAIN] Instance created: <DatasetBrain object>
[DATABRAIN] Enabled status: True
```

### 2. View Settings Panel Status
- Go to Settings tab
- Look at "Enhanced Search (DatasetBrain)" section
- Status should show "Installed [OK]" if DatasetBrain works
- If shows "DatasetBrain not available", check console for errors

### 3. Click "Test DatasetBrain" Debug Button
- Opens dialog showing:
  - Whether DatasetBrain object exists
  - Model installation status
  - Model size and location
  - Cache statistics
  - All component instances

### 4. Check Log File
- Log file: `~/.dataset_collector/logs/app.log`
- Contains: error_msg with context
- Combined with console output for full picture

## Testing Workflow

```
1. Run app: python -m dataset_collector
2. Watch console output [DATABRAIN] messages
3. If issues occur:
   - Check console traceback
   - Check ~/.dataset_collector/logs/app.log
   - Click "Test DatasetBrain" button
   - Compare model status with manual CLI test
```

## Example: Debugging Failed Initialization

### If DatasetBrain shows "not available":

**Console will show:**
```
[MAINWINDOW] Forcing DatasetBrain initialization on startup...
[DATABRAIN] Attempting initialization...
[DATABRAIN] Import successful, creating instance...
[DATABRAIN ERROR] Failed to initialize DatasetBrain: [Some Error]
[DATABRAIN] Full traceback:
Traceback (most recent call last):
  File "...main_window.py", line 92, in _get_databrain
    self._databrain = DB(self._config, self._logger)
  File "...databrain/__init__.py", line 38, in __init__
    self.model_manager = ModelManager(config, logger, download_on_init=True)
[Error Details...]
```

### Then:

**Settings Panel will show:**
```
[SETTINGS] set_databrain called with: None
[SETTINGS] DatasetBrain is None
[SETTINGS] _refresh_enhanced_search_status called
[SETTINGS] Has _databrain attr: False
[SETTINGS] Setting status to 'DatasetBrain not available'
```

**Log File (~/.dataset_collector/logs/app.log):**
```
Failed to initialize DatasetBrain: [Full error message]
```

## Files Modified

1. `src/dataset_collector/ui/main_window.py`
   - Enhanced _get_databrain() with full logging
   - Added forced initialization in __init__()

2. `src/dataset_collector/ui/widgets/settings_panel.py`
   - Enhanced set_databrain() with logging
   - Enhanced _refresh_enhanced_search_status() with logging
   - Added _on_test_databrain() method
   - Added debug button to UI

## Benefits

1. **Complete Visibility**: All initialization steps logged and printed
2. **Immediate Feedback**: Console output shows problems instantly
3. **Easy Debugging**: Can identify exact failure point
4. **User-Friendly**: Debug button shows status without code knowledge
5. **No More Silent Failures**: Every exception shows full traceback
6. **Synchronized State**: Forced initialization ensures all panels get instance

---

**Status**: All 19 tests passing
**Ready for**: v2.4.3 commit
