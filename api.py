"""Splitwise and YNAB API clients."""

import requests
from typing import Dict, Any
import logging

logger = logging.getLogger('splitwise_ynab_sync')


class APIError(Exception):
    """Raised when an API call fails."""
    pass


class SplitwiseAPI:
    """Handles Splitwise API interactions."""

    def __init__(self, api_key: str):
        self.base_url = 'https://secure.splitwise.com/api/v3.0'
        self.headers = {'Authorization': f'Bearer {api_key}'}

    def get_current_user_id(self) -> int:
        """Get the current user's Splitwise ID."""
        try:
            response = requests.get(f'{self.base_url}/get_current_user', headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()['user']['id']
        except requests.RequestException as e:
            raise APIError(f"Failed to get Splitwise user ID: {e}")

    def get_recent_expenses(self, cutoff_date) -> Dict[str, Any]:
        """Get all expenses dated after cutoff_date."""
        formatted_date = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        logger.debug(f"Fetching Splitwise expenses after: {formatted_date}")

        try:
            response = requests.get(
                f'{self.base_url}/get_expenses',
                headers=self.headers,
                params={'dated_after': formatted_date, 'limit': '0'},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            expenses = data.get('expenses', [])
            logger.debug(f"Retrieved {len(expenses)} expenses from Splitwise")

            if expenses:
                dates = [e['date'][:10] for e in expenses]
                logger.debug(f"Date range: {min(dates)} to {max(dates)}")

            return data
        except requests.RequestException as e:
            raise APIError(f"Failed to get Splitwise expenses: {e}")


class YNABAPI:
    """Handles YNAB API interactions."""

    def __init__(self, token: str):
        self.base_url = 'https://api.youneedabudget.com/v1'
        self.headers = {'Authorization': f'Bearer {token}'}

    def get_budget_id(self, budget_name: str) -> str:
        """Get budget ID by name, or 'last-used' as a passthrough."""
        if budget_name == 'last-used':
            return 'last-used'
        try:
            response = requests.get(f'{self.base_url}/budgets/', headers=self.headers, timeout=30)
            response.raise_for_status()
            for budget in response.json()['data']['budgets']:
                if budget['name'] == budget_name:
                    return budget['id']
            raise APIError(f"Budget '{budget_name}' not found in YNAB")
        except requests.RequestException as e:
            raise APIError(f"Failed to get YNAB budgets: {e}")

    def get_account_id(self, budget_id: str, account_name: str) -> str:
        """Get account ID by name within a budget."""
        try:
            response = requests.get(f'{self.base_url}/budgets/{budget_id}/accounts', headers=self.headers, timeout=30)
            response.raise_for_status()
            for account in response.json()['data']['accounts']:
                if account['name'] == account_name:
                    return account['id']
            raise APIError(f"Account '{account_name}' not found in YNAB")
        except requests.RequestException as e:
            raise APIError(f"Failed to get YNAB accounts: {e}")

    def get_category_id(self, budget_id: str, category_name: str) -> str:
        """Get category ID by name within a budget."""
        try:
            response = requests.get(f'{self.base_url}/budgets/{budget_id}/categories', headers=self.headers, timeout=30)
            response.raise_for_status()
            for group in response.json()['data']['category_groups']:
                for category in group['categories']:
                    if category['name'] == category_name:
                        return category['id']
            raise APIError(f"Category '{category_name}' not found in YNAB")
        except requests.RequestException as e:
            raise APIError(f"Failed to get YNAB categories: {e}")

    def get_all_account_transactions(self, budget_id: str, account_id: str) -> list:
        """Get all transactions for an account (used for duplicate detection)."""
        try:
            response = requests.get(
                f'{self.base_url}/budgets/{budget_id}/accounts/{account_id}/transactions',
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            transactions = response.json()['data']['transactions']

            with_ids = sum(1 for tx in transactions if tx.get('import_id'))
            logger.debug(f"Retrieved {len(transactions)} YNAB transactions ({with_ids} with import_ids)")

            return transactions
        except requests.RequestException as e:
            raise APIError(f"Failed to get YNAB transactions: {e}")

    def create_transactions(self, budget_id: str, transactions: list) -> dict:
        """Create transactions in YNAB. Returns created count and duplicate IDs."""
        if not transactions:
            return {"created": 0, "duplicates": []}

        try:
            logger.debug(f"Sending {len(transactions)} transactions to YNAB")
            response = requests.post(
                f'{self.base_url}/budgets/{budget_id}/transactions',
                headers=self.headers,
                json={"transactions": transactions},
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"YNAB returned {response.status_code}: {response.text}")

            response.raise_for_status()
            data = response.json()['data']

            return {
                "created": len(data.get('transaction_ids', [])),
                "duplicates": data.get('duplicate_import_ids', [])
            }
        except requests.RequestException as e:
            error_details = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = f" — YNAB error: {e.response.text}"
                except Exception:
                    error_details = f" — HTTP {e.response.status_code}"
            raise APIError(f"Failed to create YNAB transactions: {e}{error_details}")
