# Dry-Run Testing Guide

This guide explains how to test the campaign automation tool in dry-run mode before creating actual campaigns.

---

## What is Dry-Run Mode?

Dry-run mode validates your input files and shows you exactly what would be created **without actually creating anything**.

This allows you to:
- ✓ Verify your YAML/CSV syntax is correct
- ✓ Check that all required CSV files exist
- ✓ Preview campaign names and settings
- ✓ Catch errors before running for real
- ✓ Test different configurations safely

---

## Example Files Provided

### YAML Format
**File:** `data/input/example_campaigns.yaml`

Contains 5 example campaigns:
1. **Milfs** - US, all 3 variants (Desktop/iOS/Android), custom settings
2. **Cougars** - AU/NZ, Desktop + iOS only
3. **MatureMoms** - US, Desktop only, lower CPA
4. **Stepmom** - Disabled (enabled: false) - won't be created
5. **Milfs-Canada** - CA, all 3 variants, higher budget

**Features demonstrated:**
- Custom settings per campaign
- Multiple keywords with different match types
- Different geo targeting
- Selective variants
- Disabled campaigns

### CSV Format
**File:** `data/input/example_campaigns.csv`

Same 5 campaigns in CSV format for spreadsheet users.

---

## Running a Dry-Run

### YAML Input
```bash
python create_campaigns.py --input data/input/example_campaigns.yaml --dry-run
```

### CSV Input
```bash
python create_campaigns.py --input data/input/example_campaigns.csv --dry-run
```

---

## Expected Dry-Run Output

```
=================================================================
DRY-RUN MODE - No campaigns will be created
=================================================================

Validating input file: example_campaigns.yaml
✓ File parsed successfully
✓ 5 campaigns defined
✓ 4 campaigns enabled (1 disabled)

-----------------------------------------------------------------
VALIDATION CHECKS
-----------------------------------------------------------------
✓ All required fields present
✓ Keywords and match types count match
✓ All CSV files exist:
  ✓ data/input/Milfs.csv
  ✓ data/input/Cougars.csv
  ✓ data/input/MatureMoms.csv
  ✓ data/input/Milfs-CA.csv
✓ All geo codes valid: US, AU, NZ, CA
✓ All variant names valid
✓ No duplicate campaign definitions

-----------------------------------------------------------------
CAMPAIGNS TO BE CREATED
-----------------------------------------------------------------

Campaign Set 1: Milfs (Group: Milfs)
  Geo: US
  Keywords: milfs (broad), milf porn (exact), cougar (exact)
  CSV: Milfs.csv
  Settings:
    - Target CPA: $55
    - Per Source Budget: $100
    - Max Bid: $11
    - Frequency Cap: 1 time/day
    - Max Daily Budget: $275

  Will create 3 campaigns:
    1. US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB
       └─ Clone from template: 1013076141 (Desktop)
       └─ Upload CSV: Milfs.csv

    2. US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB
       └─ Clone from template: 1013076221 (iOS)
       └─ Upload CSV: Milfs.csv

    3. US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB
       └─ Clone from iOS campaign (created above)
       └─ Upload CSV: Milfs.csv

-----------------------------------------------------------------

Campaign Set 2: Cougars (Group: Cougars)
  Geo: AU, NZ
  Keywords: cougar (broad), cougars (exact), mature women (exact)
  CSV: Cougars.csv
  Settings:
    - Target CPA: $50 (default)
    - Per Source Budget: $200 (default)
    - Max Bid: $10 (default)
    - Frequency Cap: 2 times/day (default)
    - Max Daily Budget: $200

  Will create 2 campaigns:
    1. AU_EN_NATIVE_CPA_ALL_KEY-Cougars_DESK_M_JB
    2. AU_EN_NATIVE_CPA_ALL_KEY-Cougars_iOS_M_JB
  (Note: Android variant not requested)

-----------------------------------------------------------------

Campaign Set 3: MatureMoms (Group: Mature)
  Geo: US
  Keywords: mature moms (broad), mom porn (exact)
  CSV: MatureMoms.csv
  Settings:
    - Target CPA: $45
    - Frequency Cap: 3 times/day

  Will create 1 campaign:
    1. US_EN_NATIVE_CPA_ALL_KEY-MatureMoms_DESK_M_JB
  (Note: Only Desktop variant requested)

-----------------------------------------------------------------

Campaign Set 4: Stepmom (SKIPPED - disabled)
  Reason: enabled=false in configuration

-----------------------------------------------------------------

Campaign Set 5: Milfs-Canada (Group: Milfs)
  Geo: CA
  Keywords: milfs (broad), milf porn (exact)
  CSV: Milfs-CA.csv
  Settings:
    - Target CPA: $60
    - Max Daily Budget: $300

  Will create 3 campaigns:
    1. CA_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB
    2. CA_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB
    3. CA_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB

=================================================================
DRY-RUN SUMMARY
=================================================================
Total campaign sets: 5
  ✓ Enabled: 4
  ⊗ Disabled: 1

Total campaigns that would be created: 9
  - Desktop campaigns: 4
  - iOS campaigns: 4
  - Android campaigns: 2 (cloned from iOS)

Estimated time: ~45 minutes
  (Desktop: ~5min, iOS: ~5min, Android: ~3min per set)

=================================================================
NEXT STEPS
=================================================================
✓ Validation passed - ready to create campaigns!

To create these campaigns for real:
  python create_campaigns.py --input example_campaigns.yaml

To modify the configuration:
  1. Edit: data/input/example_campaigns.yaml
  2. Run dry-run again to verify changes
  3. Run without --dry-run when ready

=================================================================
```

---

## What Gets Validated

### File Validation
- ✓ File exists and is readable
- ✓ Valid YAML/CSV syntax
- ✓ All required columns/fields present
- ✓ No duplicate campaign definitions

### Campaign Validation
- ✓ Campaign names are valid
- ✓ Group names are valid (max 64 chars)
- ✓ At least one keyword specified
- ✓ Keywords and match types count match
- ✓ Match types are "broad" or "exact"
- ✓ At least one variant specified
- ✓ Variant names are valid (desktop/ios/android)

### File References
- ✓ CSV files exist in data/input/
- ✓ CSV files are not empty
- ✓ CSV files have correct format (for Native ads)

### Settings Validation
- ✓ Numeric values are valid numbers
- ✓ Numeric values are positive
- ✓ Geo codes are valid (2-letter ISO codes)
- ✓ Gender is "male", "female", or "all"
- ✓ Frequency cap is between 1-99

---

## Common Validation Errors

### Error: "CSV file not found"
```
✗ CSV file not found: data/input/Milfs.csv
```
**Solution:** Create the CSV file or fix the path in your YAML/CSV

### Error: "Keywords and match types count mismatch"
```
✗ Campaign 'Milfs': 3 keywords but 2 match types
```
**Solution:** Ensure you have one match type per keyword

### Error: "Invalid variant name"
```
✗ Campaign 'Milfs': Invalid variant 'Desk' (valid: desktop, ios, android)
```
**Solution:** Use lowercase variant names: desktop, ios, android

### Error: "Invalid geo code"
```
✗ Campaign 'Milfs': Invalid geo code 'USA' (use 'US')
```
**Solution:** Use 2-letter ISO country codes (US, CA, UK, AU, etc.)

### Error: "Duplicate campaign definition"
```
✗ Duplicate campaign: US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB
  First defined in row 1
  Duplicate found in row 5
```
**Solution:** Each campaign name must be unique. Change keywords or geo to differentiate.

---

## Modifying Example Files

### To Test with Your Own Data

1. **Copy the example file:**
   ```bash
   cp data/input/example_campaigns.yaml data/input/my_campaigns.yaml
   ```

2. **Edit with your campaigns:**
   - Change group names
   - Update keywords
   - Modify settings
   - Point to your CSV files

3. **Run dry-run:**
   ```bash
   python create_campaigns.py --input data/input/my_campaigns.yaml --dry-run
   ```

4. **Fix any errors and repeat**

5. **Run for real when ready:**
   ```bash
   python create_campaigns.py --input data/input/my_campaigns.yaml
   ```

---

## Testing Strategies

### Start Small
Test with 1 campaign set first:
```yaml
campaigns:
  - name: "TestCampaign"
    keywords: [{name: "test", match_type: "exact"}]
    csv_file: "Test.csv"
    variants: ["desktop"]
```

### Gradually Increase
Once 1 campaign works:
1. Add iOS variant
2. Add Android variant
3. Add more keywords
4. Add another campaign set

### Use Disabled Flag
Keep campaigns in your file but skip them:
```yaml
campaigns:
  - name: "NotReadyYet"
    enabled: false  # Won't be created
    # ... rest of config
```

---

## CSV File Requirements

Your CSV ad files (e.g., `Milfs.csv`) must exist and contain:

**Required columns for Native ads:**
- Ad Name
- Target URL
- Video Creative ID
- Thumbnail Creative ID
- Headline
- Brand Name

**Example:** See existing CSV files in `data/input/` directory.

**Note:** The tool will validate CSV file existence but not the CSV content. Use your existing `native_uploader.py` validation logic.

---

## After Successful Dry-Run

Once dry-run passes validation:

```bash
# Run for real (will ask for confirmation)
python create_campaigns.py --input my_campaigns.yaml

# Or skip confirmation (automated/batch mode)
python create_campaigns.py --input my_campaigns.yaml --yes

# Run with screenshots for debugging
python create_campaigns.py --input my_campaigns.yaml --screenshots
```

---

## Troubleshooting

### Dry-run passes but real run fails?

Common causes:
1. **TrafficJunky UI changed** - Element selectors outdated
2. **Not logged in** - Playwright session expired
3. **Rate limiting** - Too many requests too fast
4. **Template campaigns missing** - Template IDs changed or deleted
5. **Geo targeting unavailable** - Country not available in TrafficJunky

Check logs: `logs/campaign_creation_errors.log`

### Want more verbose output?

```bash
python create_campaigns.py --input my_campaigns.yaml --dry-run --verbose
```

---

## Files Needed for Dry-Run

Minimum requirements:
```
TJ_tool/
├── create_campaigns.py           (main script - to be created)
├── data/
│   └── input/
│       ├── example_campaigns.yaml    ✓ (provided)
│       ├── example_campaigns.csv     ✓ (provided)
│       ├── Milfs.csv                 (your ad CSV)
│       ├── Cougars.csv               (your ad CSV)
│       ├── MatureMoms.csv            (your ad CSV)
│       └── Milfs-CA.csv              (your ad CSV)
└── docs/
    ├── CAMPAIGN_AUTOMATION_DESIGN.md ✓ (provided)
    └── CSV_FORMAT_GUIDE.md          ✓ (provided)
```

---

## Ready to Build?

Now that you have:
- ✓ Example YAML file
- ✓ Example CSV file  
- ✓ CSV format guide
- ✓ Design document
- ✓ This testing guide

I can start building the actual tool!

**Next steps:**
1. Build input parsers (YAML & CSV)
2. Build validation logic
3. Build dry-run mode
4. Test with your example files
5. Build real campaign creation

Want me to start building? 🚀

