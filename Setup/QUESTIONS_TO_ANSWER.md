# Questions to Answer Before Implementation 🤔

These questions need to be clarified before we can proceed with building the automation tool.

---

## ❓ Critical Questions

### 1. Creative Upload Workflow ⚠️ **MOST IMPORTANT**

**Question**: Do the Creative IDs in your CSV (like `1032473171`) refer to creatives that are **already uploaded** to TrafficJunky?

- [YES] **Option A**: Yes, creatives are pre-uploaded to TrafficJunky
  - CSV just associates existing creatives with campaigns
  - We only need to automate the CSV upload
  - **This is what we're currently assuming**

- [This will be V2] **Option B**: No, we need to upload creative files first
  - Creative files (videos/images) need to be uploaded
  - TrafficJunky returns Creative IDs
  - Then we build CSV with those IDs
  - Then upload CSV

**Why This Matters**:
- Option A: Tool is simpler, just upload CSVs
- Option B: Tool needs 2 steps (upload files, then upload CSV)

**Please confirm**: Which option describes your workflow?

---

### 2. Google Drive Integration

**Question**: Your creative files are stored in Google Drive. How should we handle this?

- [] **Option A**: Manual download (simplest)
  - You download files to `data/creatives/` before running tool
  - Tool only handles CSV upload
  - **Recommended for MVP**

- [V2 ] **Option B**: Automated download
  - Tool downloads files from Google Drive automatically
  - Requires Google Drive API setup
  - More complex, but fully automated

- [Yes] **Option C**: Not needed
  - Creative files are already in TrafficJunky
  - CSV only references existing Creative IDs

**Current Plan**: We're assuming Option C (creatives already in TJ)

**Please clarify**: Which option is correct?

---

### 3. Campaign Mapping

**Question**: How do CSVs map to campaigns?

- [ ] **Option A**: Same CSV for multiple campaigns
  - One CSV (e.g., Gay.csv)
  - Upload to multiple campaign IDs
  - Same ads in all campaigns

- [Yes - we can have CSV filed which tells you which CSV will go to which campaign id] **Option B**: Different CSV per campaign
  - Gay.csv → Campaign 1013017411
  - Straight.csv → Campaign 1013017412
  - Trans.csv → Campaign 1013017413
  - Need naming convention or config file 

- [ ] **Option C**: CSV contains campaign info
  - CSV has a column with campaign IDs
  - One CSV for all campaigns
  - Tool splits and uploads accordingly

**Please specify**: Which option matches your workflow?

---

### 4. Multiple Campaigns Handling

**Question**: When processing multiple campaigns, what's the expected behavior?

- [ ] Upload same CSV to all campaigns in sequence
- [Y] Different CSV for each campaign (need mapping)
- [ ] Process one campaign at a time manually

**Also**: Do campaigns need to be processed in a specific order?
- [ ] Yes, order matters
- [Y] No, any order is fine

---

### 5. Success Verification

**Question**: How do we know an upload succeeded?

We need to identify the success indicators on the TrafficJunky platform.

**Can you provide**:
- [Y] Screenshot of successful upload page - Showing ads uploaded check on the screen for the 
- [ ] Text of success message (e.g., "Ads created successfully")
- [ ] URL that page navigates to after success

**Also**: What happens on failure?
- [Y] Error message appears - comes back with the error as over time TJ may change it's interface.
- [ ] Page shows validation errors
- [ ] Other indicator

---

### 6. Upload Process Details

**Question**: When you manually use "Mass Create with CSV":

**What happens step-by-step?**
1. Click "Mass Create with CSV"
2. Next to the field * CSV File (500KB) click Upload CSV
3. in pop-up screen select the specified CSV.
4. click Create CSV Preview
5. May get an issue called At least one issue was detected. Review the following and reupload the CSV - means to remove the creative from the CSV that under the Creative ID are marked as red with the issue like "You can only use creatives that match with the campaign content category you selected. The following creatives are not valid: {creative ID}" The issue here is that TJ has incorrectly not made the creative to All. We need a notification of the creative ID's that are not marked as all and then upload the CSV without those creatives.
6. once correct click the create ad(s) button
7. In the Create ads section you will now see the ads uploaded with the correct Ad Name and target URL

**Specifically**:
- [Y] File selector opens → select CSV → auto-uploads?
- [ ] File selector → upload button → confirm button?
- [ ] Drag-and-drop zone?
- [ ] Paste CSV content into text area?

**After upload**:
- [ ] Immediate confirmation
- [ ] Processing time (how long?)
- [Y] Review page before final submit
- [ ] Email confirmation

---

### 7. CSV Validation

**Question**: Does TrafficJunky validate CSV before uploading?

- [Y] Yes, shows validation errors if format is wrong - see above
- [ ] No, uploads anything and processes
- [ ] Preview shown, must confirm before upload

**If validation errors occur**:
- [ ] Page shows specific error messages
- [ ] Upload is rejected
- [ ] Some rows succeed, some fail

---

### 8. Rate Limiting

**Question**: When uploading to multiple campaigns:

- [ ] Need to wait between uploads (how long?)
- [ ] Can upload immediately one after another
- [Y] Unknown

**Have you noticed**:
- [ ] Slowdowns after multiple uploads
- [ ] Temporary blocks or warnings
- [Y] No issues with rapid uploads - lets try uploading fast and if issues then we rate limit.

---

### 9. Session Handling

**Question**: After logging in once:

- [ ] Stay logged in for hours
- [ ] Session expires after __ minutes
- [ ] Need to log in for each campaign
- [Y] Unknown

**Reason**: If sessions last long, we can save cookies and avoid repeated logins.

---

### 10. Error Recovery

**Question**: If an upload fails partway through:

**Preferred behavior**:
- [Y] Skip failed campaign, continue to next and report error at the end 
- [ ] Retry failed campaign (how many times?)
- [ ] Stop entire process and report error
- [ ] Ask user what to do

---

## 📊 CSV Format Clarifications

Looking at your `Gay.csv`, I see:

```csv
Ad Name,Target URL,Creative ID,Custom CTA Text,Custom CTA URL,...
```

### Questions:

**Q1**: Are all columns required or are some optional?
- Required: all required
- Optional: _______________

**Q2**: Can Ad Names be duplicated?
- [Y] Yes, same ad name in multiple rows is fine
- [ ] No, each ad name must be unique

**Q3**: The Creative IDs (1032473171, etc.) - where do these come from?
- [Y] Manually created in TrafficJunky first
- [V2] Extracted from TrafficJunky via API - WE can possibly get it this way
- [ ] Generated by another tool
- [ ] Provided by creative team

---

## 🎯 Feature Priorities

**Which features are most important to you?**

Rank 1-5 (1 = most important):

- [3] ___ Fast upload speed
- [2] ___ Detailed logging
- [4] ___ Error recovery
- [1] ___ Multiple campaign support
- [ ] ___ Google Drive integration
- [ ] ___ Email notifications
- [ ] ___ Scheduling (run at specific times)
- [ ] ___ Web dashboard
- [5] ___ CSV validation before upload

---

## 🔍 UI Exploration Needed

**To build the automation, we need to**:
- See the actual "Mass Create with CSV" interface
- Identify button/element selectors
- Understand the upload flow

**Options**:
1. **You provide screenshots** of each step
2. **You provide login temporarily** so I can explore (we'll change password after)
3. **Screen recording** of you doing manual upload
4. **Detailed written steps** of what you click

**Which option works for you?** - what works best for you?
- [ ] Option 1: I'll provide screenshots
- [ ] Option 2: Temporary login access (will change password after)
- [ ] Option 3: I'll record a video
- [ ] Option 4: Written step-by-step

---

## 📝 Action Items

**Please**:
1. ✅ Read through all questions above
2. ⬜ Check the boxes for your answers
3. ⬜ Add any additional notes/clarifications
4. ⬜ Save this file or reply with answers

**Once answered**, we can:
- Finalize the implementation plan
- Build the tool to match your exact workflow
- Avoid rebuilding due to incorrect assumptions

---

## 💡 Additional Notes

Use this space for any other information, concerns, or questions you have:

```
[Your notes here]








```

---

**Thank you!** Your answers will help us build exactly what you need. 🚀

