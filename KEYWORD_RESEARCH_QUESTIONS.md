# Keyword Research Tool - Clarification Questions

Before building this tool, I need to understand exactly what you're looking to automate.

---

## Question 1: What workflow do you want to automate?

- [ ] **A) Extract keywords FROM an existing campaign**
  - Pull keywords already configured in a campaign (like from your URL: `campaign/1013085241/audience`)
  - Export them with their volume data to CSV

- [ ] **B) Discover RELATED keywords using a seed keyword**
  - Input a keyword like "stepmom"
  - Search in TJ's keyword dropdown and capture all the suggested keywords with volumes
  - This is like what you're doing manually now with your `Niche-Findom_v2.csv`

- [X] **C) Both workflows**

---

## Question 2: Where does TrafficJunky show keyword volume?

This helps me know what UI elements to scrape:

- [X] **In the keyword search dropdown** - when you type a keyword, suggestions appear with volume numbers
- [ ] **In a table of keywords already added** - the campaign's audience section shows volume for each keyword
- [ ] **In a separate keyword planner tool** - TJ has a dedicated research tool
- [ ] **Not sure** - I can navigate there via browser and you can show me

---

## Question 3: Scale expectations

- How many seed keywords would you typically want to research at once? So we have a total of 50 or more.
- How many results per keyword do you need (top 10? top 50? all available?)? All available

---

## Question 4: Output format

Should the CSV output match your existing `Niche-Findom_v2.csv` format, or would you prefer a simpler research-focused format like:

```csv
keyword,volume,match_type,source_seed_keyword
stepmom,1500000,broad,stepmom
step mom,850000,broad,stepmom
hot stepmom,450000,broad,stepmom
```

**Preferred format:** match the exact format of niche-findom_v2.csv

---

## Your Answers

Please fill in your answers above or summarize here:

```
Q1 (Workflow): 
Q2 (Volume Location): 
Q3 (Scale): 
Q4 (Output Format): 
```

