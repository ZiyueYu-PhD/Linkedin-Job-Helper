# AI-Powered Job Application Automation System

An end-to-end automated pipeline that scrapes, analyzes, and ranks LinkedIn internship opportunities using LLMs (GPT-4o), computer vision, and Google Sheets integration.

---

## One-Line Summary

Built a fully automated job search system using Playwright, GPT-4o, and Google Sheets to identify, evaluate, and track internship opportunities.

---

## Overview

This project automates the entire job search workflow:

- Scrapes LinkedIn job postings (internships, last 24h)
- Extracts structured job data using GPT-4o Vision
- Matches job descriptions against CV using LLM reasoning
- Scores and ranks opportunities
- Deduplicates jobs across platforms
- Stores results in Google Sheets
- Runs automatically on a schedule

---

## System Architecture

```
LinkedIn Scraper (Playwright)
        ↓
Screenshot Capture
        ↓
GPT-4o Vision Extraction
        ↓
Structured Job Data
        ↓
Deduplication Engine
        ↓
LLM Job-CV Matching
        ↓
Scoring + Recommendation
        ↓
Google Sheets Dashboard
        ↓
Scheduler
```

---

## Features

### 1. LinkedIn Scraper
- Pagination support
- Internship-only filtering
- Recent jobs (24h)
- Rate limiting and anti-block strategy

### 2. GPT-4o Vision Extraction
Extracts:
- Company
- Job title
- Location
- Salary
- Job type
- Applicant count

### 3. AI Job Scoring
Multi-factor evaluation:

- Skill match (30%)
- Experience relevance (30%)
- Competition (10%)
- Job difficulty (10%)
- Growth (10%)
- Company environment (10%)

Example output:
```
{
  "apply_score": 7.8,
  "recommendation": "建议投递"
}
```

### 4. Google Sheets Dashboard
- Automatic updates
- Color-coded scores
- AI reasoning logs

### 5. Deduplication System
Supports:
- LinkedIn
- Indeed
- Glassdoor

### 6. Scheduler
Runs automatically:
- 06:00 AM
- 06:00 PM

---

## Tech Stack

- Python
- Playwright
- OpenAI GPT-4o / GPT-4.1-mini
- Google Sheets API
- PyPDF2

---

## Project Structure

```
.
├── linkedin_scraper_website.py
├── linkedin_scraper_detail.py
├── write_into_google_sheet.py
├── deduplicate_sheet.py
├── Job_analysis.py
├── scheduler.py
├── Jobs_linkedin_recent.txt
├── Jobs_linkedin_detail.txt
└── README.md
```

---

## Environment Setup

Create a `.env` file:

```
OPENAI_API_KEY=your_openai_key
GOOGLE_CREDS_PATH=path_to_google_credentials.json
SPREADSHEET_ID=your_google_sheet_id
CV_PATH=your_resume.pdf
```

---

## Usage

Run full pipeline:

```
python scheduler.py
```

Run step-by-step:

```
python linkedin_scraper_website.py
python linkedin_scraper_detail.py
python write_into_google_sheet.py
python deduplicate_sheet.py
python Job_analysis.py
```

---

## Security Notes

Do NOT upload:

```
.env
google_credentials.json
linkedin_profile/
*.pdf
__pycache__/
```

---

## Example Output

| Company | Role | Score | Recommendation |
|--------|------|------|----------------|
| Amazon | Data Scientist Intern | 8.2 | 建议投递 |
| Meta | ML Intern | 6.5 | 可投递 |
| Lockheed Martin | AI Role | 0.0 | 不推荐 |

---

## Highlights

- End-to-end automation pipeline
- LLM-based decision system
- Vision-based data extraction
- Real-time tracking dashboard

---

## Future Work

- Workday / Greenhouse integration
- Auto-apply system
- Resume auto-tailoring
- Notification system

---

## Author

Ziyue Yu  
PhD Student, University of Pittsburgh

---

## License

MIT License
