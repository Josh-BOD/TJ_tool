# CSV Format Guide for Campaign Creation

## File Format: `campaign_batch.csv`

The CSV format provides a simple, spreadsheet-friendly way to define campaigns for automated creation.

---

## Column Definitions

### Required Columns

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `group` | String | Campaign group name (will be created if doesn't exist) | `Milfs` |
| `keywords` | String | Semicolon-separated list of keywords | `milfs;milf porn;cougar` |
| `keyword_matches` | String | Semicolon-separated match types (must match keyword count) | `broad;exact;exact` |
| `csv_file` | String | Name of CSV file with ad creatives (in data/input/) | `Milfs.csv` |
| `variants` | String | Comma-separated device variants to create | `desktop,ios,android` |
| `enabled` | Boolean | Whether to create this campaign (true/false) | `true` |

### Optional Columns (will use defaults if empty)

| Column | Type | Default | Description | Example |
|--------|------|---------|-------------|---------|
| `geo` | String | `US` | Semicolon-separated country codes | `US` or `AU;NZ` |
| `target_cpa` | Number | `50` | Target cost per acquisition ($) | `55` |
| `per_source_budget` | Number | `200` | Per source test budget ($) | `100` |
| `max_bid` | Number | `10` | Maximum bid amount ($) | `11` |
| `frequency_cap` | Integer | `2` | Times to show ad per day | `1` |
| `max_daily_budget` | Number | `250` | Maximum daily budget ($) | `275` |
| `gender` | String | `male` | Target gender: `male`, `female`, or `all` | `male` |

---

## CSV Conventions

### Separators
- **Semicolon (`;`)** - Separates multiple values within a cell
  - Keywords: `milfs;milf porn;cougar`
  - Geo codes: `AU;NZ;UK`
  - Match types: `broad;exact;exact`
  
- **Comma (`,`)** - Separates variants only
  - Variants: `desktop,ios,android`

### Empty Cells
- Empty cells will use system defaults
- Example: Empty `target_cpa` column uses default value of `50`

### Boolean Values
- `enabled` column: `true` or `false` (case-insensitive)
- `true` = Create this campaign
- `false` = Skip this campaign

### Match Types
- Must have **same number** as keywords
- Valid values: `broad` or `exact`
- Example: 3 keywords = 3 match types

### Variants
- Valid values: `desktop`, `ios`, `android`
- Can specify one, two, or all three
- Examples:
  - Desktop only: `desktop`
  - Desktop + iOS: `desktop,ios`
  - All three: `desktop,ios,android`

---

## Example CSV File

```csv
group,keywords,keyword_matches,geo,csv_file,target_cpa,per_source_budget,max_bid,frequency_cap,max_daily_budget,variants,enabled
Milfs,"milfs;milf porn;cougar","broad;exact;exact",US,Milfs.csv,55,100,11,1,275,"desktop,ios,android",true
Cougars,"cougar;cougars","broad;exact","AU;NZ",Cougars.csv,50,200,10,2,200,"desktop,ios",true
Mature,"mature moms;mom porn","broad;exact",US,MatureMoms.csv,,,,,,"desktop",true
```

**Notes:**
- Row 1: "Milfs" - All custom settings specified
- Row 2: "Cougars" - Custom geo (AU;NZ) and 2 variants only
- Row 3: "Mature" - Uses defaults for CPA, budget, etc. (empty cells)

---

## Campaign Naming Convention

Campaigns are automatically named using this pattern:

```
{geo}_{lang}_{format}_{bid_type}_{source}_KEY-{keyword}_{device}_{gender}_{user}
```

**Examples:**
- `US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB`
- `US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB`
- `US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB`
- `AU_EN_NATIVE_CPA_ALL_KEY-Cougars_DESK_M_JB`

---

## Tips for Creating Your CSV

### Use a Spreadsheet Editor
1. Open Excel, Google Sheets, or similar
2. Create columns with headers from the example
3. Fill in your campaign data
4. Save as CSV format

### Keyword Tips
- Use semicolons (`;`) between keywords
- No spaces after semicolons (unless part of keyword)
- Case doesn't matter (TrafficJunky lowercases)
- Match types count must equal keyword count

### Testing
- Start with `enabled=false` to test without creating
- Use dry-run mode: `--dry-run` flag
- Check for validation errors before running

### Common Mistakes to Avoid
❌ Wrong: `milfs, milf porn` (comma instead of semicolon)  
✅ Right: `milfs;milf porn`

❌ Wrong: 3 keywords but 2 match types  
✅ Right: Same number of keywords and match types

❌ Wrong: `Desk,iOS` (wrong capitalization)  
✅ Right: `desktop,ios` (lowercase)

---

## Validation

The tool will validate your CSV before creating any campaigns:

- ✓ All required columns present
- ✓ Keywords and match types count match
- ✓ Valid variant names (desktop/ios/android)
- ✓ CSV files exist in data/input/
- ✓ Valid geo codes
- ✓ Numeric values are valid numbers
- ✓ No duplicate campaign definitions

---

## Example Scenarios

### Scenario 1: Simple Desktop-Only Campaign
```csv
group,keywords,keyword_matches,geo,csv_file,variants,enabled
TestGroup,test keyword,exact,US,Test.csv,desktop,true
```

### Scenario 2: Multi-Geo Campaign
```csv
group,keywords,keyword_matches,geo,csv_file,variants,enabled
Milfs,"milfs;milf porn","broad;exact","US;CA;UK",Milfs.csv,"desktop,ios,android",true
```

### Scenario 3: Different Settings Per Campaign
```csv
group,keywords,keyword_matches,geo,csv_file,target_cpa,max_daily_budget,variants,enabled
HighValue,"premium content",exact,US,Premium.csv,100,500,desktop,true
LowValue,"free content",exact,US,Free.csv,20,100,desktop,true
```

---

## Converting from YAML to CSV

If you have a YAML file and want CSV instead:

**YAML:**
```yaml
campaigns:
  - name: "Milfs"
    keywords:
      - name: "milfs"
        match_type: "broad"
```

**Equivalent CSV:**
```csv
group,keywords,keyword_matches,csv_file,variants,enabled
Milfs,milfs,broad,Milfs.csv,"desktop,ios,android",true
```

---

## See Also

- `example_campaigns.csv` - Full working example
- `example_campaigns.yaml` - YAML format alternative
- `docs/CAMPAIGN_AUTOMATION_DESIGN.md` - Complete design documentation

