# All Mobile Feature

## Overview

The "All Mobile" feature allows you to create a single campaign that targets both iOS and Android devices simultaneously, rather than creating two separate mobile campaigns.

## Benefits

1. **Single Campaign Management**: One campaign to manage instead of two (iOS + Android)
2. **Unified Naming**: Uses `MOB_ALL` in the campaign name for clarity
3. **Combined Targeting**: Both iOS and Android OS targeting in the same campaign
4. **Version Constraints**: Supports separate version constraints for iOS and Android

## Usage

### CSV Format

In your campaign definition CSV, use `all mobile` in the `variants` column:

```csv
group,keywords,variants,csv_file,enabled
Milfs,milf;milfs,desktop,all mobile,ads.csv,TRUE
```

### Naming Convention

**Before (separate campaigns):**
- `US_EN_NATIVE_CPA_ALL_KEY-Mom_iOS_M_JB`
- `US_EN_NATIVE_CPA_ALL_KEY-Mom_AND_M_JB`

**After (all mobile):**
- `US_EN_NATIVE_CPA_ALL_KEY-Mom_MOB_ALL_M_JB`

The `MOB_ALL` device indicator clearly shows this campaign targets all mobile devices (iOS + Android).

## Examples

### Example 1: Desktop + All Mobile

```csv
group,keywords,variants,csv_file,enabled
Milfs,milf;milfs,"desktop,all mobile",ads.csv,TRUE
```

This creates:
- 1 Desktop campaign
- 1 Mobile campaign (iOS + Android combined)

### Example 2: All Mobile Only with Version Constraints

```csv
group,keywords,variants,csv_file,ios_version,android_version,enabled
Cougars,cougar;cougars,all mobile,ads.csv,>18.4,>11.0,TRUE
```

This creates:
- 1 Mobile campaign targeting iOS 18.4+ and Android 11.0+

### Example 3: Mixed Variants

You can still use individual mobile variants if needed:

```csv
group,keywords,variants,csv_file,enabled
Mature,mature;milf,"desktop,ios,android",ads.csv,TRUE
```

This creates the traditional setup:
- 1 Desktop campaign
- 1 iOS campaign
- 1 Android campaign (cloned from iOS)

## Technical Details

### Campaign Creation

When `all mobile` is specified:

1. **CSV Parser**: Expands `all mobile` to `["ios", "android"]` internally
2. **Mobile Combined Flag**: Sets `campaign.mobile_combined = True`
3. **iOS Campaign**: Creates iOS campaign with both iOS and Android OS targeting
4. **Android Variant Skipped**: The Android variant is skipped during creation
5. **Naming**: Uses `MOB_ALL` device indicator for the combined campaign

### OS Targeting

The iOS campaign is configured with both OS types:

```python
# iOS and Android both targeted
self._configure_os_targeting(
    ["iOS", "Android"],
    ios_version=campaign.settings.ios_version,
    android_version=campaign.settings.android_version
)
```

### Version Constraints

You can specify different version constraints for each OS:

- `ios_version`: e.g., `>18.4` (iOS 18.4 or newer)
- `android_version`: e.g., `>11.0` (Android 11.0 or newer)

## Validation

The validator automatically:
- Accepts `all mobile` as a valid variant
- Skips duplicate name checking for Android when `mobile_combined` is True
- Generates the correct campaign name with `MOB_ALL` for preview

## File Changes

The following files were updated to support this feature:

1. **src/campaign_automation_v2/csv_parser.py**: Parse `all mobile` variant
2. **src/campaign_automation_v2/models.py**: Add `mobile_combined` flag
3. **src/campaign_templates.py**: Add `mobile_combined` parameter to naming
4. **src/campaign_automation_v2/creator_sync.py**: Handle combined OS targeting
5. **src/campaign_automation_v2/validator.py**: Update validation logic
6. **create_campaigns_v2_sync.py**: Skip Android variant when combined
7. **create_campaigns_v2.py**: Update dry-run display

## Notes

- The `all mobile` variant is **only available in V2** CSV format
- The feature works with both **NATIVE** and **INSTREAM** ad formats
- Ad upload happens once to the combined campaign (no separate Android upload)
- The same ads are used for both iOS and Android traffic

