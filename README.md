# Close CRM CSV Import & Lead Analysis

## Overview

This project contains a Python script that imports companies and contacts from a CSV file into a **Close CRM** organization using the Close API.

After importing the data, the script analyzes the leads and generates a report summarizing company revenue by **US state** for companies founded within a specified date range.

The script performs three main tasks:

1. Import companies and contacts from a CSV file into Close CRM
2. Identify leads founded within a user‑specified date range
3. Generate a state‑level revenue report and export it to a CSV file

---

# How the Script Works

## 1. Reading the CSV File

The script reads a CSV file where **each row represents a contact**.

Multiple contacts may belong to the same company. Since Close CRM represents companies as **Leads**, the script groups contacts by company name so that:

- **One company → One lead**
- **Multiple contacts → Attached to that lead**

### Example

| Company | Contact Name |
|--------|--------------|
| Company A | John Doe |
| Company A | Jane Smith |

Result in Close:

**Lead:** Company A

Contacts:

- John Doe
- Jane Smith

---

## 2. Eliminating Invalid Data

Before importing any data, the script validates each row in the CSV file.

A row is considered **invalid** if any of the following fields are missing or empty:

- Company
- Contact Name
- Contact Emails
- Company Founded
- Company Revenue
- Company US State

Rows that fail validation are **discarded and not imported**.

This ensures the Close API only receives **clean and valid data**.

---

## 3. Creating Leads and Contacts in Close

For each unique company in the CSV file:

1. A **Lead** is created in Close
2. All contacts associated with that company are attached to the lead

The script uses the official Close Python API client:

```python
from closeio_api import Client
```

This client handles authentication and simplifies communication with the Close API.

---

## 4. Custom Fields

The script requires two custom fields to store company data:

- **Company Founded**
- **Company Revenue**

The script automatically creates these fields if they do not already exist.

This ensures the script works in a **fresh Close account without manual setup**.

---

## 5. Finding Leads Founded in a Date Range

When running the script, the user specifies a start date and end date.

### Example

```bash
python main.py \
--csv data/MOCK_DATA.csv \
--start 2000-01-01 \
--end 2015-12-31
```

The script retrieves leads from Close and selects only those whose **Company Founded** date falls within the specified range.

---

## 6. Segmenting Leads by US State

After filtering leads by founding date, the script groups them by **US state**.

For each state, it calculates:

- Total number of leads
- The lead with the highest revenue
- Total revenue of all leads
- Median revenue of all leads

These calculations are performed using the **pandas** library.

---

## 7. Generating the Output Report

The results are exported to a CSV file:

```
output/output.csv
```

The file contains the following columns:

| US State | Total number of leads | Lead with highest revenue | Total revenue | Median revenue |

### Example Output

| US State | Total Leads | Top Revenue Lead | Total Revenue | Median Revenue |
|---------|-------------|------------------|---------------|---------------|
| California | 28 | Digitube | 68,145,121 | 6,874,512 |

---

# Installation

## 1. Clone the Repository

```bash
git clone https://github.com/marcusashmond/close-crm-import
cd close-crm-import-crm-import
```
---

## 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Required Environment Variable

Set your Close API key as an environment variable:

```bash
export CLOSE_API_KEY="your_api_key_here"
```

---

# Running the Script

Run the script with the following command:

```bash
python main.py \
--csv data/MOCK_DATA.csv \
--start 2000-01-01 \
--end 2015-12-31
```

### Arguments

| Argument | Description |
|---------|-------------|
| `--csv` | Path to the input CSV file |
| `--start` | Start date for filtering companies |
| `--end` | End date for filtering companies |

---

# Output

The script generates:

```
output/output.csv
```

This file contains the **state‑level revenue summary**.

---

# Assumptions

The implementation assumes:

- Each CSV row represents **one contact**
- Company names uniquely identify leads
- Revenue values in the CSV may include **currency symbols and commas**
- Leads store company data using **custom fields**

---

# Possible Improvements

If this script were used in production, several improvements could be added:

- Pagination when retrieving leads from the Close API
- Retry logic for API rate limits
- Structured logging
- Unit tests
- Batch imports for faster performance
- Duplicate lead detection

---

# Technologies Used

- Python
- Close CRM API
- Pandas
- CSV processing

---

# Security Note

Before pushing the project to GitHub, **remove any hardcoded API keys** and use an environment variable instead:

```python
import os

API_KEY = os.getenv("CLOSE_API_KEY")
```

This prevents accidentally exposing sensitive credentials.
