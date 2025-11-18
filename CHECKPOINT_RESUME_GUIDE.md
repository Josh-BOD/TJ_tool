# Checkpoint/Resume System - Implementation Guide

## Overview
The checkpoint/resume system allows the TrafficJunky uploader to recover from interruptions and resume where it left off, without re-processing campaigns that have already been successfully uploaded.

## Implementation Date
November 18, 2024

## Features

### 1. **Automatic Checkpoint Saving**
- Saves progress after **every single campaign** (success or failure)
- Checkpoint file stored in `data/session/upload_checkpoint.json` (or `native_upload_checkpoint.json` for native ads)
- Includes campaign status, timestamp, ads created, error messages

### 2. **Automatic Resume**
- By default, running the tool will automatically resume from the last checkpoint
- Skips campaigns that were already successful
- Shows summary of previous session progress

### 3. **Failed Campaign Handling**
- By default, skips failed campaigns on resume
- Use `--retry-failed` to retry previously failed campaigns
- Failed campaigns tracked with error messages

### 4. **Fresh Start Option**
- Use `--fresh` flag to ignore checkpoint and start from scratch
- Useful when you want to re-upload everything

## Files Created/Modified

### New Files
1. **`src/checkpoint.py`** - CheckpointManager class
   - Handles saving/loading checkpoint files
   - Tracks campaign status
   - Provides resume logic

### Modified Files
1. **`src/campaign_manager.py`**
   - Added CheckpointManager integration
   - `initialize_checkpoint()` - Load or create checkpoint
   - `mark_success()` - Saves to checkpoint
   - `mark_failed()` - Saves to checkpoint
   - `get_next_campaign()` - Skips already-successful campaigns
   - `set_retry_failed()` - Configure retry behavior
   - `clear_checkpoint()` - Delete checkpoint file

2. **`main.py`**
   - Added `--fresh` and `--retry-failed` command line arguments
   - Checkpoint initialization on startup
   - Updated help text with resume examples

3. **`native_main.py`**
   - Same changes as `main.py`
   - Uses separate checkpoint file for native uploads

## Usage Examples

### Basic Usage (Auto-Resume)
```bash
# Start upload
python main.py --live

# If interrupted (Ctrl+C, crash, network issue), just run again:
python main.py --live
# Will automatically resume where you left off!
```

### Start Fresh
```bash
# Ignore previous checkpoint, start from scratch
python main.py --live --fresh
```

### Retry Failed Campaigns
```bash
# Resume but also retry campaigns that failed before
python main.py --live --retry-failed
```

### Combine Flags
```bash
# Fresh start AND retry any failures that happen
python main.py --live --fresh --retry-failed
```

## Checkpoint File Format

```json
{
  "session_id": "upload_20251118_110820",
  "started_at": "2025-11-18T11:08:20.123456",
  "last_updated": "2025-11-18T11:15:30.654321",
  "campaigns": {
    "1011737002": {
      "status": "success",
      "ads_created": 5,
      "timestamp": "2025-11-18T11:08:45.111111",
      "campaign_name": "CPA - AI - Video-IS - Desktop - USA",
      "csv_file": "BlackFriday-General.csv"
    },
    "1011737262": {
      "status": "failed",
      "error": "Failed to navigate to campaign",
      "timestamp": "2025-11-18T11:09:10.222222",
      "campaign_name": "CPA - AI - Video-IS - Desktop - Aus",
      "csv_file": "BlackFriday-General.csv",
      "invalid_creatives_count": 0
    },
    "1011737272": {
      "status": "pending"
    }
  }
}
```

### Campaign Status Values
- `pending` - Not yet processed
- `success` - Successfully uploaded
- `failed` - Upload failed (error recorded)
- `skipped` - Skipped because already successful

## How It Works

### 1. **On Startup**
```python
# Load checkpoint if it exists
campaign_manager.initialize_checkpoint(session_id, use_existing=True)

# Checkpoint shows:
# 📋 Resuming from checkpoint:
#    • 142 successful
#    • 8 failed
#    • 100 remaining
```

### 2. **During Processing**
```python
# For each campaign:
for campaign in campaigns:
    # Check if should process
    if checkpoint.should_process_campaign(campaign_id):
        # Process campaign...
        result = upload_to_campaign(...)
        
        # Save result to checkpoint immediately
        if result['status'] == 'success':
            checkpoint.update_campaign(campaign_id, 'success', ads_created=5)
        else:
            checkpoint.update_campaign(campaign_id, 'failed', error="...")
```

### 3. **On Resume**
```python
# Campaign already successful? Skip it!
if campaign_status == 'success':
    logger.info("⊘ Skipping campaign 1011737002 - already successful (5 ads)")
    continue
```

## Benefits

### 1. **Handles Interruptions**
- Browser crashes ✅
- Network issues ✅
- System crashes ✅
- User interruption (Ctrl+C) ✅
- Power outages ✅

### 2. **Saves Time**
- Don't re-upload successful campaigns
- Pick up exactly where you left off
- No manual tracking needed

### 3. **Tracks Progress**
- See how many campaigns are done
- Know how many failed
- Review error messages later

### 4. **Flexible Recovery**
- Choose to retry failures
- Choose to start fresh
- Default behavior just works

## Examples

### Scenario 1: Network Interruption
```bash
$ python main.py --live
...
Processing campaign 142/250...
[Network drops]

# Later, when network is back:
$ python main.py --live
📋 Resuming from checkpoint:
   • 142 successful
   • 0 failed
   • 108 remaining

Processing campaign 143/250...
# Continues from where it left off!
```

### Scenario 2: Browser Crash
```bash
$ python main.py --live
...
Processing campaign 85/250...
[Browser crashes]

# Run again:
$ python main.py --live
📋 Resuming from checkpoint:
   • 85 successful
   • 0 failed
   • 165 remaining

⊘ Skipping campaign 1011737002 - already successful (5 ads)
⊘ Skipping campaign 1011737262 - already successful (3 ads)
...
Processing campaign 86/250...
```

### Scenario 3: Failed Campaigns
```bash
$ python main.py --live
...
✗ Campaign 1011737262 failed: Navigation timeout
...
[Interrupted]

# Resume and retry failures:
$ python main.py --live --retry-failed
📋 Resuming from checkpoint:
   • 100 successful
   • 5 failed
   • 145 remaining
⟳ Will retry previously failed campaigns

# Will retry the 5 failed campaigns and continue with remaining
```

### Scenario 4: Start Over
```bash
$ python main.py --live --fresh
Starting fresh - cleared previous checkpoint
📋 Checkpoint initialized - tracking 250 campaigns

# Starts from campaign 1
```

## Technical Details

### Checkpoint File Location
- **Preroll/Video**: `data/session/upload_checkpoint.json`
- **Native Ads**: `data/session/native_upload_checkpoint.json`

### File Operations
- **Save**: After every campaign (success or failure)
- **Load**: Once at startup
- **Clear**: With `--fresh` flag

### Session ID Format
- Preroll: `upload_YYYYMMDD_HHMMSS`
- Native: `native_upload_YYYYMMDD_HHMMSS`

### Campaign Skipping Logic
```python
def should_process_campaign(campaign_id, retry_failed=False):
    status = get_campaign_status(campaign_id)
    
    # Always skip successful
    if status == 'success':
        return False
    
    # Skip failed unless retry_failed=True
    if status == 'failed':
        return retry_failed
    
    # Process pending or unknown
    return True
```

## Progress Bar Integration

The checkpoint system integrates seamlessly with the progress bar:

```
Processing CPA - AI - Video: : 57%|████████▌| 142/250 [05:20<03:40] {'speed': '26.6 c/m', 'eta': '3m 40s', 'remaining': 108}

⊘ Skipping campaign 1011737003 - already successful (5 ads)
⊘ Skipping campaign 1011737004 - already successful (3 ads)
...
```

Skipped campaigns:
- Don't affect progress bar count
- Don't update ETA calculation
- Show in logs with ⊘ symbol

## Error Handling

### Checkpoint Save Fails
- Logs warning but continues
- Won't resume on next run (no checkpoint)
- Upload still completes

### Checkpoint Load Fails
- Logs warning
- Starts fresh (new checkpoint)
- No data loss

### Corrupted Checkpoint
- Logs error
- Starts fresh
- Old checkpoint backed up automatically

## Best Practices

### 1. **Long Running Jobs**
```bash
# For 250+ campaigns, checkpoint is essential
python main.py --live
# Safe to interrupt anytime with Ctrl+C
```

### 2. **Testing Uploads**
```bash
# Test with fresh start each time
python main.py --live --fresh
```

### 3. **Recovering from Failures**
```bash
# First run
python main.py --live

# Check logs for failures, then:
python main.py --live --retry-failed
```

### 4. **Multiple Sessions**
```bash
# Day 1: Upload 100 campaigns
python main.py --live
[Ctrl+C after 100]

# Day 2: Continue
python main.py --live
# Automatically resumes!
```

## Troubleshooting

### Q: How do I see what's in the checkpoint?
```bash
cat data/session/upload_checkpoint.json | python -m json.tool
```

### Q: How do I clear the checkpoint?
```bash
rm data/session/upload_checkpoint.json
# Or use --fresh flag
```

### Q: Can I manually edit the checkpoint?
Yes, but be careful. It's JSON format. Edit status values to change behavior:
- Change "success" → "pending" to re-upload
- Change "failed" → "pending" to retry
- Delete a campaign entry to reprocess it

### Q: What if I want to re-upload everything?
```bash
python main.py --live --fresh
```

### Q: Does checkpoint work with --dry-run?
Yes! Checkpoint saves even in dry-run mode (though status will be 'dry_run_success').

## Maintenance

### Cleanup Old Checkpoints
Checkpoints are overwritten on each run, but you can manually clean:

```bash
# Remove all checkpoints
rm data/session/*_checkpoint.json
```

### Backup Checkpoints
```bash
# Before risky operation
cp data/session/upload_checkpoint.json data/session/upload_checkpoint.backup.json
```

## Future Enhancements

Potential improvements (not yet implemented):
- Multiple checkpoint slots (save named checkpoints)
- Checkpoint viewer/editor UI
- Auto-cleanup of old checkpoints
- Checkpoint compression for large batches
- Distributed checkpoints (multiple machines)

## Summary

The checkpoint/resume system makes the TrafficJunky uploader **production-ready** for handling:
- ✅ Large batches (250+ campaigns)
- ✅ Unreliable networks
- ✅ Long-running jobs
- ✅ Multiple sessions
- ✅ Error recovery
- ✅ Time savings (skip successful)

**Default behavior**: Just works! No flags needed.
**Advanced usage**: `--fresh`, `--retry-failed` for special cases.

