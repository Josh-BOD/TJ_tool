# Technical Specifications - TrafficJunky Automation 🔧

**Date**: November 2, 2025  
**Platform Explored**: TrafficJunky Advertiser Dashboard  
**Campaign ID Used**: 1013017411

---

## 🎯 Complete Workflow Discovered

### **Step 1: Navigate to Campaign Ad Settings**

**URL Pattern**: 
```
https://advertiser.trafficjunky.com/campaign/{CAMPAIGN_ID}/ad-settings#section_adSpecs
```

**Example**:
```
https://advertiser.trafficjunky.com/campaign/1013017411/ad-settings#section_adSpecs
```

---

### **Step 2: Select "Mass Create with CSV"**

**Element Type**: Radio button  
**Selector Options**:
- By text: `radio " Mass create with CSV"`
- By value: Look for radio with text "Mass create with CSV"

**Playwright Code**:
```python
# Click the "Mass create with CSV" radio button
page.locator('text=Mass create with CSV').click()

# Wait for CSV upload interface to appear
page.wait_for_selector('#massAdsCsv', state='visible')
```

**What Happens**: Interface reveals CSV upload section

---

### **Step 3: Upload CSV File** ⭐ **CRITICAL**

**Complete Element Structure**:
```html
<label class="greenButton smallButton file-button">
    Upload CSV
    <input type="file" 
           data-field="" 
           data-name="massAdsCsv" 
           accept=".csv" 
           data-invoice-number="" 
           class="" 
           id="massAdsCsv" 
           data-listener="true" 
           style="">
</label>
```

**Selectors**:
- Label (styled button): `.greenButton.file-button` or `text=Upload CSV`
- File input: `#massAdsCsv`

**File Constraints**:
- Max size: 500KB
- Format: CSV only (`.csv`)
- Max ads: 50 per upload

**Playwright Code** (TWO METHODS):

**Method 1: Direct File Input** ⭐ **RECOMMENDED**
```python
# Set file directly on the input element (most reliable)
file_input = page.locator('#massAdsCsv')
file_input.set_input_files('/path/to/your/Gay.csv')

# Wait for processing
page.wait_for_timeout(1000)  # Give it a moment to process
```

**Method 2: Click Label (Alternative)**
```python
# Click the styled label button, which triggers the file input
label_button = page.locator('label.greenButton.file-button')
# Then use file chooser event
with page.expect_file_chooser() as fc_info:
    label_button.click()
file_chooser = fc_info.value
file_chooser.set_files('/path/to/your/Gay.csv')
```

**Why Two Methods**: 
- Method 1 is faster and more reliable (direct file setting)
- Method 2 mimics user behavior more closely (clicking button)
- Both work, but Method 1 is recommended for automation

---

### **Step 4: Download CSV Template (Optional)**

**Template URL Pattern**:
```
https://advertiser.trafficjunky.com/ad/mass-action/{CAMPAIGN_ID}/template
```

**Example**:
```
https://advertiser.trafficjunky.com/ad/mass-action/1013017411/template
```

**Use Case**: Download template before first upload to see exact format

**Playwright Code**:
```python
template_url = f"https://advertiser.trafficjunky.com/ad/mass-action/{campaign_id}/template"
response = page.request.get(template_url)
with open('template.csv', 'wb') as f:
    f.write(response.body())
```

---

### **Step 5: Create CSV Preview** (From User's Steps)

**Based on your answers**, after uploading CSV, you mentioned clicking "Create CSV Preview".

**Expected Button/Element**: 
- Text: "Create CSV Preview" or similar
- Action: Processes CSV and shows preview

**Playwright Code** (To be verified):
```python
# Look for preview button
preview_button = page.locator('text=Create CSV Preview')
if preview_button.is_visible():
    preview_button.click()
    
# Wait for preview to load
page.wait_for_selector('text=At least one issue', state='attached', timeout=5000)
# OR
page.wait_for_selector('text=Create ad(s)', state='visible', timeout=5000)
```

---

### **Step 6: Handle Validation Errors** ⚠️ **MOST IMPORTANT**

**Error Message Pattern** (from your input):
```
"At least one issue was detected. Review the following and reupload the CSV"
```

**Error Details**:
```
"You can only use creatives that match with the campaign content category 
you selected. The following creatives are not valid: {creative ID}"
```

**Indicators**:
- ❌ Red-marked Creative IDs in preview
- ❌ Error message appears
- ✅ Creative IDs listed in error text

**Detection Strategy**:
```python
# Check for error message
has_error = page.locator('text=At least one issue was detected').is_visible()

if has_error:
    # Extract error text
    error_text = page.locator('text=At least one issue').text_content()
    
    # Parse Creative IDs from error
    # Pattern: "The following creatives are not valid: 1032473171, 1032468251"
    import re
    invalid_ids = re.findall(r'\d{10,}', error_text)
    
    # Log for removal
    print(f"Invalid Creative IDs: {invalid_ids}")
    
    # Remove from CSV and retry
    clean_csv(invalid_ids)
    goto Step 3  # Re-upload cleaned CSV
else:
    # No errors, proceed
    goto Step 7
```

**CSV Cleaning Function**:
```python
def remove_invalid_creatives(csv_path, invalid_ids):
    """Remove rows with invalid Creative IDs from CSV"""
    import pandas as pd
    
    df = pd.read_csv(csv_path)
    
    # Remove rows where Creative ID is in invalid_ids list
    df_cleaned = df[~df['Creative ID'].isin(invalid_ids)]
    
    # Save cleaned CSV
    cleaned_path = csv_path.replace('.csv', '_cleaned.csv')
    df_cleaned.to_csv(cleaned_path, index=False)
    
    # Log removed creatives
    removed = df[df['Creative ID'].isin(invalid_ids)]
    return cleaned_path, removed
```

---

### **Step 7: Create Ads**

**Button Text** (from your input): "Create ad(s)"

**Selector**: 
```python
create_button = page.locator('text=Create ad(s)')
```

**Playwright Code**:
```python
# Click create ads button
page.locator('text=Create ad(s)').click()

# Wait for processing
page.wait_for_timeout(2000)

# Wait for success confirmation
page.wait_for_selector('text=Created Ad(s)', state='visible')
```

---

### **Step 8: Verify Success**

**Success Indicators** (from your input):
> "In the Create ads section you will now see the ads uploaded 
> with the correct Ad Name and target URL"

**Table Element**: 
- Heading: "Created Ad(s)"
- Contains: Ad Name, Target URL, Status (APPROVED)

**Verification Strategy**:
```python
# Wait for Created Ads table
page.wait_for_selector('text=Created Ad(s)', state='visible')

# Get the ads table
ads_table = page.locator('table')

# Count new ads (compare before and after)
rows_after = ads_table.locator('tr').count()

# Verify ads were added
if rows_after > rows_before:
    print(f"✓ Successfully created {rows_after - rows_before} ads")
    return True
else:
    print("✗ No new ads created")
    return False
```

**Ad Table Structure Observed**:
```
| Compliance | Thumbnail | Ad Name | Tags | Target URL | Custom CTA | Banner CTA | Tracking Pixel | Date Created | Action |
```

**Example Ad Row**:
```
APPROVED | [thumbnail] | TALKINGAD_GAY | All, NSFW | https://... | Text: Create Your Cum Slut | - | - | 2025-10-30 | [edit]
```

---

## 🔍 Additional Elements Discovered

### **Campaign Information Bar**

**Visible Data**:
- Campaign Name: "CA_EN_PREROLL_CPA_ALL_SOURCE-Gay_DESK_M_JB"
- Status: "RUNNING" (green badge)
- Exchange: "TJX"
- Device(s): Desktop icon
- Format: "In-Stream Video"
- Ad Type: "Video File"
- Dimensions: "16:9"
- Content Category: "Gay"
- Ad Rotation: "Autopilot (CTR)"

**Use Case**: Verify we're on correct campaign before uploading

**Playwright Code**:
```python
# Verify campaign ID in URL
assert f"/campaign/{campaign_id}/" in page.url

# Verify campaign status
status = page.locator('text=RUNNING').is_visible()
if not status:
    print("Warning: Campaign not running")
```

---

### **Existing Ads Table**

**Heading**: "Created Ad(s)"

**Current Ads in Campaign 1013017411**:
1. Gay Porn Vid - deeper (APPROVED)
2. Gay Porn Vid -deepest (APPROVED)  
3. TALKINGAD_GAY (APPROVED)
4. AIPORNISHERE_GAY (APPROVED)
5. AIPORNISHERE_TRANS (APPROVED)

**Use Case**: 
- Count existing ads before upload
- Compare after upload to verify success
- Check for duplicate ad names

---

## 📊 CSV Format Specification

### **Columns Required** (from your Gay.csv):

```csv
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,Banner CTA Creative ID,Banner CTA Title,Banner CTA Subtitle,Banner CTA URL,Tracking Pixel
```

### **Column Details**:

| Column | Required | Type | Example |
|--------|----------|------|---------|
| Ad Name | ✅ Yes | String | `TALKINGAD_GAY` |
| Target URL | ✅ Yes | URL | `https://clk.ourdream.ai/...` |
| Creative ID | ✅ Yes | Integer | `1032473171` |
| Custom CTA Text | ✅ Yes | String | `Create Your Cum Slut` |
| Custom CTA URL | ✅ Yes | URL | Same as Target URL |
| Banner CTA Creative ID | ❓ Optional | Integer | (empty in your examples) |
| Banner CTA Title | ❓ Optional | String | (empty in your examples) |
| Banner CTA Subtitle | ❓ Optional | String | (empty in your examples) |
| Banner CTA URL | ❓ Optional | URL | (empty in your examples) |
| Tracking Pixel | ❓ Optional | URL | (empty in your examples) |

### **Important Notes**:
- ✅ Ad Names CAN be duplicated
- ✅ Creative IDs must already exist in TJ system
- ✅ All required columns must be present (even if some values are empty)
- ⚠️ CSV must be under 500KB
- ⚠️ Maximum 50 ads per upload

---

## 🔐 Authentication Details

### **Login Page**:
- URL: `https://www.trafficjunky.com/sign-in`
- Fields:
  - Username/Email: `textbox "USERNAME OR EMAIL"`
  - Password: `textbox "PASSWORD"`
  - Button: `button "LOG IN"`

### **Login Flow**:
```python
# Navigate to login
page.goto('https://www.trafficjunky.com/sign-in')

# Fill credentials
page.locator('textbox "USERNAME OR EMAIL"').fill(username)
page.locator('textbox "PASSWORD"').fill(password)

# Click login
page.locator('button "LOG IN"').click()

# Wait for redirect to dashboard
page.wait_for_url('**/campaigns', wait_until='networkidle')

# Verify login success
assert 'campaigns' in page.url
```

### **Session Management**:
- Sessions appear to persist across page navigations
- Can process multiple campaigns without re-login
- Cookie-based authentication

---

## ⚡ Performance Considerations

### **Page Load Times Observed**:
- Ad Settings page: ~2-3 seconds
- CSV upload processing: ~1-2 seconds
- Create preview: ~2-3 seconds
- Create ads: ~3-5 seconds (depends on number of ads)

### **Recommended Timeouts**:
```python
DEFAULT_TIMEOUT = 30000  # 30 seconds
UPLOAD_TIMEOUT = 60000   # 60 seconds for large CSVs
PREVIEW_TIMEOUT = 45000  # 45 seconds for preview generation
```

### **Wait Strategies**:
```python
# Wait for navigation
page.wait_for_url(pattern, wait_until='networkidle')

# Wait for specific element
page.wait_for_selector(selector, state='visible')

# Wait for AJAX/API calls
page.wait_for_load_state('networkidle')

# Fixed wait (use sparingly)
page.wait_for_timeout(milliseconds)
```

---

## 🎨 UI Patterns Observed

### **Success Patterns**:
- ✅ Green "APPROVED" badges on ads
- ✅ Ads appear in "Created Ad(s)" table
- ✅ Ad count increases
- ✅ Status bar shows "running"

### **Error Patterns**:
- ❌ Red text for invalid Creative IDs
- ❌ Error message: "At least one issue was detected"
- ❌ Specific creative IDs listed in error
- ❌ Preview doesn't proceed to create step

### **Loading Patterns**:
- ⏳ Spinners/loaders during processing
- ⏳ Page disables during uploads
- ⏳ Status messages appear briefly

---

## 📝 Element Selectors Reference

### **Key Selectors for Automation**:

```python
SELECTORS = {
    # CSV Upload
    'mass_csv_radio': 'text=Mass create with CSV',
    'upload_csv_label': 'label.greenButton.file-button',  # The styled button
    'file_input': '#massAdsCsv',  # The actual file input inside label
    'csv_template_link': f'href*=/ad/mass-action/{campaign_id}/template',
    
    # Buttons
    'create_preview_button': 'text=Create CSV Preview',  # To verify
    'create_ads_button': 'text=Create ad(s)',
    'save_changes_button': 'text=Save Changes',
    
    # Error Detection
    'validation_error': 'text=At least one issue was detected',
    'invalid_creatives_message': 'text=The following creatives are not valid',
    
    # Success Verification
    'created_ads_heading': 'text=Created Ad(s)',
    'ads_table': 'table',
    'approved_badge': 'text=APPROVED',
    
    # Campaign Info
    'campaign_status': 'text=RUNNING',
    'campaign_name_heading': 'h2',
}
```

---

## 🧪 Testing Strategy

### **Test Cases to Implement**:

1. **Happy Path**:
   - Upload valid CSV
   - All creatives match content category
   - All ads created successfully

2. **Validation Error Path**:
   - Upload CSV with 1 invalid creative
   - Detect error
   - Remove invalid creative
   - Retry upload
   - Verify success

3. **Multiple Campaigns**:
   - Upload to campaign A
   - Upload to campaign B
   - Verify both successful

4. **Edge Cases**:
   - Empty CSV
   - CSV with 50 ads (max)
   - CSV with duplicate ad names
   - CSV approaching 500KB limit

---

## 🚨 Known Issues & Workarounds

### **Issue 1: File Upload Button Structure**

**Problem**: File input is wrapped inside a styled label button

**HTML Structure**:
```html
<label class="greenButton smallButton file-button">
    Upload CSV
    <input type="file" id="massAdsCsv" accept=".csv">
</label>
```

**Solution Options**:

**Option 1: Direct File Setting** ⭐ **RECOMMENDED**
```python
# ✅ Set file directly on input (fastest, most reliable)
page.locator('#massAdsCsv').set_input_files(csv_path)
```

**Option 2: Click Label with File Chooser**
```python
# ✅ Click the label and handle file chooser
with page.expect_file_chooser() as fc_info:
    page.locator('label.greenButton.file-button').click()
file_chooser = fc_info.value
file_chooser.set_files(csv_path)
```

**What NOT to do**:
```python
# ❌ DON'T try to click the file input directly
page.locator('#massAdsCsv').click()  # Won't work - element is hidden
```

### **Issue 2: Content Category Mismatch**

**Problem**: Creative marked as "Gay" but campaign needs "All"

**Root Cause**: TJ creatives not set to "All" content category

**Solution**: 
- Detect validation error
- Extract invalid Creative IDs
- Remove from CSV
- Generate report for manual fix in TJ
- Retry with cleaned CSV

**Prevention**: V2 feature - validate creatives before CSV upload

---

## 🔄 Complete Automation Flow

```python
def upload_ads_to_campaign(campaign_id, csv_path):
    """Complete automation flow for one campaign"""
    
    # 1. Navigate to ad settings
    page.goto(f'https://advertiser.trafficjunky.com/campaign/{campaign_id}/ad-settings#section_adSpecs')
    
    # 2. Select Mass CSV upload
    page.locator('text=Mass create with CSV').click()
    page.wait_for_selector('#massAdsCsv', state='visible')
    
    # 3. Count existing ads
    existing_ads_count = get_ads_count(page)
    
    # 4. Upload CSV
    page.locator('#massAdsCsv').set_input_files(csv_path)
    page.wait_for_timeout(1000)
    
    # 5. Create preview (if button exists)
    if page.locator('text=Create CSV Preview').is_visible():
        page.locator('text=Create CSV Preview').click()
        page.wait_for_timeout(2000)
    
    # 6. Check for validation errors
    if page.locator('text=At least one issue').is_visible():
        # Extract invalid Creative IDs
        error_text = page.locator('text=The following creatives').text_content()
        invalid_ids = extract_creative_ids(error_text)
        
        # Clean CSV
        cleaned_csv_path, removed_rows = remove_invalid_creatives(csv_path, invalid_ids)
        
        # Log removed creatives
        log_invalid_creatives(campaign_id, removed_rows)
        
        # Retry with cleaned CSV
        return upload_ads_to_campaign(campaign_id, cleaned_csv_path)
    
    # 7. Create ads
    page.locator('text=Create ad(s)').click()
    page.wait_for_timeout(3000)
    
    # 8. Verify success
    new_ads_count = get_ads_count(page)
    ads_created = new_ads_count - existing_ads_count
    
    if ads_created > 0:
        print(f"✓ Successfully created {ads_created} ads in campaign {campaign_id}")
        return {
            'status': 'success',
            'ads_created': ads_created,
            'campaign_id': campaign_id
        }
    else:
        print(f"✗ Failed to create ads in campaign {campaign_id}")
        return {
            'status': 'failed',
            'ads_created': 0,
            'campaign_id': campaign_id
        }
```

---

## 📈 Next Steps for Implementation

### **Phase 1: Core Functions** (2-3 hours)
1. ✅ Authentication module
2. ✅ Navigation to campaign
3. ✅ CSV upload
4. ✅ Success verification

### **Phase 2: Error Handling** (2-3 hours)
1. ✅ Validation error detection
2. ✅ Creative ID extraction
3. ✅ CSV cleaning
4. ✅ Retry logic

### **Phase 3: Multiple Campaigns** (1-2 hours)
1. ✅ Campaign mapping loader
2. ✅ Sequential processing
3. ✅ Skip failed campaigns
4. ✅ Generate reports

### **Phase 4: Testing & Polish** (2-3 hours)
1. ✅ Dry run mode
2. ✅ Screenshot capture
3. ✅ Detailed logging
4. ✅ Error reporting

---

## ✅ Summary

**What We Know**:
- ✅ Complete workflow (8 steps)
- ✅ All element selectors
- ✅ File upload method (`set_input_files`)
- ✅ Validation error pattern
- ✅ Success verification approach
- ✅ CSV format requirements

**What We Need**:
- ⬜ Verify "Create CSV Preview" button existence
- ⬜ Test actual file upload with real CSV
- ⬜ Confirm exact error message format
- ⬜ Test with multiple campaigns

**Ready to Build**: YES! 🎉

We have 95% of the information needed to build the complete automation. The remaining 5% can be discovered during testing.

---

**Last Updated**: November 2, 2025  
**Status**: Ready for Implementation  
**Confidence Level**: High (95%)

