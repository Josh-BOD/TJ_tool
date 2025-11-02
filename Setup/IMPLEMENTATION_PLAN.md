# Implementation Plan - Based on Your Answers ✅

## Overview

Based on your answers, here's the finalized implementation plan for the TrafficJunky Automation Tool.

---

## 🎯 Confirmed Requirements

### **Workflow**
✅ **Creatives are pre-uploaded** - CSV just associates them with campaigns  
✅ **Different CSV per campaign** - Need mapping configuration  
✅ **Order doesn't matter** - Can process campaigns in any sequence  
✅ **Skip failed, continue** - Report all errors at the end  
✅ **No rate limiting initially** - Try fast, add if needed  

### **Critical Feature: Creative Validation Error Handling**
When uploading CSV, TJ may reject some Creative IDs with error:
```
"You can only use creatives that match with the campaign content category 
you selected. The following creatives are not valid: {creative ID}"
```

**Solution**: 
1. Detect validation error
2. Extract invalid Creative IDs
3. Remove them from CSV
4. Retry upload
5. **Notify user** of removed Creative IDs
6. Log for later fixing in TJ

---

## 📋 Feature Priority (Your Rankings)

1. **Priority 1**: Multiple campaign support ⭐⭐⭐⭐⭐
2. **Priority 2**: Detailed logging ⭐⭐⭐⭐
3. **Priority 3**: Fast upload speed ⭐⭐⭐
4. **Priority 4**: Error recovery ⭐⭐
5. **Priority 5**: CSV validation before upload ⭐

---

## 🔄 Upload Process Flow (7 Steps)

Based on your detailed steps, here's what the automation will do:

### **Step 1: Navigate to Campaign**
- URL: `https://advertiser.trafficjunky.com/campaign/{CAMPAIGN_ID}/ad-settings#section_adSpecs`

### **Step 2: Click "Mass Create with CSV"**
- Locate button/link with text "Mass Create with CSV"
- Click to open upload interface

### **Step 3: Upload CSV File**
- Locate field "* CSV File (500KB)"
- Click "Upload CSV" button next to it
- File selector popup opens

### **Step 4: Select CSV**
- Use Playwright file upload to select CSV
- Confirm selection

### **Step 5: Create CSV Preview**
- Click "Create CSV Preview" button
- Wait for preview to load

### **Step 6: Handle Validation Errors** ⚠️ **CRITICAL**
```python
if "At least one issue was detected" appears:
    # Extract Creative IDs marked in red
    invalid_creative_ids = extract_invalid_creatives()
    
    # Log for user notification
    log_invalid_creatives(campaign_id, invalid_creative_ids)
    
    # Remove invalid creatives from CSV
    cleaned_csv = remove_creatives(csv, invalid_creative_ids)
    
    # Re-upload cleaned CSV
    goto Step 3 with cleaned_csv
else:
    # No errors, proceed
    goto Step 7
```

### **Step 7: Create Ads**
- Click "Create ad(s)" button
- Wait for confirmation

### **Step 8: Verify Success**
- Check "Create ads" section
- Verify ads appear with correct:
  - Ad Name
  - Target URL
- Take screenshot
- Log success

---

## 📁 Campaign-CSV Mapping Configuration

Since you need different CSVs for different campaigns, we'll use a mapping file.

### **Option A: Simple CSV Mapping** (Recommended)

Create `data/input/campaign_mapping.csv`:

```csv
campaign_id,csv_filename,campaign_name
1013017411,Gay.csv,Gay Campaign
1013017412,Straight.csv,Straight Campaign
1013017413,Trans.csv,Trans Campaign
```

### **Option B: JSON Configuration**

Create `config/campaigns.json`:

```json
{
  "campaigns": [
    {
      "id": "1013017411",
      "csv": "Gay.csv",
      "name": "Gay Campaign",
      "enabled": true
    },
    {
      "id": "1013017412",
      "csv": "Straight.csv",
      "name": "Straight Campaign",
      "enabled": true
    }
  ]
}
```

**Which do you prefer?** (CSV is simpler, JSON more flexible)

---

## 🚨 Error Handling Strategy

### **Invalid Creative IDs**
```
Problem: Creative not marked as "All" content category in TJ
Detection: Red text with error message during preview
Action: 
  1. Extract Creative IDs from error message
  2. Remove from CSV
  3. Retry upload
  4. Generate report: "Removed_Creatives_Report_{timestamp}.csv"
  5. User manually fixes in TJ later
```

### **Campaign Processing**
```
Problem: Campaign upload fails
Action:
  1. Log detailed error
  2. Take screenshot
  3. Skip to next campaign
  4. Continue processing
  5. Report all failures at end
```

### **Login Issues**
```
Problem: Authentication fails
Action:
  1. Log error
  2. Take screenshot
  3. Stop process (can't continue without login)
  4. Notify user
```

---

## 📊 Output Reports

The tool will generate:

### **1. Upload Summary Report**
`data/output/upload_summary_{timestamp}.csv`

```csv
campaign_id,campaign_name,csv_file,status,ads_created,ads_failed,duration,timestamp
1013017411,Gay Campaign,Gay.csv,success,12,0,45s,2025-11-02 14:30:22
1013017412,Straight Campaign,Straight.csv,partial,10,2,52s,2025-11-02 14:31:15
```

### **2. Invalid Creatives Report**
`data/output/invalid_creatives_{timestamp}.csv`

```csv
campaign_id,campaign_name,creative_id,ad_name,error_message
1013017411,Gay Campaign,1032473171,TALKINGAD_GAY,Content category mismatch
1013017412,Straight Campaign,1032468251,WALKINGSELFIE,Content category mismatch
```

### **3. Detailed Log**
`logs/upload_log_{timestamp}.txt`

```
2025-11-02 14:30:00 - INFO - Starting upload process
2025-11-02 14:30:05 - INFO - Logged into TrafficJunky successfully
2025-11-02 14:30:10 - INFO - Processing campaign 1013017411 (Gay Campaign)
2025-11-02 14:30:15 - WARNING - Validation error detected
2025-11-02 14:30:16 - INFO - Removing invalid creative IDs: [1032473171]
2025-11-02 14:30:22 - SUCCESS - Campaign 1013017411 completed: 12 ads created
...
```

---

## 🎨 Module Structure

### **New Module: Campaign Manager**
`src/campaign_manager.py`
```python
class CampaignManager:
    """Manages campaign-CSV mappings and batch processing."""
    
    def load_campaign_mapping(self, mapping_file: str) -> List[Campaign]
    def get_next_campaign(self) -> Optional[Campaign]
    def mark_campaign_complete(self, campaign_id: str, status: str)
    def mark_campaign_failed(self, campaign_id: str, error: str)
    def generate_summary_report(self) -> str
```

### **New Module: CSV Processor**
`src/csv_processor.py`
```python
class CSVProcessor:
    """Handles CSV validation and cleaning."""
    
    def validate_csv(self, csv_path: Path) -> ValidationResult
    def remove_creatives(self, csv_path: Path, creative_ids: List[str]) -> Path
    def extract_invalid_creatives(self, error_html: str) -> List[str]
```

### **Enhanced: Uploader Module**
`src/uploader.py`
```python
class TJUploader:
    """Main upload automation logic."""
    
    def upload_to_campaign(self, campaign: Campaign) -> UploadResult
    def handle_validation_errors(self, page) -> List[str]
    def verify_ads_created(self, page) -> bool
    def take_debug_screenshot(self, step: str)
```

---

## 🔍 UI Exploration Approach

**Best approach for you**: **Option 2 - Temporary Login Access**

**Why?**
- I can see the exact UI elements and their selectors
- Test the automation in real-time
- Handle any edge cases
- Takes ~30-60 minutes
- You change password immediately after

**Process**:
1. You provide login credentials temporarily
2. I use browser automation to explore and build
3. Test upload flow with dry run
4. You change password
5. Tool is ready to use

**Alternative**: Screen recording works too, but I might miss technical details needed for selectors.

**What's your preference?**

---

## 📅 Development Timeline

### **Phase 1: Core Automation (MVP)** - 4-6 hours
- [ ] Authentication module
- [ ] Navigation to campaign ad settings
- [ ] CSV upload automation
- [ ] Basic error handling
- [ ] Success verification

### **Phase 2: Advanced Features** - 3-4 hours
- [ ] Campaign mapping configuration
- [ ] Invalid creative detection & removal
- [ ] Multiple campaign processing
- [ ] Detailed logging & reports

### **Phase 3: Polish & Testing** - 2-3 hours
- [ ] Error recovery improvements
- [ ] Report generation
- [ ] Documentation updates
- [ ] Dry run testing
- [ ] Live upload testing

**Total**: 9-13 hours development time

---

## 🚀 Implementation Sequence

### **Week 1: Foundation**
1. ✅ Setup complete (DONE)
2. ⬜ Explore UI (login access or screenshots)
3. ⬜ Build authentication
4. ⬜ Build navigation

### **Week 2: Core Features**
5. ⬜ CSV upload automation
6. ⬜ Validation error detection
7. ⬜ Creative ID removal logic
8. ⬜ Campaign mapping system

### **Week 3: Enhancement & Testing**
9. ⬜ Multiple campaign processing
10. ⬜ Report generation
11. ⬜ Error handling refinement
12. ⬜ Testing & bug fixes

---

## 🎓 V2 Features (Future)

Based on your notes, V2 will include:

1. **Creative File Upload**
   - Upload videos/images to TJ first
   - Get Creative IDs back
   - Auto-generate CSV

2. **Google Drive Integration**
   - Auto-download CSVs from Drive
   - Auto-download creative files

3. **API Creative Extraction**
   - Get existing Creative IDs via API
   - Validate against TJ system

4. **Advanced Features**
   - Scheduling
   - Email notifications
   - Web dashboard

---

## 📋 Configuration Files Needed

### **1. Campaign Mapping**
`data/input/campaign_mapping.csv`
```csv
campaign_id,csv_filename,campaign_name
```

### **2. Updated .env**
Add these new settings:
```env
# Campaign Processing
CAMPAIGN_MAPPING_FILE=./data/input/campaign_mapping.csv
SKIP_FAILED_CAMPAIGNS=True
REMOVE_INVALID_CREATIVES=True

# Reporting
GENERATE_SUMMARY_REPORT=True
GENERATE_INVALID_CREATIVES_REPORT=True
```

---

## ✅ Next Immediate Steps

**For you to do**:
1. ⬜ Review this implementation plan
2. ⬜ Create `data/input/campaign_mapping.csv` with your campaigns
3. ⬜ Choose UI exploration method (login access recommended)
4. ⬜ Confirm if you prefer CSV or JSON for campaign mapping

**For me to do** (once you choose UI exploration):
1. ⬜ Explore TJ interface
2. ⬜ Map element selectors
3. ⬜ Build authentication module
4. ⬜ Build upload automation

---

## 🎯 Success Criteria

The tool is complete when:

✅ Logs in automatically  
✅ Reads campaign mapping file  
✅ Uploads CSV to correct campaign  
✅ Detects validation errors  
✅ Removes invalid Creative IDs  
✅ Retries upload  
✅ Verifies ads created  
✅ Skips failed campaigns  
✅ Processes all campaigns  
✅ Generates reports  
✅ Logs everything  

---

## 🤝 Ready to Start?

**Choose your path**:

**Path A: Give me login access** (30-60 min, most efficient)
- I'll explore, build, and test in one session
- You change password immediately after
- Tool ready to use

**Path B: Provide screen recording**
- Record yourself doing manual upload
- I build based on video
- May need clarifications
- Takes longer but no password sharing

**Which path works better for you?**

---

**Once you decide, we'll move forward immediately!** 🚀

