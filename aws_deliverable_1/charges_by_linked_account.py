import asyncio
from pathlib import Path
import aioboto3
from docx import Document

from .aws_cost_fetcher import AWSCostFetcher
from .cost_report_document_builder import CostReportDocumentBuilder


async def generate_styled_aws_cost_docx(
    start_date: str,
    end_date: str,
    cum_start_date: str,
    written_end_date: str,
    title: str,
    deli_dir: Path,
    template_dir: Path,
    exceptions: list[str] | None = None,
    **kwargs
) -> Path:
    """Main pipeline executing async AWS data collection and off-thread document generation."""
    exceptions = exceptions or []
    session = aioboto3.Session()
    fetcher = AWSCostFetcher(session)

    # 1. Asynchronously retrieve cost data
    cum_costs, curr_costs = await fetcher.fetch_cost_and_usage_data(
        start_date, end_date, cum_start_date, exceptions
    )

    all_account_ids = set(cum_costs.keys()) | set(curr_costs.keys())

    # 2. Retrieve Account Names
    account_names = await fetcher.fetch_account_names(all_account_ids)

    # 3. Process data & calculate aggregates
    account_data = [
        {
            'account_id': acc_id,
            'account_name': account_names.get(acc_id, ''),
            'cumulative': cum_costs.get(acc_id, 0.0),
            'current': curr_costs.get(acc_id, 0.0)
        }
        for acc_id in all_account_ids
    ]

    total_cumulative = sum(item['cumulative'] for item in account_data)
    total_current = sum(item['current'] for item in account_data)

    sorted_records = sorted(account_data, key=lambda x: x['cumulative'], reverse=True)

    # 4. Thread-isolated Document Creation
    def render_and_save() -> Path:
        output_path = deli_dir / title
        doc = Document(template_dir / "template1.docx")

        CostReportDocumentBuilder.build_cost_table(
            doc,
            sorted_records,
            total_cumulative,
            total_current,
            cum_start_date,
            start_date,
            written_end_date,
        )
        doc.save(output_path)
        return output_path

    saved_file_path = await asyncio.to_thread(render_and_save)
    print(f"Report successfully saved to {saved_file_path}")
    return saved_file_path