import pandas as pd
from datetime import datetime
from statistics import median
import argparse
from closeio_api import Client
import os

# -------------------------------------------------
# CONFIGURATION
# -------------------------------------------------

# The API key is read from an environment variable for security.
# This prevents sensitive credentials from being stored in code
# or accidentally pushed to GitHub.
API_KEY = os.getenv("CLOSE_API_KEY")

# Default headers for HTTP requests (again mostly informational since
# the Close SDK handles this internally).
HEADERS = {
    "Content-Type": "application/json"
}

# Create the Close API client which will be used for all API calls
api = Client(API_KEY)


# -------------------------------------------------
# CUSTOM FIELD SETUP
# -------------------------------------------------

def ensure_custom_fields():
    """
    Ensure the required custom fields exist in Close CRM.

    Close stores extra company information in *custom fields*.
    Our script requires two of them:

    1. Company Founded
    2. Company Revenue

    This function attempts to create them. If they already exist,
    Close will throw an error, which we safely ignore.

    This allows the script to run in a fresh Close account without
    requiring manual setup beforehand.
    """

    fields = [
        {"name": "Company Founded", "type": "date"},
        {"name": "Company Revenue", "type": "number"}
    ]

    for field in fields:
        try:
            api.post('custom_field/lead', data=field)
        except Exception:
            # If the field already exists, Close returns an error.
            # We ignore it because that simply means the field
            # is already available.
            pass


# -------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------

def parse_revenue(value: str) -> None | float:
    """
    Convert the revenue value from the CSV file into a number.

    In the CSV file, revenue may appear in different formats:

    Examples:
        "$1,200,000"
        "450000"

    This function cleans the value so Python can treat it as a
    numerical value. If the value is missing or invalid, None
    is returned instead.
    """

    # Handle pandas NaN values (missing values in the CSV)
    if pd.isna(value):
        return None

    # If pandas already interpreted the value as a number
    if isinstance(value, (int, float)):
        return float(value)

    # Remove currency symbols and commas
    value = str(value).replace("$", "").replace(",", "").strip()

    if not value:
        return None

    return float(value)


def valid_row(row):
    """
    Check whether a row in the CSV file contains valid data.

    The assignment requires that invalid rows be discarded.

    A row is considered invalid if any of the required fields
    are missing or empty.

    Required fields:
    - Company
    - Contact Name
    - Contact Emails
    - Company Founded
    - Company Revenue
    - Company US State
    """

    required_fields = [
        "Company",
        "Contact Name",
        "Contact Emails",
        "custom.Company Founded",
        "custom.Company Revenue",
        "Company US State"
    ]

    for field in required_fields:
        value = row.get(field)

        # If the value is missing or blank, reject the row
        if pd.isna(value) or value == "":
            return False

    return True


# -------------------------------------------------
# IMPORT DATA INTO CLOSE
# -------------------------------------------------

def import_contacts(csv_file):
    """
    Import companies and contacts from the CSV file into Close.

    Each row in the CSV represents a **contact**.

    Multiple contacts may belong to the same company.

    In Close CRM:
        Company = Lead
        Person = Contact

    Therefore this function:

    1. Groups contacts by company
    2. Creates a Lead for each company
    3. Attaches all contacts belonging to that company
    """

    # Load the CSV file into a pandas DataFrame
    df = pd.read_csv(csv_file)

    # Remove invalid rows
    df = df[df.apply(lambda row: valid_row(row), axis=1)]

    # Group contacts by company
    grouped = df.groupby("Company")

    for company, group in grouped:

        # Log progress so users know the script is running
        print(f"\nProcessing company: {company} | Contacts: {len(group)}")

        first = group.iloc[0]

        revenue = parse_revenue(first["custom.Company Revenue"])

        founded = first["custom.Company Founded"]
        if pd.isna(founded):
            founded = None

        state = first["Company US State"]
        if pd.isna(state):
            state = None

        # Data used to create a Lead in Close
        lead_payload = {
            "name": company,
            "addresses": [
                {
                    "state": state,
                    "country": "US"
                }
            ],
            "custom": {
                "Company Founded": founded,
                "Company Revenue": revenue
            }
        }

        # Create the Lead in Close
        try:
            response = api.post('lead', data=lead_payload)
            lead_id = response["id"]
        except Exception as e:
            print("Lead creation failed:", company, "|", e)
            continue

        # Create contacts belonging to the company
        for idx, row in group.iterrows():

            print(f"  Processing contact row {idx} | Contact: {row.get('Contact Name')}")

            contact_payload = {
                "lead_id": lead_id,
                "name": row["Contact Name"],
                "emails": [{"email": row["Contact Emails"]}],
                "phones": [] if pd.isna(row["Contact Phones"]) else [{"phone": row["Contact Phones"]}]
            }

            try:
                api.post('contact', data=contact_payload)
            except Exception as e:
                print("Contact creation failed:", row.get("Contact Name"), "|", e)


# -------------------------------------------------
# FETCH LEADS BY DATE RANGE
# -------------------------------------------------

def get_leads_by_date(start_date, end_date):
    """
    Retrieve leads founded within the specified date range.

    After importing the data, we query Close CRM to retrieve
    all leads. We then filter them based on their founding date.

    Only companies whose founding date falls between the
    provided start and end dates are returned.
    """

    leads = []

    response = api.get('lead')
    data = response.get("data", [])

    for lead in data:

        custom = lead.get("custom", {})

        founded = custom.get("Company Founded")
        revenue = custom.get("Company Revenue")

        if not founded or not revenue:
            continue

        founded_date = datetime.strptime(founded, "%Y-%m-%d")

        if start_date <= founded_date <= end_date:

            state = None

            if lead.get("addresses"):
                state = lead["addresses"][0].get("state")

            leads.append({
                "name": lead["name"],
                "state": state,
                "revenue": revenue
            })

    return leads


# -------------------------------------------------
# SEGMENT BY STATE
# -------------------------------------------------

def generate_statistics(leads):
    """
    Analyze leads and compute statistics grouped by US state.

    For each state we calculate:

    - Total number of leads
    - Lead with the highest revenue
    - Total revenue
    - Median revenue
    """

    df = pd.DataFrame(leads)

    # If no leads exist, return an empty result
    if df.empty:
        return []

    for col in ["name", "state", "revenue"]:
        if col not in df.columns:
            df[col] = None

    result = []

    grouped = df.groupby("state")

    for state, group in grouped:

        total_leads = len(group)

        revenues = list(group["revenue"])

        total_revenue = sum(revenues)

        median_revenue = median(revenues)

        top_lead = group.loc[group["revenue"].idxmax()]["name"]

        result.append({
            "US State": state,
            "Total number of leads": total_leads,
            "Lead with highest revenue": top_lead,
            "Total revenue": f"{total_revenue:.2f}",
            "Median revenue": median_revenue
        })

    return result


# -------------------------------------------------
# EXPORT CSV
# -------------------------------------------------

def export_csv(data, filename):
    """
    Save the generated statistics to a CSV file.

    This file becomes the final output of the assignment.
    """

    df = pd.DataFrame(data)

    df.to_csv(filename, index=False)


# -------------------------------------------------
# MAIN SCRIPT
# -------------------------------------------------

def main():
    """
    Main entry point of the script.

    This function orchestrates the entire workflow:

    1. Parse command line arguments
    2. Ensure custom fields exist
    3. Import contacts and companies
    4. Fetch leads within the date range
    5. Generate statistics
    6. Export results to CSV
    """

    parser = argparse.ArgumentParser()

    parser.add_argument("--csv", required=True)
    parser.add_argument("--start")
    parser.add_argument("--end")

    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    ensure_custom_fields()

    print("Importing contacts to Close...")
    import_contacts(args.csv)

    print("Fetching leads in date range...")
    leads = get_leads_by_date(start_date, end_date)

    print("Generating statistics...")
    stats = generate_statistics(leads)

    print("Exporting CSV...")
    export_csv(stats, "output/output.csv")

    print("Done!")


if __name__ == "__main__":
    main()