import json
import urllib.parse
import boto3
import requests
from urllib.parse import quote, urlencode
from pathlib import Path
from datetime import datetime,timedelta
import asyncio
from playwright.async_api import async_playwright
import add_image

SCRIPT_DIR = Path(__file__).resolve().parent

ROLE_SESSION_NAME = "PlaywrightConsoleSession"

CE_CONSOLE = "https://us-east-1.console.aws.amazon.com/cost-management/home?region=us-east-1"

CAPTURES = {
    "Cost Comparison Overview.png": lambda page: (
        page.get_by_role("heading", name="Cost comparison overview")
            .locator("xpath=ancestor::*[@data-awsui-analytics][1]")
    ),
    "Charges by Linked Accounts.png": lambda page: page.get_by_role("table"),
    "Cost Comparison Graph.png": lambda page: page.locator('[data-analytics="ce-chart"]'),
}

def get_account_names(account_ids: set) -> dict[str, str]:
    """Fetches AWS account names using AWS Organizations API."""
    org_client = boto3.client('organizations')
    account_names = {}
 
    for acc_id in account_ids:
    
        res = org_client.describe_account(AccountId=acc_id)
        account_names[acc_id] = res['Account']['Name']
 
    return account_names

 

def account_filter(accounts: dict[str, str], operator: str = "EXCLUDES") -> str:
    """accounts: {account_id: account_name}"""
    return json.dumps([{
        "dimension": {"id": "LinkedAccount", "displayValue": "Linked account"},
        "operator": operator,
        "values": [
            {"value": acct_id, "displayValue": f"{name} ({acct_id})"}
            for acct_id, name in accounts.items()
        ],
    }], separators=(",", ":"))


def cost_explorer_url(start_date: str, end_date: str) -> str:
    
    file_path= "exceptions.json"
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            exceptions = json.load(file)["exceptions"]
    except FileNotFoundError:
        print(f"File '{file_path}' does not exist.")
        exceptions = {} 

    ##report can switch between STANDARD and COMPARE
    CE_VIEW = {
    "reportName": "New cost and usage report",
    "reportMode": "COMPARE",
    "historicalRelativeRange": "CUSTOM",
    "timeRangeOption": "Custom",
    "granularity": "Monthly",
    "groupBy": '["LinkedAccount"]',
    "costAggregate": "unBlendedCost",
    "excludeForecasting": "false",
    "filter": account_filter(get_account_names(exceptions)),
}
    params = {**CE_VIEW, "startDate": start_date, "endDate": end_date}
    return f"{CE_CONSOLE}#/cost-explorer?{urlencode(params, quote_via=quote)}"

def get_federated_console_url(start_date, end_date,profile_name="default"):
    session = boto3.Session(profile_name=profile_name)
    sts_client = session.client("sts")

    with open("role.json", "r") as f:
        data = json.load(f)
        arn = data.get("arn")

    # Assume role to get valid federated credentials
    assumed_role = sts_client.assume_role(
        RoleArn=arn,
        RoleSessionName=ROLE_SESSION_NAME
    )
    
    creds = assumed_role["Credentials"]
    session_data = {
        "sessionId": creds["AccessKeyId"],
        "sessionKey": creds["SecretAccessKey"],
        "sessionToken": creds["SessionToken"]
    }

    # Request the federated sign-in token
    params = {
        "Action": "getSigninToken",
        "SessionType": "json",
        "Session": json.dumps(session_data)
    }

    res = requests.get("https://signin.aws.amazon.com/federation", params=params)
    signin_token = res.json()["SigninToken"]

    # Point the Destination parameter straight to the target dashboard URL
    
    return (
        f"https://signin.aws.amazon.com/federation?"
        f"Action=login&"
        f"Destination={urllib.parse.quote(cost_explorer_url(start_date, end_date))}&"
        f"SigninToken={signin_token}"
    )

async def capture_dashboard_screenshot(start_date: str, end_date: str, month: str) -> Path:
    folder = SCRIPT_DIR / Path("deliverables") / month
    folder.mkdir(parents=True, exist_ok=True)

    login_url = get_federated_console_url(start_date, end_date, profile_name="default")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        #try:
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        page = await context.new_page()
        await page.goto(login_url)

        chart = page.locator('[data-testid="ce-cost-chart"]')
        await chart.wait_for(state="visible")
        await chart.locator(".recharts-bar-rectangle").first.wait_for()

        for file_name, build in CAPTURES.items():
            widget = build(page)
            await widget.scroll_into_view_if_needed()
            await widget.screenshot(path=SCRIPT_DIR / folder / file_name)
        #finally:
        await browser.close()

    return folder

def get_previous_month_parameters(date):
    first_day_this_month = date.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)

    #days in YYYY-MM-DD format
    start_date = first_day_prev_month.strftime('%Y-%m-%d')
    query_end_date = first_day_this_month.strftime('%Y-%m-%d')
    return {"start_date":start_date, "end_date": query_end_date, "month" : datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y %B")}


if __name__ == "__main__":

    today = datetime.now().date()
    #print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    query = get_previous_month_parameters(today)
    print(query)
    folder = asyncio.run(capture_dashboard_screenshot(**query))
    print (f"The screenshots were added to {folder}")

    month_year =  datetime.strptime(query["start_date"], "%Y-%m-%d").strftime("%B %Y")

    print(month_year)
    asyncio.run(add_image.main(folder, month_year))
