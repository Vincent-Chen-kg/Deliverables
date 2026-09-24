import asyncio
import datetime
import json
from pyparsing import Path
from aws_deliverable_1 import charges_by_linked_account
from aws_deliverable_2 import screenshots, add_image
from datetime  import datetime,timedelta
from ensure_requirements import ensure_requirements

cum_start_date = "2026-06-13"

def get_previous_month_parameters(date):
    first_day_this_month = date.replace(day=1)
    last_day_prev_month = first_day_this_month - timedelta(days=1)
    first_day_prev_month = last_day_prev_month.replace(day=1)

    #days in YYYY-MM-DD format
    start_date = first_day_prev_month.strftime('%Y-%m-%d')
    end_date = first_day_this_month.strftime('%Y-%m-%d')

    written_end_date = last_day_prev_month.strftime('%Y-%m-%d')
    return {
        "start_date":start_date, 
        "end_date": end_date,
        "written_end_date": written_end_date,
        "month" : datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y %B"),
        "month_year": datetime.strptime(start_date, "%Y-%m-%d").strftime("%B %Y"),
        "title": f"{last_day_prev_month.strftime('%Y_%B')}_AWS_Cost_Report.docx"
    }


def get_exceptions_from_json(json_path: str = "exceptions.json") -> list:
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            return data.get("exceptions", [])
    except FileNotFoundError:
        print(f"Warning: {json_path} not found. No exceptions will be applied.")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {json_path}: {e}")
        return []
    
async def generate_cost_comparison_report(query) -> None:
    await screenshots.capture_dashboard_screenshot(**query)
    await add_image.main(query["deli_dir"], query["month_year"])

async def generate_deliverables(path: str=".", date: str | None = None) -> None:

    today = datetime.now()
    query = get_previous_month_parameters(today)

    SCRIPT_DIR = Path(__file__).resolve().parent
    TEMPLATE_DIR =  SCRIPT_DIR / "templates"

    deli_dir = SCRIPT_DIR / "deliverables" / query["month"]
    deli_dir.mkdir(parents=True, exist_ok=True)

    query["cum_start_date"] = cum_start_date
    query["exceptions"] = get_exceptions_from_json("exceptions.json")

    # print(json.dumps(query, indent=4))

    query["deli_dir"] = deli_dir
    query["template_dir"] = TEMPLATE_DIR
    await charges_by_linked_account.generate_styled_aws_cost_docx(**query)
    await generate_cost_comparison_report(query)

    print(f"runtime: {datetime.now() - today} seconds")

if __name__ == "__main__":

    ensure_requirements("requirements.txt")
    print("All dependencies are ready!")

    asyncio.run(generate_deliverables())