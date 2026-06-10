# Troubleshooting Guide

## Common Issues & Solutions

### Search & Performance

#### "Search is very slow"

**Symptoms**: First search takes >30 seconds; subsequent searches slow too

**Causes**:
1. Embeddings model not downloaded (first search downloads ~90 MB)
2. Large result set (1000+) being processed
3. Disk I/O bottleneck (HDD instead of SSD)

**Solutions**:
1. **First search**: Wait for model download to complete (~2-5 minutes on slow internet)
2. **Subsequent searches**: Should be <5s; if not:
   - Clear embeddings cache: Settings → "Rebuild Cache"
   - Check disk space: `~/.dataset_collector/` should have >2 GB free
   - Try fewer sources: Uncheck unused data sources

---

#### "Results table freezes when clicking details"

**Symptoms**: UI unresponsive for 5-10 seconds after clicking a result

**Causes**: Similar datasets computation happening on UI thread

**Solutions**:
1. This is expected for first dataset details (computing similarities)
2. Subsequent details open faster (cached)
3. Workaround: Reduce "Similar Datasets" limit in settings

---

#### "Search returns "No results"

**Symptoms**: Valid search returns empty results

**Causes**:
1. All selected sources offline/rate-limited
2. Query too specific (e.g., "xyz123")
3. Search cancelled mid-way

**Solutions**:
1. Try different sources (Settings → uncheck problematic sources)
2. Broaden query (e.g., "machine learning" instead of "ML-XYZ-v1")
3. Try again (may be temporary rate limit)

---

#### "Intent tags are wrong or missing"

**Symptoms**: Search shows incorrect intent (e.g., "anime" detected as "Food" instead of "Animation")

**Causes**:
1. Not enough search history for intent classifier to learn
2. Ambiguous query (e.g., "apple" could be fruit or company)

**Solutions**:
1. Intent accuracy improves with more searches
2. More specific queries help: "anime dataset" instead of "anime"
3. Clear learning data and restart: Settings → "Clear Learning Data"

---

### Model & Cache Issues

#### "Model download fails"

**Symptoms**: Error message "Failed to download model" when clicking download button

**Causes**:
1. No internet connection
2. Firewall/proxy blocking Hugging Face
3. Insufficient disk space (<500 MB)
4. Corrupted partial download

**Solutions**:
1. Check internet: Open browser, visit huggingface.co
2. Check firewall: Allow outbound HTTPS to huggingface.co, cdn-lfs.huggingface.co
3. Free up disk space: `~/.dataset_collector/` needs >500 MB free
4. Clear partial download: Delete `~/.dataset_collector/sentence-transformers/`
5. Try again: Settings → "Download Model"

---

#### "Enhanced Search shows "Not Installed""

**Symptoms**: Settings shows model status as "Not installed" even after download attempt

**Causes**:
1. Download didn't complete (interrupted or failed)
2. Model files corrupted

**Solutions**:
1. Check download folder: `ls ~/.dataset_collector/sentence-transformers/`
   - Should see: `all-MiniLM-L6-v2/` with `.bin` and `.json` files
2. Delete and re-download:
   ```bash
   rm -rf ~/.dataset_collector/sentence-transformers/
   # Click "Download Model" in settings
   ```

---

#### "Embeddings cache corrupted"

**Symptoms**: Error "Database is corrupted" when opening app

**Causes**:
1. Forced shutdown during embedding computation
2. Disk corruption

**Solutions**:
1. Clear embeddings cache:
   ```bash
   rm ~/.dataset_collector/embeddings.db
   ```
2. Restart app (will rebuild cache on next search)
3. If issues persist:
   ```bash
   rm -rf ~/.dataset_collector/cache/
   # Re-download model
   ```

---

#### "Search creates huge cache files"

**Symptoms**: `~/.dataset_collector/` grows to >5 GB

**Causes**: Embeddings cache has millions of entries

**Solutions**:
1. Check cache size:
   ```bash
   du -h ~/.dataset_collector/cache/
   ```
2. Clear cache: Settings → "Rebuild Cache"
3. Or manually:
   ```bash
   rm ~/.dataset_collector/embeddings.db
   ```

---

### Recommendations & Discovery

#### "Recommendations panel is empty"

**Symptoms**: "Recommendations" tab shows "No recommendations yet"

**Causes**:
1. No search history (brand new user)
2. No downloads recorded
3. Insufficient data for ML recommendations

**Solutions**:
1. Perform 5-10 searches first
2. Download at least 2-3 datasets
3. Recommendations improve over time (week+ of usage)

---

#### "People Also Downloaded shows nothing"

**Symptoms**: Dataset details don't show co-downloaded datasets

**Causes**:
1. Multi-download not yet triggered
2. Dataset hasn't been part of group downloads

**Solutions**:
1. Try multi-select: Check 2+ results → "Download Selected"
2. This triggers co-download logging
3. Open those datasets again to see "People Also Downloaded"

---

#### "Related Datasets shows incorrect matches"

**Symptoms**: Similar datasets seem unrelated (e.g., "anime" returns "medical imaging")

**Causes**:
1. Semantic embedding captures unexpected similarity
2. Datasets mis-categorized or tagged incorrectly

**Solutions**:
1. This is expected for datasets with misleading names/tags
2. Report via GitHub issues if systematically wrong
3. Workaround: Use keyword-only search (no semantic scoring) by disabling Enhanced Search

---

### Data & Privacy

#### "I want to reset all my data"

**Symptoms**: Want to start fresh without history

**Solutions**:
1. Clear all: Settings → "Clear Learning Data" → Yes
2. Or delete entire folder:
   ```bash
   rm -rf ~/.dataset_collector/
   ```
3. App will recreate on restart

---

#### "I'm worried about privacy"

**FAQ**:
- ✅ All data stays local (`~/.dataset_collector/`)
- ✅ No telemetry, no tracking, no cloud sync
- ✅ No personal data collected or shared
- ✅ Source code open on GitHub

---

### Installation & Updates

#### "Command not found: dataset-collector"

**Symptoms**: After `pip install`, command doesn't run

**Solutions**:
1. Try full module path:
   ```bash
   python -m dataset_collector
   ```
2. Check installation: `pip show dataset-collector`
3. Reinstall: `pip install --force-reinstall dataset-collector`

---

#### "Standalone .exe won't run"

**Symptoms**: Double-clicking .exe does nothing, or UAC prompt without launching

**Causes**:
1. Missing Visual C++ runtime
2. Antivirus blocking
3. Corrupted download

**Solutions**:
1. Install Visual C++ Redistributable: https://support.microsoft.com/en-us/help/2977003/
2. Try right-click → "Run as Administrator"
3. Re-download .exe, verify SHA256:
   ```bash
   certutil -hashfile dataset-collector.exe SHA256
   # Compare with dataset-collector.exe.sha256
   ```

---

### Specific Error Messages

#### "RuntimeError: Could not find torch installation"

**Cause**: PyTorch not installed properly

**Solution**:
```bash
pip install torch torchvision torchaudio
pip install -e .
python -m dataset_collector
```

---

#### "FileNotFoundError: ~/.dataset_collector/user_behavior.db"

**Cause**: Database corrupted or deleted during operations

**Solution**:
```bash
rm ~/.dataset_collector/user_behavior.db
# Restart app (will recreate)
```

---

#### "Unable to open database file" on Windows

**Cause**: File locked by antivirus or other process

**Solution**:
1. Close app completely
2. Disable antivirus temporarily
3. Restart app
4. Whitelist `~/.dataset_collector/` in antivirus

---

## Getting More Help

- **GitHub Issues**: [Report bug or request feature](https://github.com/yourusername/dataset-collector/issues)
- **Discussions**: [Ask questions](https://github.com/yourusername/dataset-collector/discussions)
- **Email**: support@example.com (if available)
- **Logs**: Check `~/.dataset_collector/logs/` for detailed error messages

---

## Performance Tips

### Make searches faster

1. **Narrow sources**: Uncheck unnecessary data sources
2. **Use keyword search**: Uncheck "Semantic Search" in settings if slow
3. **Smaller batches**: Search 5-10 items instead of 100+
4. **Use SSD**: HDD significantly slower than SSD for embeddings cache

### Reduce disk usage

1. Don't enable embeddings cache for massive searches (>10K datasets)
2. Periodically clear cache: Settings → "Rebuild Cache"
3. Delete old downloads: `~/.dataset_collector/downloads/`

### Improve recommendations

1. Perform varied searches (not just one topic)
2. Download multiple datasets per search
3. Return and search again (engagement signals improve ranking)
4. Let the system learn over 1-2 weeks

---

## Reporting Bugs

Please include:
1. App version: Menu → About
2. Error message (full text)
3. Steps to reproduce
4. System info: OS, Python version, disk space
5. Logs: `~/.dataset_collector/logs/` (if available)

**Example**:
```
Version: 2.4.0
Error: RuntimeError: CUDA out of memory
Steps: 
  1. Search for "anime" with all sources
  2. Select 100+ results
  3. Click "Download All"
OS: Windows 11
Python: 3.11.2
Disk: 50 GB free
```
