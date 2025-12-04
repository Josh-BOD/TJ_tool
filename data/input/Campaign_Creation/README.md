# Campaign Creation Input Folder

This folder contains input files for the Campaign Creation tool.

## Files

### Campaign Definition CSVs
Files that define what campaigns to create:
- `example_campaigns.csv` - Example template showing all available columns (references the ad CSVs below)

### Ad CSVs (Creatives)
Files that contain the ads to upload to each campaign:
- `example_native_ads.csv` - Example Native ad format (Video + Thumbnail)
- `example_preroll_ads.csv` - Example Preroll/Instream ad format (Single video)

**Native ads require:** `Ad Name`, `Target URL`, `Video Creative ID`, `Thumbnail Creative ID`, `Headline`, `Brand Name`

**Preroll (Instream) ads require:** `Ad Name`, `Target URL`, `Creative ID`, `Custom CTA Text`, `Custom CTA URL`

## CSV Format for Campaign Definitions

### Required Columns
| Column | Description | Example |
|--------|-------------|---------|
| `group` | Campaign group name | `Milfs` |
| `keywords` | Semicolon-separated list | `milf;milfs;milf porn;cougar` |
| `csv_file` | Path to ad CSV file | `ads.csv` |
| `variants` | Device types | `desktop,ios,android` |
| `enabled` | Enable this row | `TRUE` or `FALSE` |

### Optional Columns
| Column | Description | Default | Example |
|--------|-------------|---------|---------|
| `ad_format` | Ad format type | `NATIVE` | `NATIVE` or `INSTREAM` |
| `keyword_matches` | Match types | All exact | `broad` or `broad;broad` |
| `gender` | Target gender | `male` | `male`, `female`, `all` |
| `geo` | Geos for ONE campaign | `US` | `US;CA;UK` |
| `multi_geo` | SEPARATE campaigns per geo | - | `CA;AUS` |
| `target_cpa` | Target CPA | `50.0` | `50` |
| `per_source_budget` | Per-source test budget | `200.0` | `100` |
| `max_bid` | Maximum bid | `10.0` | `10` |
| `frequency_cap` | Frequency cap | `2` | `1` |
| `max_daily_budget` | Maximum daily budget | `250.0` | `250` |
| `ios_version` | iOS version constraint | All | `>18.4` |
| `android_version` | Android version constraint | All | `>11.0` |
| `t` | Test number suffix | - | `12` → `_T-12` |

## Usage

```bash
# Dry-run (validate and preview)
python create_campaigns_v2.py --input data/input/Campaign_Creation/my_campaigns.csv --dry-run

# Create campaigns
python create_campaigns_v2.py --input data/input/Campaign_Creation/my_campaigns.csv

# With visible browser
python create_campaigns_v2.py --input data/input/Campaign_Creation/my_campaigns.csv --no-headless
```

## Examples

### Native Campaign (default)
```csv
group,keywords,keyword_matches,gender,geo,csv_file,variants,enabled
Milfs,"milf;milfs;cougar",broad,male,US,milf_ads.csv,"desktop,ios,android",TRUE
```

### Preroll/Instream Campaign
```csv
group,keywords,keyword_matches,gender,geo,csv_file,ad_format,variants,enabled
Milfs,"milf;milfs;cougar",broad,male,US,preroll_ads.csv,INSTREAM,"desktop,ios,android",TRUE
```

### Multi-Geo (Separate Campaigns)
```csv
group,keywords,keyword_matches,gender,multi_geo,csv_file,variants,enabled
Milfs,"milf;milfs",broad,male,"US;CA;UK",milf_ads.csv,"desktop,ios,android",TRUE
```
This creates 9 campaigns: US-Desktop, US-iOS, US-Android, CA-Desktop, CA-iOS, etc.

