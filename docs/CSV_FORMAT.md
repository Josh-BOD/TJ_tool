# Campaign CSV Format Guide

## Overview

The campaign automation tool uses a CSV file to define campaigns. This guide explains the format and features.

## CSV Columns

### Required Columns

| Column | Description | Example |
|--------|-------------|---------|
| `group` | Campaign group name | `Milfs` |
| `keywords` | Semicolon-separated list | `milf;milfs;milf porn;cougar` |
| `csv_file` | Path to ad CSV file (relative to `data/input/`) | `ads.csv` |
| `variants` | Comma-separated device types | `desktop,ios,android` |
| `enabled` | Enable this row | `TRUE` or `FALSE` |

### Optional Columns

| Column | Description | Default | Example |
|--------|-------------|---------|---------|
| `keyword_matches` | Match types (see below) | All exact | `broad` or `broad;broad` |
| `gender` | Target gender | `male` | `male`, `female`, or `all` |
| `geo` | Geos for ONE campaign | `US` | `US;CA;UK` |
| `multi_geo` | Create SEPARATE campaigns per geo | - | `CA;AUS` |
| `target_cpa` | Target CPA | `50.0` | `50` |
| `per_source_budget` | Per-source test budget | `200.0` | `100` |
| `max_bid` | Maximum bid | `10.0` | `10` |
| `frequency_cap` | Frequency cap | `2` | `1` |
| `max_daily_budget` | Maximum daily budget | `250.0` | `250` |
| `ios_version` | iOS version constraint | All versions | `>18.4` |
| `android_version` | Android version constraint | All versions | `>11.0` |

## Features

### 1. Simplified Keyword Match Types

**Old Way (verbose):**
```csv
keywords,keyword_matches
"milf;milfs;milf porn;cougar;older woman","broad;exact;exact;exact;exact"
```

**New Way (simplified):**
```csv
keywords,keyword_matches
"milf;milfs;milf porn;cougar;older woman","broad"
```

**How it works:**
- Only specify "broad" for keywords that need it
- All remaining keywords automatically default to "exact"

**Examples:**
- `keyword_matches: "broad"` → First keyword is broad, rest are exact
- `keyword_matches: "broad;broad"` → First 2 keywords are broad, rest are exact
- `keyword_matches: ""` (or omit) → All keywords are exact

### 2. Multi-Geo Expansion

Create separate campaigns for multiple geos with identical settings.

**Use `multi_geo` column** to create separate campaigns:

```csv
group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,variants,enabled
Milfs,"milf;milfs;mature",broad,male,,CA;AUS,ads.csv,"desktop,ios,android",TRUE
```

**Result:**
- **Campaign 1:** Milfs-CA (targeting CA)
  - Desktop, iOS, Android variants
- **Campaign 2:** Milfs-AUS (targeting AUS)
  - Desktop, iOS, Android variants

### 3. Multi-Geo Single Campaign

Use the `geo` column to target multiple geos in **one campaign**:

```csv
group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,variants,enabled
Milfs,"milf;milfs;mature",broad,female,US;CA;UK,,ads.csv,"desktop,ios,android",TRUE
```

**Result:**
- **Campaign 1:** Milfs (targeting US+CA+UK together)
  - Desktop, iOS, Android variants

## Complete Examples

### Example 1: Multiple Campaigns for Different Geos

Create separate campaigns for CA and AUS:

```csv
group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,variants,enabled
Milfs,"milf;milfs;milf porn;cougar;older woman",broad,male,,CA;AUS,Batch011_Native_Milf.csv,50,100,10,1,250,"desktop,ios,android",TRUE
```

This creates **6 campaigns total**:
- Milfs-CA-Desktop
- Milfs-CA-iOS
- Milfs-CA-Android
- Milfs-AUS-Desktop
- Milfs-AUS-iOS
- Milfs-AUS-Android

### Example 2: Single Campaign with Multiple Geos

Create one campaign targeting multiple countries:

```csv
group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,variants,enabled
Milfs,"milf;milfs;mature",broad;broad,female,US;CA;UK,,ads.csv,50,100,10,1,250,"desktop,ios,android",TRUE
```

This creates **3 campaigns total**:
- Milfs-Desktop (targeting US+CA+UK)
- Milfs-iOS (targeting US+CA+UK)
- Milfs-Android (targeting US+CA+UK)

### Example 3: Multiple Rows with Different Settings

```csv
group,keywords,keyword_matches,gender,geo,multi_geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,variants,enabled
Milfs,"milf;milfs;mature",broad,male,,CA;AUS,milf_ads.csv,50,100,10,1,250,"desktop,ios,android",TRUE
Cougars,"cougar;cougars",broad,female,US,,cougar_ads.csv,60,150,12,2,300,"desktop,ios",TRUE
```

**Row 1 creates:**
- Milfs-CA (Desktop, iOS, Android)
- Milfs-AUS (Desktop, iOS, Android)

**Row 2 creates:**
- Cougars (targeting US, Desktop and iOS only)

## Important Notes

1. **Use either `geo` OR `multi_geo`, not both**
   - If `multi_geo` is specified, `geo` is ignored
   - If both are empty, defaults to `geo: US`

2. **Keyword match types are prefix-based**
   - You only need to specify "broad" for the first N keywords
   - All remaining keywords automatically become "exact"

3. **Gender options**
   - `male` (default)
   - `female`
   - `all` (targets both)

4. **OS Version Targeting**
   - `ios_version`: Target minimum iOS version
     - Format: `>VERSION` (e.g., `>18.4` means "Newer than 18.4")
     - Without `>`: Just version number is treated as "Newer than" (e.g., `18.4` = `>18.4`)
     - Leave empty for all versions
   - `android_version`: Target minimum Android version
     - Format: `>VERSION` (e.g., `>11.0` means "Newer than 11.0")
     - Without `>`: Just version number is treated as "Newer than" (e.g., `11.0` = `>11.0`)
     - Leave empty for all versions
   - Examples:
     ```csv
     ios_version,android_version
     >18.4,>11.0        # iOS newer than 18.4, Android newer than 11.0
     18.4,11.0          # Same as above (> is implied)
     ,>11.0             # All iOS versions, Android newer than 11.0
     ,,                 # All versions (no constraints)
     ```

5. **Campaign naming**
   - Uses format: `{group}-{geo}-{variant}`
   - Example: `Milfs-CA-Desktop`
   - If targeting multiple geos in one campaign: `Milfs-Desktop`

5. **CSV file paths**
   - Relative to `data/input/Campaign_Creation/` directory
   - Example: `ads.csv` → `data/input/Campaign_Creation/ads.csv`

