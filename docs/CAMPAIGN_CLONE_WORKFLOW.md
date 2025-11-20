# Campaign Clone Workflow - Native Template

**Date Recorded:** November 19, 2025  
**Purpose:** Document the process of cloning a Native campaign template to create new campaigns  
**Use Case:** Creating multiple Native keyword campaigns from a template

---

## Overview

This workflow captures the step-by-step process of cloning a Native campaign template in TrafficJunky. This is faster than creating campaigns from scratch because it preserves all settings, targeting, and configuration.

---

## Step 1: Navigate to Campaigns Page

**URL:** `https://advertiser.trafficjunky.com/campaigns`

**Screenshot:** `01_campaigns_page.png`

**What you see:**
- Campaigns list/table
- Campaign groups/tabs (General, Ocean, Hentai, AI, etc.)
- Filter options
- Action buttons (+ New Campaign, Export, etc.)

---

## Step 2: Locate the Template Campaign

**Template Campaign Details:**
- **Campaign ID:** `1013076141`
- **Campaign Name:** `TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTER-Keywords_DESK_M_JB`
- **Status:** NOT RUNNING
- **Ad Format:** Display (Native)
- **Dimension:** 640 x 360
- **Content Rating:** NSFW (Not Safe for Work)
- **Device:** Desktop (DESK)

**Screenshot:** `02_searching_for_template_campaign.png`

**How to find it:**
- The template campaigns are visible in the campaigns list
- Look for campaigns starting with "TEMPLATE_EN_NATIVE..." or "TEMPLATE_EN_PREROLL..."
- For Native campaigns, use the one with "NATIVE" in the name (not "PREROLL")

---

## Step 3: Select the Template Campaign

**Action:** Click the checkbox next to the template campaign

**Element Details:**
- **Checkbox selector:** `input[type="checkbox"][value="1013076141"]`
- **Element class:** `tableCheckbox mt-1`
- **Located:** In the first column of the campaign row

**Screenshot:** `03_template_campaign_selected.png`

**What happens:**
- The checkbox becomes checked
- The campaign row gets highlighted with an orange border
- Action buttons at the top become active/enabled (previously disabled)

**Buttons that become active:**
- Play/Pause button
- Edit button  
- Clone button (copy icon) ← **This is what we need!**
- Move to group button
- Archive button
- Delete button

---

## Step 4: Click the Clone Button

**Action:** Click the Clone button to duplicate the campaign

**Element Details:**
- **Icon:** `<i class="fal fa-copy"></i>` (copy icon)
- **Button type:** Icon button in the action toolbar
- **Location:** In the row of buttons above the campaigns table
- **Visual:** Copy/duplicate icon (two overlapping squares)

**What happens:**
- Immediately navigates to campaign settings page
- Creates a new campaign with a new ID
- ALL settings from template are copied

---

## Step 5: Cloned Campaign - Basic Settings Page

**New Campaign Created:**
- **Campaign ID:** `1013076151` (NEW - automatically assigned)
- **URL:** `https://advertiser.trafficjunky.com/campaign/1013076151`
- **Page Title:** `(clone) TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTER-Keywords_DESK_M_JB`

**Screenshot:** `04_cloned_campaign_basic_settings.png`

**Page Structure - 5 Steps Navigation:**
1. ✓ **BASIC SETTINGS** (currently here)
2. **AUDIENCE** - Audience Targeting, More Audience Targeting, Advanced Targeting
3. **TRACKING, SOURCES & RULES** - Conversion Tracker, Source Selection, Rules
4. **SCHEDULE & BUDGET** - Schedule, Budget
5. **AD(S)** - Ad Specs, Ad Creation, Ad Rotation

### Fields on Basic Settings Page:

#### Campaign Name (Required field marked with *)
- **Current value:** `(clone) TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTER-Keywords_DESK_M_JB`
- **Type:** Text input
- **Note:** Has "(clone)" prefix - needs to be changed

#### Content Rating (Required field marked with *)
- **Options:** NSFW / SFW
- **Current:** NSFW (checked)
- **Copied from template:** ✓

#### Group
- **Current:** Templates
- **Type:** Dropdown/combobox with option to create new group
- **Copied from template:** ✓

#### Labels
- **Current:** Native
- **Type:** Multi-select (up to 6 labels)
- **Copied from template:** ✓

#### Device (Required field marked with *)
- **Current:** Desktop (checked)
- **Options:** All / Desktop / Mobile
- **Copied from template:** ✓
- **Important:** This is the field that changes for iOS/Android clones

#### Ad Format
- **Current:** Display (checked)
- **Options:** Display / In-Stream Video
- **Copied from template:** ✓

#### Format Type
- **Current:** Native (checked)
- **Options:** Banner / Native
- **Copied from template:** ✓

#### Ad Type
- **Current:** Rollover (checked)
- **Copied from template:** ✓

#### Ad Dimensions
- **Current:** 640 X 360 (checked)
- **Options:** Multiple dimension options
- **Copied from template:** ✓

#### Content Category
- **Current:** Straight (checked)
- **Options:** Straight / Gay / Trans
- **Copied from template:** ✓

#### Demographic Targeting - Gender
- **Current:** Male (checked)
- **Options:** All / Male / Female
- **Copied from template:** ✓

### Campaign Summary (Top of page)
Shows key settings:
- Status: not running
- Exchange: TJX
- Device(s): Desktop icon
- Format: Display (Native)
- Ad Type: Rollover
- Dimensions: 640 x 360
- Content Category: Straight
- Audience: (icons showing targeting)
- Targeting: GEO, FRQ, KEY, LANG
- Ad Rotation: Autopilot (CTR)

### Action Buttons:
- **Save & Continue** - Saves and moves to next step
- **Save Changes** - Saves current settings
- **Back to Campaign Overview** - Returns to campaign overview

---

## Notes

### Why Clone Instead of Create New?

1. **Faster:** All settings are already configured
2. **Consistent:** Ensures all campaigns have the same base configuration
3. **Less Error-Prone:** No need to manually configure each setting
4. **Preserves Complex Settings:** Targeting, sources, rules, etc. are all copied

### Template Naming Convention

The template uses a naming pattern that indicates:
- `TEMPLATE` - Identifies it as a template (not a live campaign)
- `EN` - Language (English)
- `NATIVE` - Ad format type
- `CPA` - Bid type
- `ALL` - Source/network
- `KEY-ENTER-Keywords` - Keyword targeting (placeholder for actual keywords)
- `DESK` - Device (Desktop)
- `M` - Gender targeting (Male)
- `JB` - Initials/team identifier

### Device Variants

Typically you'll need to create 3 variants:
1. **DESK** (Desktop) - Created first, cannot be cloned from
2. **iOS** - Cloned from Desktop
3. **AND** (Android) - Cloned from Desktop

The Desktop version must be created first because iOS and Android versions are clones that adjust the device targeting.

---

## Next Steps

After clicking Clone, we will document:
1. The clone dialog/form that appears
2. What fields need to be changed (campaign name, device targeting, etc.)
3. How to save/create the cloned campaign
4. How to extract the new campaign ID

---

## Step 6: Update Campaign Name

**Action:** Change the campaign name from template format to actual campaign name

**Field:** Campaign Name (required field marked with *)

**Original value:** `(clone) TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTER-Keywords_DESK_M_JB`  
**New value:** `US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB`

**Screenshot:** `05_campaign_name_updated.png`

### Naming Convention Explained

**Format:** `Geo_Language_ADFormat_BidType_Source_Operating-Systems_Advanced-Targeting_Gender_LaunchedBy`

**Components in this example:**
- **Geo:** `US` (United States)
- **Language:** `EN` (English)
- **ADFormat:** `NATIVE` (Native ad format)
- **BidType:** `CPA` (Cost Per Action)
- **Source:** `ALL` (All sources/networks)
- **Advanced-Targeting:** `KEY-Milfs` (Keyword targeting for "Milfs")
- **Device:** `DESK` (Desktop)
- **Gender:** `M` (Male)
- **LaunchedBy:** `JB` (Initials)

### Other Naming Convention Examples:

**Example 1 - Homepage targeting:**
```
US_EN_NATIVE_CPM_PH_HOMEPAGE_ALL-MOB_iOS_ALL_TJ
```
- Geo: US
- Language: EN
- Format: NATIVE
- Bid: CPM
- Source: PH (Pornhub)
- Targeting: HOMEPAGE
- Device: ALL-MOB then iOS specific
- Gender: ALL
- By: TJ

**Example 2 - Segment targeting:**
```
US_EN_NATIVE_CPM_PH_ALL-MOB_HENTAI_SEGMENT_ALL_TJ
```
- Similar structure but with HENTAI_SEGMENT targeting

**Example 3 - Canada, all devices:**
```
CA_EN_NATIVE_CPM_PH_HOMEPAGE_ALL-MOB_ALL_TJ
```

### Why This Naming Matters

1. **Instantly Identifiable:** Know exactly what the campaign targets without opening it
2. **Sortable:** Campaigns group naturally by geo, format, keyword, etc.
3. **Scalable:** Easy to create 100+ campaigns following same pattern
4. **Consistent:** Everyone on team follows same format

---

## Step 6: Set Campaign Group

**Purpose:** Organize campaigns into groups for easier management (like folders on a computer).

### Actions Taken:

1. **Clicked on the Group dropdown** (was showing "Templates")
   - **Element:** `.select2-selection` (dropdown container showing "×Milfs")
   - **Screenshot:** `06_searching_for_milfs_group.png`

2. **Searched for "Milfs" group** in the dropdown
   - **Search Field:** `searchbox` (active)
   - **Result:** "Milfs" group was found and selected

### Group Creation Process (if needed)

**Note:** In this workflow, "Milfs" already existed. But if creating a new group:

1. **Open Group Dropdown:**
   - Click on the dropdown showing current group (e.g., "Templates")
   - Type the group name to search (e.g., "Milfs")

2. **If "No results found" appears:**
   - Element: `<li role="alert" aria-live="assertive" class="select2-results__option select2-results__message">No results found</li>`
   - **Click:** "Create a New Group" link
     - Element: `<a href="javascript:;" class="btn-link" id="showNewGroupFormButton" data-toggle-target="create_new_group">Create a New Group</a>`
   
3. **Enter New Group Name:**
   - **Input Field:** `<input type="text" class="form-control form-control-sm" name="new_group_name" id="new_group_name" maxlength="64">`
   - Type the group name (e.g., "Milfs")
   
4. **Create the Group:**
   - **Click:** "Create" button
     - Element: `<button type="button" id="confirmNewGroupButton" class="smallButton greenButton width80">Create</button>`
   
5. **Auto-tagging:**
   - The new group automatically gets tagged to the campaign

### Available Groups (as seen in dropdown):
- Ocean
- Hentai
- AI
- Bin
- Shorties
- Tests
- Marvel
- Archive
- Missionary
- TransV2
- Furry
- Blowjob
- Cowgirl
- Erotica Interest
- VR Intent
- VOD Hentai Intent
- Trans
- Header Retargetting
- FinDom
- Threesome
- Global
- Indian
- Big Tits
- Blonde
- Broad
- Cumshot
- Handjob
- Gay
- JB-Testing
- Remarketing
- Templates
- **Milfs** (selected)

#### Key Technical Details
- **Group Dropdown:** `.select2-selection` with combobox role
- **Selected Group Display:** `combobox "×Milfs"` with `[selected]` state
- **Create New Group Link:** `#showNewGroupFormButton`
- **New Group Input:** `#new_group_name` (maxlength: 64 chars)
- **Confirm Button:** `#confirmNewGroupButton`
- **"No results" message:** `<li role="alert" aria-live="assertive" class="select2-results__option select2-results__message">No results found</li>`

---

## Step 7: Set Demographic Targeting (Gender)

**Purpose:** Configure the gender demographic for the campaign. This should match what will be set in the CSV ads.

### Actions Taken:

1. **Verified Gender Setting**
   - **Label:** `<label class="col-2 col-form-label col-form-label-sm text-right fieldLabel">Gender</label>`
   - **Current Selection:** Male (already set correctly)
   - **No change needed** - Template was already set to Male, which matches this campaign's target

### Gender Options Available:

#### Option 1: All
```html
<label class="btn btn-secondary">
    <input type="radio" name="demographic_targeting_id" id="demographic_all" value="1" autocomplete="off">
    All
</label>
```
- **Value:** `1`
- **ID:** `demographic_all`

#### Option 2: Male (Currently Selected)
```html
<label class="btn btn-secondary active">
    <input type="radio" name="demographic_targeting_id" id="demographic_male" value="2" autocomplete="off" checked="">
    Male
</label>
```
- **Value:** `2`
- **ID:** `demographic_male`
- **State:** Active/Checked

#### Option 3: Female
```html
<label class="btn btn-secondary">
    <input type="radio" name="demographic_targeting_id" id="demographic_female" value="3" autocomplete="off">
    Female
</label>
```
- **Value:** `3`
- **ID:** `demographic_female`

### Important Notes:

- The gender setting should **match what will be in your CSV ads**
- In this case: Campaign targets **Male**, so using Male demographic targeting
- The label with class `active` indicates the currently selected option
- The `checked=""` attribute also indicates the current selection

#### Key Technical Details
- **Field Label:** `.fieldLabel` with text "Gender"
- **Radio Button Group Name:** `demographic_targeting_id`
- **Radio Button IDs:**
  - All: `#demographic_all` (value: 1)
  - Male: `#demographic_male` (value: 2)
  - Female: `#demographic_female` (value: 3)
- **Active State:** Class `active` added to label when selected

---

## Step 8: Save Basic Settings & Continue to Audience

**Purpose:** Save the Basic Settings configuration and proceed to the Audience targeting step.

### Actions Taken:

1. **Clicked "Save & Continue" button**
   - **Element:** `<button type="button" id="addCampaign" class="smallButton greenButton mr-3">Save & Continue</button>`
   - **Screenshot:** `07_after_save_continue_step1.png`

### Result:

- **Success Message:** "Campaign US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB saved successfully"
- **Navigation:** Automatically moved to Step 2: AUDIENCE
- **URL Changed:** From `/campaign/1013076151` to `/campaign/1013076151/audience`
- **Page Title Updated:** Now displays the new campaign name

### Current Page State:

Now on **STEP 2. TARGET YOUR AUDIENCE** with three main sections:

1. **Audience Targeting**
   - Geo Targeting (United States already selected from template)
   - OS Targeting (OFF)
   - Browser Targeting (OFF)
   - Browser Language Targeting (ON - English selected)

2. **More Audience Targeting**
   - Various additional targeting options

3. **Advanced Targeting**
   - Keyword Targeting (ON - 22 keywords already selected from template)
   - Audience Exclusion/Pixel Targeting (OFF)
   - Retargeting (OFF)
   - Segment Targeting (OFF)

#### Key Technical Details
- **Save Button ID:** `#addCampaign`
- **Button Classes:** `smallButton greenButton mr-3`
- **Success Notification:** Appears as a dismissible banner at the bottom of the page
- **Step 1 Complete Indicator:** Checkmark (✓) shown next to "1. BASIC SETTINGS" in left navigation

---

## Step 9: Configure Geo Targeting

**Purpose:** Set the geographic locations (countries, regions, or cities) where ads will be displayed.

### Test Case: Changing from USA to Australia & New Zealand

**Note:** This was a test to demonstrate the Geo Targeting workflow. For the actual Milfs campaign, USA would remain as the target based on the naming convention `US_EN_NATIVE_CPA_ALL_KEY-Milfs_DESK_M_JB`.

### Actions Performed:

#### 1. Remove Existing Geo Target (USA)

- **Current Geo:** United States (from template)
- **Element:** `<a href="javascript:;" data-hash="US" data-country="US" class="btn-link removeTargetedLocation" data-geo=" - United States">Remove</a>`
- **Action:** Clicked "Remove" link
- **Result:** Targeted Locations changed from (1) to (0), showing message "You have not added a Geo target yet."
- **Screenshot:** `09_usa_removed.png`

#### 2. Add Australia

**Step 2a: Open Country Dropdown**
- **Dropdown Element:** `<select2-selection__rendered id="select2-geo_country-container" role="textbox">`
- **Clicked on:** Country dropdown (shows "Country" placeholder)

**Step 2b: Search for Australia**
- **Search Box:** `<input class="select2-search__field" type="search"... placeholder="Type here to search">`
- **Typed:** "Australia"
- **Filtered Result:** Shows "Australia" option
- **Screenshot:** `10_australia_search.png`, `11_australia_filtered.png`

**Step 2c: Select Australia from List**
- **Option Element:** `<li class="select2-results__option">Australia</li>`
- **Action:** Clicked on "Australia" option
- **Result:** Dropdown now shows "Australia ×" (with clear button)
- **Screenshot:** `12_australia_selected.png`

**Step 2d: Add Australia to Targeted Locations**
- **Add Button:** `<button type="button" id="addLocation" class="smallButton greenButton width80">Add</button>`
- **Action:** Clicked "Add" button
- **Result:** 
  - Targeted Locations (1)
  - 🇦🇺 - Australia (with "Remove" link)
  - Dropdown resets to "Country" placeholder
- **Screenshot:** `13_australia_added.png`

#### 3. Add New Zealand (Process would be identical)

1. Click Country dropdown
2. Type "New Zealand" in search box
3. Select "New Zealand" from filtered results
4. Click "Add" button
5. Result: Targeted Locations (2) showing both Australia and New Zealand

**Completed Successfully:**
- **Screenshot 14:** `14_new_zealand_search.png` - Search filtered to show "New Zealand"
- **Screenshot 15:** `15_new_zealand_selected.png` - New Zealand selected in dropdown (showing "New Zealand ×")
- **Screenshot 16:** `16_both_countries_added.png` - **Final result showing both countries:**
  - **Targeted Locations ( 2 )**
  - 🇦🇺 - Australia (with Remove link)
  - 🇳🇿 - New Zealand (with Remove link)

### Geo Targeting UI Elements

**Country Dropdown:**
```html
<span class="select2 select2-container select2-container--default" style="width: 170px;">
  <span class="selection">
    <span class="select2-selection select2-selection--single" role="combobox">
      <span class="select2-selection__rendered" id="select2-geo_country-container" 
            role="textbox" aria-readonly="true">
        <!-- When empty: -->
        <span class="select2-selection__placeholder">Country</span>
        
        <!-- When selected: -->
        <span class="select2-selection__clear" title="Remove all items">×</span>Australia
      </span>
      <span class="select2-selection__arrow"><b></b></span>
    </span>
  </span>
  <span class="dropdown-wrapper" aria-hidden="true"></span>
</span>
```

**Search Box (inside dropdown):**
```html
<span class="select2-search select2-search--dropdown">
  <input class="select2-search__field" type="search" tabindex="-1" 
         autocomplete="off" autocorrect="off" autocapitalize="none" 
         spellcheck="false" role="searchbox" aria-autocomplete="list" 
         placeholder="Type here to search">
</span>
```

**Country Options List:**
```html
<ul class="select2-results__options" role="listbox">
  <li class="select2-results__option" role="option">Afghanistan</li>
  <li class="select2-results__option" role="option">Albania</li>
  <!-- ... -->
  <li class="select2-results__option" role="option">Australia</li>
  <li class="select2-results__option" role="option">Austria</li>
  <!-- ... -->
</ul>
```

**Add Button:**
```html
<button type="button" id="addLocation" class="smallButton greenButton width80">Add</button>
```

**Targeted Locations Table:**
```html
<table>
  <tbody>
    <tr>
      <td>Targeted Locations ( 1 )</td>
      <td><a href="javascript:;" class="btn-link">Remove All</a></td>
    </tr>
  </tbody>
  <tbody>
    <tr>
      <td>[Flag]</td>
      <td></td>
      <td class="geoDisplayText" title="Australia">- Australia</td>
      <td></td>
      <td><a href="javascript:;" data-hash="AU" data-country="AU" 
            class="btn-link removeTargetedLocation" 
            data-geo=" - Australia">Remove</a></td>
    </tr>
  </tbody>
</table>
```

### Additional Geo Targeting Options

**+ Add Region / City Button:**
- Allows targeting specific regions or cities within a country
- Element: `<button id="addRegionCityButton" class="btn btn-sm btn-link">+ Add Region / City</button>`

**Remove All Link:**
- Clears all targeted locations at once
- Element: `<a href="javascript:;" class="btn-link">Remove All</a>`

### Important Notes

1. **Required Field:** At least one geo target must be selected per campaign
2. **Limit:** Up to 30 geos (countries, regions, or cities) can be targeted
3. **Template Inheritance:** Cloned campaigns inherit geo targeting from the template
4. **Match Naming Convention:** Geo targeting should match the campaign name (e.g., US in name = United States targeted)

#### Key Technical Details
- **Country Dropdown:** Uses Select2 jQuery plugin for enhanced dropdown functionality
- **Search:** Real-time filtering as you type
- **Data Attributes:** `data-hash` and `data-country` used for removal tracking
- **Remove Link:** Each targeted location has its own remove link with geo-specific data attributes

---

---

## Step 12: Verify Conversion Tracker

**Page:** STEP 3. TRACK YOUR CAMPAIGN, CHOOSE & OPTIMIZE YOUR SOURCES  
**URL:** `https://advertiser.trafficjunky.com/campaign/1013076151/tracking-spots-rules`

**Purpose:** Verify that the required conversion tracker(s) are added to the campaign from the template.

### Verification:

The Conversion Tracker section shows the following trackers are already added:

1. **Completed Payment**
   - **Element:** `<div class="labelText" title="Completed Payment">Completed&nbsp;Payment</div>`
   - **Remove Option:** `<generic [ref=e293] [cursor=pointer]>` (× button)

2. **Redtrack - Purchase** ✓
   - **Element:** `<div class="labelText" title="Redtrack - Purchase">Redtrack&nbsp;-&nbsp;Purchase</div>`
   - **Remove Option:** `<generic [ref=e296] [cursor=pointer]>` (× button)

**Result:** ✅ **Redtrack - Purchase** is confirmed as present. No action required - template already has the correct tracker configured.

**Screenshots:**
- `30_conversion_tracker_both_trackers_visible.png` - Shows both "Completed Payment" and "Redtrack - Purchase" trackers

### Additional Tracker Options:

- **Dropdown:** `<combobox [ref=e300]>` with placeholder "Select Your Tracker"
- **Create New Link:** `<link "Create New Tracker" [ref=e234]>` (links to `/tools/conversion-trackers#newTracker`)

**Note:** If "Redtrack - Purchase" was NOT present, it would indicate that the template needs to be updated to include this tracker.

---

## Step 13: Configure Bidding Parameters

**Purpose:** Set the Target CPA, Per Source Test Budget, and Max Bid values for the Bidder feature.

**Settings:**

### Automatic Bidding
- **Status:** ON (toggle)
- **Mode:** Bidder (selected)
- **Description:** "With the Bidder Feature, let your bids be automatically optimized based on your target CPA."

### 1. Target CPA ($)

**Purpose:** Enter the dollar amount of your target CPA.

- **Element:** `<input type="text" id="target_cpa" name="target_cpa" class="form-control form-control-sm numberOnly noCommas noNegatives requiredField text-right maxWidth80" value="50.00000">`
- **Default Value:** $50.00000
- **Test Value:** $55
- **CSV Logic:** If value provided in CSV, use that; otherwise leave as $50

**Actions:**
1. Click on the Target CPA input field
2. Select all (Ctrl+A)
3. Type the new value (e.g., "55")
4. **Screenshot:** `32_target_cpa_changed_to_55.png`

### 2. Per Source Test Budget ($)

**Purpose:** Enter your test budget per source. Recommendation: Test Budget should be at least 4 times your Target CPA.

- **Element:** `<input type="text" id="per_source_test_budget" name="per_source_test_budget" class="form-control form-control-sm numberOnly noCommas noNegatives requiredField text-right maxWidth80 per_source_test_budget_input" value="200.00">`
- **Default Value:** $200.00
- **Test Value:** $100
- **CSV Logic:** If value provided in CSV, use that; otherwise leave as $200
- **Helper Button:** "Set test budget to recommended value (Target CPA x 4)" - appears dynamically

**Actions:**
1. Click on the Per Source Test Budget input field
2. Select all (Ctrl+A)
3. Type the new value (e.g., "100")
4. **Screenshot:** `33_per_source_test_budget_changed_to_100.png`

### 3. Max Bid ($)

**Purpose:** The max bid feature allows you to specify the maximum amount you are willing to bid on any source.

- **Element:** `<input type="text" id="maximum_bid" name="maximum_bid" class="requiredField w-100 form-control form-control-sm numberOnly noCommas noNegatives text-right" value="10.00000">`
- **Default Value:** $10.00000
- **Test Value:** $11
- **CSV Logic:** If value provided in CSV, use that; otherwise leave as $10
- **Info Message:** "If your max bid does not meet a source's minimum bid requirements, that source will automatically be excluded. You can always change your max bid to include more sources."
- **Helper Link:** "Refresh sources list" - appears dynamically

**Actions:**
1. Click on the Max Bid input field
2. Select all (Ctrl+A)
3. Type the new value (e.g., "11")
4. **Screenshot:** `34_max_bid_changed_to_11.png`

---

## Step 14: Include All Sources

**Purpose:** Ensure all available sources are included for the campaign to maximize reach.

### Source Selection Settings:

- **Target Sources:** Manually (button selected)
- **Automatic Bidding:** ON

### Actions Performed:

#### 1. Select All Sources

- **Element:** `<input type="checkbox" class="checkUncheckAll" data-table="sourceSelectionTable" data-gtm-form-interact-field-id="0">`
- **Initial State:** All sources were already selected (13 sources checked)
- **Status Count:** "Show only selected ( 13 )"

#### 2. Click Include Button

- **Element:** 
```html
<button class="smallButton greyButton mr-2 includeBtn" type="button" data-btn-action="include">
    <i class="far fa-plus-circle"></i>
    Include
</button>
```
- **Action:** Clicked the "Include" button to include all selected sources
- **Screenshot Before:** `35_before_clicking_include.png` - Shows sources with "EXCLUDED" status
- **Screenshot After:** `36_after_clicking_include.png` - Shows all sources with "INCLUDED" status

### Results:

**Before Include:**
- Mixed status: Some sources showed "INCLUDED" (green badge), others showed "EXCLUDED" (red badge)
- Each excluded source had an "Include" button
- Example: 
  - Pornhub PC - Native Categories (2501312): INCLUDED
  - Tube8 PC - Native Categories (2500642): EXCLUDED

**After Include:**
- All sources now show "INCLUDED" (green badge)
- All "Include" buttons changed to "Exclude" buttons
- Checkboxes cleared automatically
- "Show only selected" changed from "( 13 )" to "( 0 )"

### Source List Summary:

All 13 sources are now included:
1. Pornhub PC - Native Categories (2501312) - Min CPM: $0.041
2. Tube8 PC - Native Categories (2500642) - Min CPM: $0.014
3. Redtube PC - Search Native (2497592) - Min CPM: $0.014
4. Tube8 PC - Watch Native (2497562) - Min CPM: $0.014
5. Pornhub PC - Watch Native (2412681) - Min CPM: $0.041
6. Pornhub PC - Native Homepage (2501332) - Min CPM: $0.135
7. Redtube PC - Native Categories (2500692) - Min CPM: $0.014
8. YouPorn PC - Native Categories (2500662) - Min CPM: $0.014
9. Tube8 PC - Search Native (2497612) - Min CPM: $0.014
10. YouPorn PC - Search Native (2497602) - Min CPM: $0.014
11. YouPorn PC - Watch Native (2497552) - Min CPM: $0.014
12. Redtube PC - Watch Native (2497522) - Min CPM: $0.014
13. Pornhub PC - Search Native (2402751) - Min CPM: $0.054

**Note:** All sources are positioned "Below the fold" and show both "Min CPM" and "Suggested CPM" values.

---

## Step 15: Save & Continue to Schedule & Budget

**Purpose:** Save the Tracking, Sources & Rules configuration and proceed to the Schedule & Budget step.

### Actions Performed:

**Element:** 
```html
<button type="submit" class="smallButton greenButton confirmtrackingAdSpotsRules saveAndContinue mr-2" data-gtm-index="saveContinueStepThree">
    Save &amp; Continue
</button>
```

**Action:** Clicked "Save & Continue" button

**Screenshots:**
- `37_before_save_continue_step3.png` - Shows the Rules for Source Optimization section before saving
- `38_after_save_continue_step3.png` - Shows Step 4 page after successful save

### Results:

**Navigation:**
- **Previous URL:** `https://advertiser.trafficjunky.com/campaign/1013076151/tracking-spots-rules`
- **New URL:** `https://advertiser.trafficjunky.com/campaign/1013076151/schedule-budget`
- **Page Title:** "STEP 4. SET YOUR CAMPAIGN SCHEDULE & BUDGET"

**Success Confirmation:**
- Green notification toast: "The information was successfully saved."

**Current Page State:**
- **Campaign Status:** RUNNING
- **Step 3. TRACKING, SOURCES & RULES** - Completed (checkmark shown in sidebar)
- **Step 4. SCHEDULE & BUDGET** - Now active

**Default Settings Observed:**

### SCHEDULE Section:
1. **Duration:** OFF
   - Purpose: Define campaign's start and end dates
   
2. **Campaign Schedule:** OFF
   - Purpose: Select days and times of the week campaign will run
   
3. **Frequency Capping:** ON ✓
   - Setting: "2 time(s) to a visitor every 1 day(s)"
   - Purpose: Limit the number of times a visitor can see ads over a designated time interval

### BUDGET Section:
- **Max Daily Budget:** "Unlimited" (selected)
- **Custom Budget Option:** Available but not selected

---

## Step 16: Configure Schedule & Budget Settings

**Purpose:** Update Frequency Capping and Max Daily Budget based on CSV values or defaults.

### Settings to Configure:

### 1. Frequency Capping Times

**Element:** 
```html
<input type="text" placeholder="1 - 99" class="numberOnly noCommaAndDots noNegatives form-control form-control-sm" 
       name="frequency_cap_times" id="frequency_cap_times" value="2" maxlength="2">
```

**Purpose:** Set how many times a visitor can see ads over the designated interval.

- **Default Value:** 2
- **Test Value:** 1
- **CSV Logic:** If value provided in CSV, use that; otherwise leave as 2

**Actions:**
1. Click on the Frequency Capping times input field
2. Select all (Ctrl+A)
3. Type the new value (e.g., "1")
4. **Screenshot:** `39_frequency_capping_changed_to_1.png`

**Result:** Frequency Capping set to "1 time(s) to a visitor every 1 day(s)"

### 2. Max Daily Budget

**Element:**
```html
<input type="text" name="daily_budget" class="requiredField w-100 numberOnly noCommas noNegatives setBudget text-right form-control" 
       id="daily_budget" data-visible="0" value="250">
```

**Purpose:** Set the maximum daily budget for the campaign.

- **Default Value (Template):** $250
- **Test Value:** $275
- **CSV Logic:** If value provided in CSV, use that; otherwise use template default of $250
- **Radio Button State:** "Custom" must be selected (automatically selected when template has a value)

**Actions:**
1. **Note:** The "Custom" radio button is already selected (as the template has a budget set)
2. Click on the Amount ($) input field
3. Select all (Ctrl+A)
4. Type the new value (e.g., "275")
5. **Screenshot:** `40_budget_changed_to_275.png`

**Result:** Max Daily Budget set to $275

### Settings Summary:

**SCHEDULE:**
- **Duration:** OFF (no changes needed)
- **Campaign Schedule:** OFF (no changes needed)
- **Frequency Capping:** ON - **1** time(s) to a visitor every **1** day(s)

**BUDGET:**
- **Max Daily Budget:** Custom - **$275**

---

## Step 17: Save & Continue to Ad Creation

**Purpose:** Save the Schedule & Budget configuration and proceed to the Ad Creation step (final step).

### Actions Performed:

**Element:** 
```html
<button type="submit" class="smallButton greenButton confirmtrackingAdSpotsRules saveAndContinue mr-2" 
        data-gtm-index="saveContinueStepFour">
    Save &amp; Continue
</button>
```

**Action:** Clicked "Save & Continue" button

**Screenshots:**
- `41_before_save_continue_step4.png` - Shows Schedule & Budget settings before saving
- `42_after_save_continue_step4.png` - Shows Step 5 (Ad Creation) page after successful save

### Results:

**Navigation:**
- **Previous URL:** `https://advertiser.trafficjunky.com/campaign/1013076151/schedule-budget`
- **New URL:** `https://advertiser.trafficjunky.com/campaign/1013076151/ad-settings`
- **Page Title:** "STEP 5. CREATE YOUR AD(S)"

**Success Confirmation:**
- Green notification toast: "The information was successfully saved."

**Current Page State:**
- **Campaign Status:** RUNNING
- **Step 4. SCHEDULE & BUDGET** - Completed (checkmark shown in sidebar)
- **Step 5. AD(S)** - Now active (final step)

### Ad Creation Page Elements:

**AD SPECS - DISPLAY:**
- **Ad Creation Method:** 
  - Manual selection (default)
  - **Mass create with CSV** ← Used for automation
  
- **Ad Name Options:**
  - Use Creative Name (default)
  - Enter Ad Name

- **Required Fields:**
  - Target URL (with dynamic tags available: {CampaignID}, {CampaignName}, etc.)
  - Headline (0/87 characters max)
  - Brand Name (0/25 characters max)

- **Creative Selection:**
  - "Use Existing Creatives" button
  - "Upload New Creatives" button

**AD ROTATION:**
- **Method:** Autopilot (selected)
- **Autopilot Method:** CTR (selected) / CPA (alternative)

---

## Step 18: CSV Upload Automation (Handled by native_uploader.py)

**Purpose:** At this point, the manual workflow is complete. The remaining ad creation process is automated via CSV upload using the existing `native_uploader.py` module.

### Automation Process:

The `NativeUploader` class (in `src/native_uploader.py`) handles the following automated steps:

1. **Navigation:** Navigate to campaign ad-settings page (already on this page from Step 17)
2. **Page Setup:** Set ads table page length to 100 for accurate counting
3. **Count Existing Ads:** Get baseline count of ads before upload
4. **Select Mass CSV:** Click "Mass create with CSV" radio button
5. **Upload CSV:** Upload the Native CSV file via file input (`#massAdsCsv`)
6. **Validation:** Check for and handle validation errors (invalid creative IDs)
7. **Create Preview:** Click "Create CSV Preview" button (if present)
8. **Create Ads:** Click "Create ad(s)" button (`button.create-ads-from-csv-button`)
9. **Wait & Reload:** Wait for processing, reload page to get fresh count
10. **Verify Success:** Count new ads and verify upload success

### CSV Upload Flow Reference:

```python
# From src/native_uploader.py
uploader = NativeUploader(dry_run=False, take_screenshots=True)
result = uploader.upload_to_campaign(
    page=page,
    campaign_id=campaign_id,
    csv_path=csv_path,
    screenshot_dir=screenshot_dir,
    skip_navigation=True  # Already on ad-settings page
)
```

### Key Selectors for Automation:

- **Mass CSV Radio:** `text=Mass create with CSV`
- **File Input:** `#massAdsCsv`
- **Validation Error:** `text=At least one issue was detected`
- **Preview Button:** `text=Create CSV Preview`
- **Create Ads Button:** `button.create-ads-from-csv-button`

### Notes:

- The manual workflow (Steps 1-17) prepares the campaign configuration
- The CSV upload automation (Step 18) handles bulk ad creation
- For manual ad creation (non-automated), users would:
  - Enter Target URL, Headline, and Brand Name
  - Select or upload creatives
  - Click "Create Ad(s)" button

---

## Workflow Summary

### Manual Campaign Clone & Configuration (Steps 1-17):

1. ✅ **Clone Template Campaign** - Copy from template (e.g., `1013076141`)
2. ✅ **Update Campaign Name** - Apply naming convention
3. ✅ **Set Campaign Group** - Create or select group (e.g., "Milfs")
4. ✅ **Configure Gender** - Set demographic targeting (Male/Female/All)
5. ✅ **Save Basic Settings** - Continue to Audience
6. ✅ **Configure Geo Targeting** - Set countries (tested: Australia & New Zealand)
7. ✅ **Remove Existing Keywords** - Clear template keywords
8. ✅ **Add New Keywords** - Add campaign-specific keywords (e.g., milfs, milf porn, cougar)
9. ✅ **Set Keyword Match Types** - Change to Broad/Exact as needed
10. ✅ **Save Audience Settings** - Continue to Tracking
11. ✅ **Verify Conversion Tracker** - Confirm "Redtrack - Purchase" is present
12. ✅ **Configure Bidding** - Set Target CPA ($55), Test Budget ($100), Max Bid ($11)
13. ✅ **Include All Sources** - Select and include all 13 sources
14. ✅ **Save Tracking Settings** - Continue to Schedule & Budget
15. ✅ **Configure Frequency Capping** - Set to 1 time per 1 day
16. ✅ **Set Max Daily Budget** - Set to $275 (Custom)
17. ✅ **Save Schedule & Budget** - Continue to Ad Creation
18. ✅ **CSV Upload** - Automated via `native_uploader.py`

### Automation Integration:

The manual workflow (Steps 1-17) is a **one-time setup per campaign** that can be automated using Playwright. Once the campaign reaches Step 5 (Ad Creation), the existing `native_uploader.py` module takes over to handle bulk ad uploads via CSV.

### For Full Automation (Future Development):

To automate the entire campaign creation process:
1. **Create automation script** that replicates Steps 1-17 using Playwright
2. **Integrate with `native_uploader.py`** for Step 18 (already implemented)
3. **Use CSV/YAML config** to specify campaign parameters
4. **Generate campaign combinations** (Desktop/Mobile/iOS variants)
5. **Auto-generate CSVs** with creative IDs and URLs

---

*Campaign Clone Workflow Documentation Complete*

Continue through the remaining campaign setup steps:
1. ✅ **BASIC SETTINGS** (completed)
2. ✅ **AUDIENCE** (completed)
   - ✅ Geo Targeting (documented - tested with Australia & New Zealand)
   - ✅ Advanced Targeting - Keywords (documented - added milfs, milf porn, cougar; changed milfs to Broad)
3. ✅ **TRACKING, SOURCES & RULES** (completed)
   - ✅ Conversion Tracker (verified Redtrack - Purchase is present)
   - ✅ Bidding Parameters (Target CPA: $55, Test Budget: $100, Max Bid: $11)
   - ✅ Source Selection (all 13 sources included)
   - Rules (skipped - no rules added)
4. **SCHEDULE & BUDGET** (current step)
   - Schedule settings (next)
   - Budget settings
5. **AD(S)** - ad specs, ad creation, ad rotation

---

# Part 2: iOS Campaign Clone Workflow

**Campaign Variant:** iOS Device Targeting (Native)  
**New Campaign Name:** `US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB`  
**Template Campaign ID:** `1013076221`  
**Template Campaign Name:** `TEMPLATE_EN_NATIVE_CPA_ALL_KEY-ENTERKEYWORDS_iOS_M_JB`

**Purpose:** Document the process of cloning a Native iOS template campaign. The workflow is similar to Desktop but with iOS-specific device targeting.

---

## iOS Step 1: Search for iOS Native Template

**Action:** Search for iOS Native template campaign using Campaign ID filter

**Campaign ID/Name Filter:**
- **Typed:** `1013076221`
- **Element:** `searchbox "All Campaigns"`
- **Result:** Dropdown shows "TEMPLATE_EN_NATIVE_CPA_ALL_KEY-..."

**Screenshot:** `ios_01_searching_for_native_ios_template.png`

---

# Part 3: Android Campaign Clone Workflow

**Campaign Variant:** Android Device Targeting (Native)  
**New Campaign Name:** `US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB`  
**Source Campaign ID:** `1013076231` (iOS campaign created in Part 2)  
**Source Campaign Name:** `US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB`

**Purpose:** Document the process of cloning a Native Android campaign from an already-configured iOS campaign. This is the most efficient workflow as all settings (keywords, tracking, bids, budgets) are already configured - only the OS Targeting needs to change.

**Key Efficiency Gain:** By cloning from iOS instead of a template, we inherit all configured settings and only need to change ONE thing (iOS → Android), then click through 3 pages to reach Ad Creation.

---

## Android Step 1: Search for iOS Campaign to Clone

**Action:** Search for the iOS campaign we just created using Campaign ID filter.

**Campaign ID/Name Filter:**
- **Typed:** `1013076231`
- **Element:** `searchbox "All Campaigns"` (ref=e129)
- **Result:** Dropdown shows "US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB..."

**Screenshot:** `android_01_searching_for_ios_campaign.png`

---

## Android Step 2: Select and Clone iOS Campaign

**Purpose:** Select the iOS campaign and clone it to create the Android variant.

### Actions Performed:

1. **Applied Filter:** Clicked on the dropdown result for campaign `1013076231`.
   - **Element:** `option` (ref=e9208)
   - **Screenshot:** `android_07_ios_campaign_selected.png`

2. **Clicked "Apply Filters":** Applied the filter to show only the iOS campaign.
   - **Element:** `button "Apply Filters"` (ref=e272)
   - **Screenshot:** `android_08_ios_campaign_filtered.png`

3. **Selected Campaign Checkbox:** Clicked the checkbox next to Campaign ID `1013076231`.
   - **Element:** `checkbox` (ref=e9632)
   - **Screenshot:** `android_10_campaign_selected.png`

4. **Clicked "Clone" Button:** Identified the "Clone" button (4th icon button) and clicked it.
   - **Element:** `button` (ref=e521)
   - **Screenshot:** `android_11_action_toolbar_visible.png`, `android_12_after_clone_click.png`

### Result:

- **Success Message:** "Campaign has been successfully cloned."
- **Navigation:** Redirected to the cloned campaign's **BASIC SETTINGS** page.
- **URL:** `https://advertiser.trafficjunky.com/campaign/1013076271` (new campaign ID)
- **Campaign Name:** `(clone) US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB`
- **Status:** PAUSED
- **Device:** Mobile (inherited from iOS)
- **Group:** "Milfs" (inherited from iOS)
- **All Settings Inherited:** Keywords, tracking, bids, budgets, all copied from iOS campaign.

---

## Android Step 3: Update Campaign Name (Basic Settings)

**Purpose:** Rename the cloned campaign to change "iOS" to "AND" (Android).

### Actions Performed:

1. **Clicked Campaign Name field:** `input field` (ref=e225)
2. **Selected all text:** `Control+a`
3. **Typed new name:** `US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB`
   - **Screenshot:** `android_13_campaign_name_updated.png`

### Result:

- Campaign name updated to Android naming convention.

---

## Android Step 4: Verify Group and Gender (Basic Settings)

**Purpose:** Confirm Group and Gender settings are correct (inherited from iOS).

### Actions Performed:

- **Observed:** Group is already set to **"Milfs"**. No action required.
- **Observed:** Gender is already set to **Male**. No action required.

### Result:

- Group and Gender settings confirmed as correct.

---

## Android Step 5: Save & Continue to Audience (Basic Settings)

**Purpose:** Save Basic Settings and proceed to the Audience configuration.

### Actions Performed:

1. **Clicked "Save & Continue" button:** `button "Save & Continue"` (ref=e303)
   - **Screenshot:** `android_14_after_save_continue_step1.png`

### Result:

- **Success Message:** "Campaign US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB saved successfully"
- **Navigation:** Moved to **Step 2: AUDIENCE** page.
- **URL:** `https://advertiser.trafficjunky.com/campaign/1013076271/audience`
- **Progress Sidebar:** "1. BASIC SETTINGS" now has a checkmark.
- **Inherited Settings Visible:** Geo Targeting shows "United States", OS Targeting shows "iOS" (needs to be changed).

---

## Android Step 6: Change OS Targeting from iOS to Android (Audience)

**Purpose:** This is the KEY STEP - change Operating System from iOS to Android. This is the ONLY setting that needs to be changed when cloning iOS to Android.

### Actions Performed:

1. **Scrolled to OS Targeting section:** `document.querySelector('#section_audienceTargeting')?.scrollIntoView()`
   - **Screenshot:** `android_15_os_targeting_section.png`

2. **Clicked "Remove All" link for Included Operating Systems:** `link "Remove All"` (ref=e276)
   - **Screenshot:** `android_16_ios_removed.png`

3. **Clicked "Operating System" dropdown (Include):** `combobox "Operating System"` (ref=e334)
   - **Screenshot:** `android_17_os_dropdown_opened.png`

4. **Clicked "Android" option:** `option "Android"` (ref=e546)
   - **Screenshot:** `android_18_android_selected.png`

5. **Clicked "Add" button:** `button "Add"` (ref=e260)
   - **Screenshot:** `android_19_android_added_to_included.png`

### Result:

- **Android** successfully added to "Included Operating Systems".
- iOS has been replaced with Android.
- **This is the ONLY difference between iOS and Android campaigns!**

### Important Note:

All other settings are already inherited from iOS and do NOT need to be changed:
- ✅ Geo Targeting: United States
- ✅ Keywords: milfs (Broad), milf porn (Exact), cougar (Exact)
- ✅ Conversion Tracker: Redtrack - Purchase
- ✅ Target CPA: $55
- ✅ Per Source Test Budget: $100
- ✅ Max Bid: $11
- ✅ All Sources: Included
- ✅ Frequency Capping: 2 (or 1 if iOS was updated)
- ✅ Max Daily Budget: $250 (or $275 if iOS was updated)

---

## Android Step 7: Save & Continue to Tracking, Sources & Rules

**Purpose:** Save the Audience targeting configuration (with Android OS) and proceed to the next step.

### Actions Performed:

1. **Clicked "Save & Continue" button:** `button "Save & Continue"` (ref=e525)
   - **Screenshot:** `android_20_after_save_continue_audience.png`

### Result:

- **Success Message:** "Campaign US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB saved successfully"
- **Navigation:** Moved to **Step 3: TRACKING, SOURCES & RULES** page.
- **URL:** `https://advertiser.trafficjunky.com/campaign/1013076271/tracking-spots-rules`
- **Progress Sidebar:** "2. AUDIENCE" now has a checkmark.
- **All tracking, bids, and sources are already configured** (inherited from iOS).

---

## Android Step 8: Save & Continue to Schedule & Budget

**Purpose:** Since all tracking, bids, and sources are inherited, just save and continue.

### Actions Performed:

1. **Verified:** All 13 sources are "INCLUDED" (inherited from iOS).
2. **Clicked "Save & Continue" button:** `button "Save & Continue"` (ref=e696)
   - **Screenshot:** `android_21_schedule_budget_page.png`

### Result:

- **Success Message:** "The information was successfully saved."
- **Navigation:** Moved to **Step 4: SCHEDULE & BUDGET** page.
- **URL:** `https://advertiser.trafficjunky.com/campaign/1013076271/schedule-budget`
- **Progress Sidebar:** "3. TRACKING, SOURCES & RULES" now has a checkmark.
- **Frequency Capping and Max Daily Budget are already set** (inherited from iOS).

---

## Android Step 9: Save & Continue to Ad Creation

**Purpose:** Since Frequency Capping and Max Daily Budget are inherited, just save and continue.

### Actions Performed:

1. **Verified:** Frequency Capping set to 2, Max Daily Budget set to $250 (inherited from iOS source campaign at clone time).
2. **Clicked "Save & Continue" button:** `button "Save & Continue"` (ref=e266)
   - **Screenshot:** `android_22_ad_creation_page.png`

### Result:

- **Success Message:** "The information was successfully saved."
- **Navigation:** Moved to **Step 5: CREATE YOUR AD(S)** page.
- **URL:** `https://advertiser.trafficjunky.com/campaign/1013076271/ad-settings`
- **Progress Sidebar:** "4. SCHEDULE & BUDGET" now has a checkmark.
- **All 5 setup steps complete!**

---

## Android Step 10: Remove Inherited Ads from iOS Campaign

**Purpose:** Since we cloned from iOS, there are existing ads inherited that need to be removed before uploading Android-specific ads.

### Actions Performed:

1. **Set Page Length to 100:** Clicked "Show" dropdown (ref=e428) and selected "100" (ref=e470) to ensure all ads are visible on one page.
   - **Screenshot:** `android_24_page_length_100.png`

2. **Selected All Ads:** Clicked the "select all" checkbox in the table header (ref=e363).
   - **Screenshot:** `android_25_all_ads_selected.png`
   - **Result:** Both the header checkbox and individual ad checkboxes are now checked. The "Delete" button (ref=e358) is now enabled.

3. **Delete All Inherited Ads:** Click the "Delete" button to remove all ads inherited from iOS clone.
   - **Note:** This step prepares the campaign for fresh Android-specific ads with correct naming conventions and URL parameters.

### Result:

- All inherited iOS ads removed from the Android campaign.
- Campaign is now ready for Android-specific CSV upload.

---

## Android Step 11: CSV Upload Automation

**Purpose:** Upload Android-specific ads using `native_uploader.py`.

### Actions Performed:

- The automated CSV upload process (from `native_uploader.py`) takes over at this point.
- Android-specific ads with correct naming conventions and URL parameters are uploaded via CSV.
- The CSV contains ads tailored for Android devices with appropriate creative IDs and campaign-specific URLs.

### Result:

- Android-specific ads successfully uploaded to the campaign.

---

## Android Step 12: Save Campaign

**Purpose:** Save all changes and finalize the Android campaign.

### Actions Performed:

1. **Clicked "Save Campaign" button:** After CSV upload completes, click the "Save Campaign" button (ref=e452) to save all ad changes.
   - **Element:** `link "Save Campaign"` at bottom of Ad Creation page
   - **Alternative:** Can also use "Save Changes" button (ref=e453)

### Result:

- Android campaign fully configured and saved.
- Campaign ready to be activated when needed.
- All ads uploaded with correct Android-specific settings.

---

## Summary: Android Campaign Clone Workflow

### Complete Workflow Steps:

1. **Clone from iOS campaign** (not from template)
2. **Update campaign name** (iOS → AND)
3. **Change OS Targeting** (iOS → Android) - **THE KEY CHANGE**
4. **Save & Continue through 3 pages** (all settings inherited)
5. **Remove inherited iOS ads** (delete all existing ads)
6. **Upload Android-specific ads** (via `native_uploader.py`)
7. **Save Campaign** (finalize all changes)

### Efficiency Highlights:

1. **Clone from iOS (not template):** Massive time savings - all settings inherited.
2. **Change only ONE thing:** OS Targeting (iOS → Android) in Step 6.
3. **Click through 3 more pages:** Just "Save & Continue" - no edits needed.
4. **Quick ad refresh:** Delete inherited ads, upload new ones, save.
5. **Total time:** ~5-7 minutes vs ~20+ minutes from template.

### Key Differences from Desktop/iOS Workflows:

- **Desktop:** Clone from template, configure everything from scratch.
- **iOS:** Clone from template, configure everything, add iOS to OS Targeting.
- **Android:** Clone from iOS, change iOS to Android in OS Targeting, done!

### Campaign Naming Conventions:

- **iOS:** `US_EN_NATIVE_CPA_ALL_KEY-Milfs_iOS_M_JB`
- **Android:** `US_EN_NATIVE_CPA_ALL_KEY-Milfs_AND_M_JB`
- **Both iOS+Android:** `US_EN_NATIVE_CPA_ALL_KEY-Milfs_All_M_JB` (if targeting both mobile OSes)

---

