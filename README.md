# AWS Cost Report Generator

A Python script that queries the AWS Cost Explorer API, aggregates costs by linked account, filters out designated exceptions, maps AWS account IDs to friendly names using AWS Organizations, and generates a styled Microsoft Word (`.docx`) document summarizing monthly and cumulative spend.

---

## Features

- **AWS Cost Explorer Integration**: Aggregates costs using the `NetUnblendedCost` metric to capture actual invoiced costs net of credits, refunds, and discounts.
- **AWS Organizations Lookup**: Maps AWS Account IDs to human-readable Account Names automatically.
- **Account Exception Filtering**: Excludes specified account IDs using a local `exceptions.json` file.
- **Dynamic Date Formatting**: Formats dates with ordinal suffixes in superscript (e.g., June 13<sup>th</sup>, 2026) for custom table headers.
- **Templated Output**: Populates cost data directly into a pre-formatted Word template (`template.docx`).
- **Automated Prior-Month Reporting**: Calculates time ranges relative to the current date to automatically generate reports for the previous calendar month.

---

## Prerequisites

### Python Dependencies

Ensure Python 3.9+ is installed, then install the required dependencies:

```bash
pip install boto3 python-docx
```

### AWS Credentials & IAM Permissions

The script uses standard `boto3` credential resolution (AWS CLI profile, environment variables, or IAM role). 

The AWS identity running the script requires the following IAM permissions:
- `ce:GetCostAndUsage` (Cost Explorer access)
- `organizations:DescribeAccount` (Optional, required to convert Account IDs to Account Names)

### Required Local Files

The following files must exist in the working directory alongside the script:

1. **`template.docx`**: A pre-formatted Word document containing at least two tables. **Table 2** (index `1`) serves as the target cost table.
2. **`exceptions.json`**: *(Optional)* A JSON file listing account IDs to exclude from reporting.

---

## Configuration

### Account Exceptions (`exceptions.json`)

To exclude specific AWS accounts from the report, define their account IDs in `exceptions.json`:

```json
{
  "exceptions": [
    "123456789012",
    "987654321098"
  ]
}
```

*Note: If `exceptions.json` is missing, the script prints a warning and proceeds without excluding any accounts.*

### In-Code Configuration

- **`COST_METRIC`**: Default is `"NetUnblendedCost"`.
- **`cum_start_date`**: Baseline start date for tracking cumulative costs (e.g., `"2026-06-13"`).

---

## Technical Overview

### Functions

| Function | Description |
| :--- | :--- |
| `get_account_names(account_ids)` | Fetches account names from AWS Organizations given a set of account IDs. Defaults to `"Unknown / External"` if inaccessible. |
| `get_date_parts(date_str)` | Extracts the month, day, year, and ordinal suffix (`st`, `nd`, `rd`, `th`) from a date string for styling. |
| `add_header_with_superscript_date(...)` | Formats paragraph text with ordinal day suffixes in superscript font for headers. |
| `generate_styled_aws_cost_docx(...)` | Queries AWS Cost Explorer for cumulative and current period costs, aggregates data, sorts records, and triggers document creation. |
| `build_cost_table(...)` | Writes table headers, totals, and sorted row data into Table 2 (`doc.tables[1]`) of the document template. |
| `get_previous_month_parameters(date)` | Returns the start date, end date, Cost Explorer query boundary, and output file title for the previous calendar month based on the current date. |

---

## Execution & Usage

Run the script directly from your terminal:

```bash
python generate_report.py
```

### Execution Steps
1. The script determines the current date and calculates parameters for the previous full calendar month.
2. Queries AWS Cost Explorer for:
   - **Cumulative spend** from `cum_start_date` through the end of the target month.
   - **Current spend** for the target month.
3. Maps account IDs to account names using AWS Organizations.
4. Filters out any accounts specified in `exceptions.json`.
5. Opens `template.docx`, populates table header dates, inserts overall totals, and adds rows sorted by cumulative cost in descending order.
6. Saves the generated file with a name following the structure: `YYYY_Month_AWS_Cost_Report.docx` (e.g., `2026_May_AWS_Cost_Report.docx`).
```
