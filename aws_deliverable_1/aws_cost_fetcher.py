import asyncio
import aioboto3
from botocore.exceptions import ClientError

COST_METRIC = "NetUnblendedCost"


class AWSCostFetcher:
    """Handles asynchronous interaction with AWS Cost Explorer & Organizations APIs."""

    def __init__(self, session: aioboto3.Session):
        self.session = session

    async def fetch_account_names(self, account_ids: set[str]) -> dict[str, str]:
        """Asynchronously fetches AWS account names using AWS Organizations API."""
        account_names: dict[str, str] = {}
        async with self.session.client('organizations') as org_client:
            for acc_id in account_ids:
                try:
                    res = await org_client.describe_account(AccountId=acc_id)
                    account_names[acc_id] = res['Account']['Name']
                except ClientError:
                    account_names[acc_id] = "Unknown / External"
        return account_names

    async def fetch_cost_and_usage_data(
        self,
        start_date: str,
        end_date: str,
        cum_start_date: str,
        exceptions: list[str]
    ) -> tuple[dict[str, float], dict[str, float]]:
        """Queries Cost Explorer for cumulative and current billing metrics concurrently."""
        async with self.session.client('ce') as ce_client:
            task_cum = ce_client.get_cost_and_usage(
                TimePeriod={'Start': cum_start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=[COST_METRIC],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}]
            )
            task_curr = ce_client.get_cost_and_usage(
                TimePeriod={'Start': start_date, 'End': end_date},
                Granularity='MONTHLY',
                Metrics=[COST_METRIC],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'LINKED_ACCOUNT'}]
            )

            res_cum, res_curr = await asyncio.gather(task_cum, task_curr)

        cum_costs = self._extract_account_costs(res_cum, exceptions)
        curr_costs = self._extract_account_costs(res_curr, exceptions)
        return cum_costs, curr_costs

    @staticmethod
    def _extract_account_costs(response: dict, exceptions: list[str]) -> dict[str, float]:
        """Parses Cost Explorer response and accumulates amounts by linked account ID."""
        costs: dict[str, float] = {}
        for result in response.get('ResultsByTime', []):
            for group in result.get('Groups', []):
                acc_id = group['Keys'][0]
                if acc_id not in exceptions:
                    amount = float(group['Metrics'][COST_METRIC]['Amount'])
                    costs[acc_id] = costs.get(acc_id, 0.0) + amount
        return costs