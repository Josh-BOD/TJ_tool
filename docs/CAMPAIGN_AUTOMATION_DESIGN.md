# Campaign Automation Design

## Overview

Automated end-to-end campaign creation system for TrafficJunky Native campaigns. Creates Desktop, iOS, and Android campaign variants from templates with full configuration and CSV ad upload.

---

## System Architecture

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Campaign Creation Tool                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │   Input      │───▶│   Campaign   │───▶│  Playwright  │     │
│  │   Parser     │    │   Orchestr.  │    │  Automation  │     │
│  │ (YAML/CSV)   │    │              │    │              │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│         │                    │                    │             │
│         │                    │                    │             │
│         ▼                    ▼                    ▼             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │  Validation  │    │  Checkpoint  │    │     CSV      │     │
│  │              │    │   Manager    │    │   Uploader   │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Input Formats

### Option 1: YAML (Recommended for Complex Campaigns)

```yaml
# campaign_definitions.yaml

# Global defaults (can be overridden per campaign)
defaults:
  geo: ["US"]
  target_cpa: 50
  per_source_test_budget: 200
  max_bid: 10
  frequency_cap: 2
  max_daily_budget: 250
  gender: "male"
  variants: ["desktop", "ios", "android"]

# Campaign sets to create
campaigns:
  - name: "Milfs"
    group: "Milfs"
    keywords:
      - name: "milfs"
        match_type: "broad"
      - name: "milf porn"
        match_type: "exact"
      - name: "cougar"
        match_type: "exact"
    csv_file: "Milfs.csv"
    settings:
      target_cpa: 55
      per_source_test_budget: 100
      max_bid: 11
      frequency_cap: 1
      max_daily_budget: 275
    variants: ["desktop", "ios", "android"]

  - name: "Cougars"
    group: "Cougars"
    geo: ["AU", "NZ"]  # Override default geo
    keywords:
      - name: "cougar"
        match_type: "broad"
      - name: "cougars"
        match_type: "exact"
    csv_file: "Cougars.csv"
    # Uses defaults for other settings
    variants: ["desktop", "ios"]  # Only Desktop and iOS

  - name: "MatureMoms"
    group: "Mature"
    keywords:
      - name: "mature moms"
        match_type: "broad"
    csv_file: "MatureMoms.csv"
    variants: ["desktop"]  # Desktop only
```

### Option 2: CSV (Simple, Spreadsheet-Friendly)

**File: `campaign_batch.csv`**

| group | keywords | keyword_matches | geo | csv_file | target_cpa | per_source_budget | max_bid | frequency_cap | max_daily_budget | variants | enabled |
|-------|----------|-----------------|-----|----------|------------|-------------------|---------|---------------|------------------|----------|---------|
| Milfs | milfs;milf porn;cougar | broad;exact;exact | US | Milfs.csv | 55 | 100 | 11 | 1 | 275 | desktop,ios,android | true |
| Cougars | cougar;cougars | broad;exact | AU;NZ | Cougars.csv | 50 | 200 | 10 | 2 | 250 | desktop,ios | true |
| MatureMoms | mature moms | broad | US | MatureMoms.csv | 50 | 200 | 10 | 2 | 250 | desktop | true |

**CSV Conventions:**
- `;` separates multiple values within a cell (keywords, geo)
- `,` separates variants
- Empty cells use system defaults
- `enabled=false` skips the campaign

---

## Template Configuration

**File: `src/campaign_templates.py`**

```python
# Template campaign IDs (CONSTANTS - never change)
TEMPLATE_CAMPAIGNS = {
    "desktop": {
        "id": "1013076141",
        "name": "TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTER-Keywords_DESK_M_JB",
        "device": "desktop"
    },
    "ios": {
        "id": "1013076221", 
        "name": "TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTERKEYWORDS_iOS_M_JB",
        "device": "mobile",
        "os": "iOS"
    },
    "android": {
        # Android clones from iOS, not from template
        "clone_from": "ios",
        "device": "mobile",
        "os": "Android"
    }
}

# Default values (can be overridden)
DEFAULT_SETTINGS = {
    "target_cpa": 50.0,
    "per_source_test_budget": 200.0,
    "max_bid": 10.0,
    "frequency_cap": 2,
    "max_daily_budget": 250.0,
    "gender": "male",
    "conversion_tracker": "Redtrack - Purchase"
}

# Campaign naming convention
NAMING_PATTERN = "{geo}_{lang}_{format}_{bid_type}_{source}_{keyword_type}-{keyword}_{device}_{gender}_{user}"
# Example: US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB
```

---

## Workflow Steps

### Phase 1: Initialization
1. Parse input (YAML or CSV)
2. Validate campaign definitions
3. Check for existing checkpoint (resume if found)
4. Initialize progress tracker
5. Launch Playwright browser (reuse existing session if logged in)

### Phase 2: Campaign Creation Loop

For each campaign definition:

#### A. Desktop Campaign (from template)
1. Navigate to campaigns page
2. Search for Desktop template (`1013076141`)
3. Clone template
4. **Basic Settings:**
   - Update campaign name
   - Set/create group
   - Verify gender
5. **Audience (Geo Targeting):**
   - Remove existing geo targets
   - Add new countries
6. **Audience (Keywords):**
   - Remove all existing keywords
   - Add new keywords with correct match types
7. **Tracking, Sources & Rules:**
   - Verify conversion tracker
   - Update Target CPA, Per Source Budget, Max Bid
   - Include all sources
8. **Schedule & Budget:**
   - Update Frequency Capping
   - Update Max Daily Budget
9. **Ad Creation:**
   - Set page length to 100 (if ads exist)
   - Delete all existing ads (if any)
   - Upload CSV via `native_uploader.py`
   - Click "Save Campaign"
10. Record campaign ID for iOS cloning
11. **Checkpoint:** Save progress

#### B. iOS Campaign (from template)
1. Search for iOS template (`1013076221`)
2. Clone template
3. Follow same steps as Desktop, plus:
   - **Audience (OS Targeting):** Add iOS to included OS
4. Record campaign ID for Android cloning
5. **Checkpoint:** Save progress

#### C. Android Campaign (clone from iOS)
1. Search for the just-created iOS campaign (by ID)
2. Clone iOS campaign
3. **Basic Settings:** Update campaign name (iOS → AND)
4. **Audience (OS Targeting):** 
   - Remove iOS
   - Add Android
5. **Ad Creation:**
   - Delete inherited iOS ads
   - Upload Android CSV
   - Save Campaign
6. **Checkpoint:** Save progress

### Phase 3: Completion
1. Generate summary report
2. Log all created campaign IDs
3. Display success/error statistics

---

## Progress Tracking & Checkpointing

**File: `data/checkpoints/campaign_creation_TIMESTAMP.json`**

```json
{
  "session_id": "20250120_143022",
  "input_file": "campaign_definitions.yaml",
  "total_campaigns": 3,
  "completed_campaigns": 1,
  "failed_campaigns": 0,
  "status": "in_progress",
  "started_at": "2025-01-20T14:30:22Z",
  "updated_at": "2025-01-20T14:35:10Z",
  "campaigns": [
    {
      "name": "Milfs",
      "group": "Milfs",
      "status": "completed",
      "variants": {
        "desktop": {
          "status": "completed",
          "campaign_id": "1013076301",
          "campaign_name": "US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB",
          "ads_uploaded": 15,
          "completed_at": "2025-01-20T14:35:10Z"
        },
        "ios": {
          "status": "completed",
          "campaign_id": "1013076302",
          "campaign_name": "US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB",
          "ads_uploaded": 15,
          "completed_at": "2025-01-20T14:37:45Z"
        },
        "android": {
          "status": "completed",
          "campaign_id": "1013076303",
          "campaign_name": "US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB",
          "ads_uploaded": 15,
          "completed_at": "2025-01-20T14:39:20Z"
        }
      }
    },
    {
      "name": "Cougars",
      "group": "Cougars",
      "status": "in_progress",
      "variants": {
        "desktop": {
          "status": "in_progress",
          "step": "audience_keywords"
        },
        "ios": {
          "status": "pending"
        }
      }
    },
    {
      "name": "MatureMoms",
      "status": "pending"
    }
  ]
}
```

**Resume Behavior:**
- If checkpoint exists and is incomplete, ask user to resume or start fresh
- Skip already-completed campaigns
- Continue from last incomplete step

---

## Progress Bar Display

```
Creating Campaigns: Milfs (1/3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 

  ✓ Desktop (1013076301)  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
    └─ 15 ads uploaded
  ✓ iOS (1013076302)      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
    └─ 15 ads uploaded
  ⏳ Android               ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  85%
    └─ Uploading CSV...

Overall Progress: 2/3 campaigns completed (66%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 66%
```

---

## Error Handling

### Strategy: Log and Continue

When an error occurs:
1. **Log the error** to `logs/campaign_creation_errors.log`
2. **Update checkpoint** with error details
3. **Mark campaign/variant as failed**
4. **Continue to next campaign/variant**
5. **Display summary at end** showing all failures

### Example Error Log Entry:

```
[2025-01-20 14:45:30] ERROR - Campaign: Cougars, Variant: desktop
Step: audience_keywords
Error: Timeout waiting for keyword dropdown to open
Traceback: ...
Action: Skipping Cougars-desktop, continuing to next variant
```

### Retry Logic:
- Playwright timeouts: 3 retries with exponential backoff
- UI element not found: 2 retries after 2 seconds
- CSV upload errors: Logged, campaign marked as failed, continue

---

## CLI Interface

```bash
# Create campaigns from YAML
python create_campaigns.py --input campaigns.yaml

# Create campaigns from CSV
python create_campaigns.py --input campaign_batch.csv

# Dry run (validate and preview without creating)
python create_campaigns.py --input campaigns.yaml --dry-run

# Resume from checkpoint
python create_campaigns.py --resume

# Force fresh start (ignore checkpoint)
python create_campaigns.py --input campaigns.yaml --fresh

# Specify CSV directory
python create_campaigns.py --input campaigns.yaml --csv-dir data/input/

# Take screenshots for debugging
python create_campaigns.py --input campaigns.yaml --screenshots
```

---

## Output Files

### Created Files:
1. **Checkpoint:** `data/checkpoints/campaign_creation_TIMESTAMP.json`
2. **Summary Report:** `data/reports/campaign_summary_TIMESTAMP.txt`
3. **Error Log:** `logs/campaign_creation_errors.log`
4. **Campaign Mapping:** `data/output/campaign_mapping_TIMESTAMP.csv` (for use with uploader later)

### Summary Report Example:

```
=================================================================
CAMPAIGN CREATION SUMMARY
=================================================================
Session: 20250120_143022
Input File: campaign_definitions.yaml
Started: 2025-01-20 14:30:22
Completed: 2025-01-20 15:05:45
Duration: 35m 23s

-----------------------------------------------------------------
RESULTS
-----------------------------------------------------------------
Total Campaigns: 3
  ✓ Completed: 2 (Milfs, Cougars)
  ✗ Failed: 1 (MatureMoms)

Total Variants Created: 7
  ✓ Desktop: 3
  ✓ iOS: 2
  ✓ Android: 2

-----------------------------------------------------------------
CREATED CAMPAIGNS
-----------------------------------------------------------------

Campaign: Milfs (Group: Milfs)
  ✓ Desktop: 1013076301 - US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB (15 ads)
  ✓ iOS:     1013076302 - US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB (15 ads)
  ✓ Android: 1013076303 - US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB (15 ads)

Campaign: Cougars (Group: Cougars)
  ✓ Desktop: 1013076304 - AU_EN_NATIVE_CPA_ALL_KEY-Cougars_DESK_M_JB (12 ads)
  ✓ iOS:     1013076305 - AU_EN_NATIVE_CPA_ALL_KEY-Cougars_iOS_M_JB (12 ads)

-----------------------------------------------------------------
FAILED CAMPAIGNS
-----------------------------------------------------------------

Campaign: MatureMoms
  ✗ Desktop: Error during keyword selection (timeout)
    See: logs/campaign_creation_errors.log

-----------------------------------------------------------------
NEXT STEPS
-----------------------------------------------------------------
1. Review failed campaigns in error log
2. Manually fix failed campaigns or re-run with corrected settings
3. Use created campaigns with existing uploader tools

Campaign IDs saved to: data/output/campaign_mapping_20250120_143022.csv
=================================================================
```

---

## File Structure

```
TJ_tool/
├── src/
│   ├── campaign_automation/
│   │   ├── __init__.py
│   │   ├── input_parser.py          # Parse YAML/CSV
│   │   ├── campaign_orchestrator.py # Main orchestration
│   │   ├── campaign_creator.py      # Playwright automation
│   │   ├── checkpoint_manager.py    # Save/load progress
│   │   ├── progress_tracker.py      # Progress bars
│   │   └── validator.py             # Input validation
│   ├── campaign_templates.py        # Template IDs & defaults
│   └── native_uploader.py           # Existing CSV uploader
├── create_campaigns.py              # CLI entry point
├── data/
│   ├── input/
│   │   ├── campaigns.yaml           # User-created
│   │   ├── campaign_batch.csv       # User-created
│   │   └── *.csv                    # Ad CSVs
│   ├── checkpoints/
│   │   └── campaign_creation_*.json
│   └── output/
│       └── campaign_mapping_*.csv
├── logs/
│   └── campaign_creation_errors.log
└── docs/
    ├── CAMPAIGN_CLONE_WORKFLOW.md   # Manual workflow (done)
    └── CAMPAIGN_AUTOMATION_DESIGN.md # This file
```

---

## Development Phases

### Phase 1: Core Infrastructure ✅ (Week 1)
- [ ] Input parsers (YAML & CSV)
- [ ] Campaign data models
- [ ] Validation logic
- [ ] Checkpoint manager
- [ ] Progress tracker with progress bars

### Phase 2: Campaign Creation ✅ (Week 2)
- [ ] Desktop campaign creation (from template)
- [ ] iOS campaign creation (from template)
- [ ] Android campaign creation (clone iOS)
- [ ] Integration with `native_uploader.py`
- [ ] Error handling & logging

### Phase 3: CLI & Testing ✅ (Week 3)
- [ ] CLI interface (`create_campaigns.py`)
- [ ] Dry-run mode
- [ ] Resume functionality
- [ ] End-to-end testing
- [ ] Documentation

### Phase 4: Refinement ✅ (Week 4)
- [ ] Performance optimization
- [ ] Better error messages
- [ ] Screenshot debugging mode
- [ ] User guide & examples

---

## Testing Strategy

### Unit Tests
- Input parser (YAML/CSV parsing)
- Validation logic
- Checkpoint save/load
- Campaign naming convention

### Integration Tests
- Full campaign creation flow (dry-run mode)
- Error handling scenarios
- Resume from checkpoint
- Progress tracking

### Manual Testing
- Create 3-5 test campaigns
- Verify all settings applied correctly
- Test error recovery
- Test resume functionality

---

## Notes & Considerations

1. **Browser Session:** Reuse existing logged-in Playwright session
2. **Rate Limiting:** Add small delays between campaigns to avoid UI issues
3. **Screenshot Mode:** Optional screenshots at each step for debugging
4. **Idempotency:** Check if campaign already exists before creating (by name)
5. **CSV File Paths:** Support both absolute and relative paths
6. **Naming Conflicts:** Warn if campaign name already exists
7. **Group Creation:** Auto-create groups if they don't exist
8. **Template Verification:** Verify template IDs exist before starting batch

---

## Future Enhancements

- [ ] Web UI for campaign management
- [ ] Schedule campaign creation for off-hours
- [ ] Auto-pause campaigns after X spend
- [ ] Integration with API for post-creation monitoring
- [ ] Slack notifications (optional)
- [ ] Campaign performance tracking dashboard
- [ ] Bulk campaign editing tool
- [ ] CSV template generator

