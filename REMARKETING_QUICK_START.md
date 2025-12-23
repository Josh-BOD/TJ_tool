# Remarketing Campaign Creation - Quick Start Guide

## Overview

The campaign creation tool now supports **Remarketing campaigns** in addition to standard keyword-targeting campaigns. Remarketing campaigns use pre-configured audience retargeting templates.

## New CSV Columns

Two new optional columns have been added:

| Column | Values | Default | Description |
|--------|--------|---------|-------------|
| `campaign_type` | `Standard` / `Remarketing` | `Standard` | Standard = keyword targeting, Remarketing = audience retargeting |
| `bid_type` | `CPA` / `CPM` | `CPA` | CPA = Cost Per Action, CPM = Cost Per Mille (impressions) |

## Remarketing Templates

The following templates are used for remarketing campaigns:

| Format | Device | Template ID |
|--------|--------|-------------|
| NATIVE | Desktop | 1013186231 |
| NATIVE | All Mobile | 1013186221 |
| PREROLL (INSTREAM) | Desktop | 1013186211 |
| PREROLL (INSTREAM) | All Mobile | 1013186201 |

## Campaign Naming Convention

Remarketing campaigns use `RMK` instead of `KEY` in the campaign name:

- **Standard:** `US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB`
- **Remarketing:** `US_EN_NATIVE_CPM_ALL_RMK-Milfs_DESK_M_JB`

For All Mobile variants:
- `US_EN_NATIVE_CPM_ALL_RMK-Milfs_MOB_ALL_M_JB`

## Example CSV

### Basic Remarketing (No Keywords, CPM Bidding)

```csv
group,keywords,ad_format,campaign_type,bid_type,variants,csv_file,enabled
Milfs,,NATIVE,Remarketing,CPM,"desktop,all mobile",Native_Ads.csv,TRUE
Latina,,INSTREAM,Remarketing,CPM,"desktop,all mobile",PreRoll_Ads.csv,TRUE
```

### Hybrid Remarketing (Keywords + Audience, CPA Bidding)

```csv
group,keywords,keyword_matches,ad_format,campaign_type,bid_type,variants,csv_file,target_cpa,enabled
Milfs,"milf;milfs",broad,NATIVE,Remarketing,CPA,"desktop,all mobile",Native_Ads.csv,55,TRUE
```

## Variants

| Variant | Description |
|---------|-------------|
| `desktop` | Desktop-only campaign |
| `all mobile` or `all_mobile` | Combined iOS + Android campaign (MOB_ALL) |
| `ios` | iOS-only campaign (cloned from all_mobile, removes Android) |
| `android` | Android-only campaign (cloned from all_mobile, removes iOS) |

## Bidding Types

### CPA (Cost Per Action)
- Uses: Target CPA, Per Source Test Budget, Max Bid
- Same as standard campaigns

### CPM (Cost Per Mille)
- Uses suggested CPM bids from each source
- Typically used for remarketing/retargeting campaigns
- **Note:** CPM workflow implementation in progress

## Usage

Run the campaign creation tool as usual:

```bash
python create_campaigns_v2_sync.py --input data/input/Campaign_Creation/Remarketing_Test.csv
```

## Template File

See `Example_docs/Remarketing_Campaign_Template.csv` for a complete example.

