"""API utilities for Splitwise and YNAB integration."""

import json
import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger('splitwise_ynab_sync')


class APIError(Exception):
    """Custom exception for API-related errors."""
    pass


class SplitwiseAPI:
    """Handles Splitwise API interactions."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://secure.splitwise.com/api/v3.0'
        self.headers = {'Authorization': f'Bearer {api_key}'}
    
    def get_current_user_id(self) -> int:
        """Get the current user's Splitwise ID."""
        try:
            response = requests.get(
                f'{self.base_url}/get_current_user',
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()['user']['id']
        except requests.RequestException as e:
            raise APIError(f"Failed to get Splitwise user ID: {e}")
    
    def get_recent_expenses(self, cutoff_date) -> Dict[str, Any]:
        """Get expenses dated after the given cutoff date."""
        import logging
        logger = logging.getLogger('splitwise_ynab_sync')
        
        # Format date for Splitwise API (ISO format)
        formatted_date = cutoff_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        logger.debug(f"Fetching Splitwise expenses dated after: {formatted_date}")
        
        try:
            # Use dated_after to filter by expense date (not when it was last modified)
            # Set limit to 0 to get maximum number of expenses (per Splitwise API docs)
            response = requests.get(
                f'{self.base_url}/get_expenses',
                headers=self.headers,
                params={
                    'dated_after': formatted_date,
                    'limit': '0',  # 0 means get maximum allowed by API
                    # Note: No group_id parameter to get ALL expenses (groups + standalone)
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # Log how many expenses were returned
            expense_count = len(data.get('expenses', []))
            logger.debug(f"Retrieved {expense_count} expenses from Splitwise API")
            
            # Log date range of expenses for debugging
            if data.get('expenses'):
                dates = [exp['date'][:10] for exp in data['expenses']]  # Extract date part
                earliest = min(dates)
                latest = max(dates)
                logger.debug(f"Expense date range: {earliest} to {latest}")
            
            return data
        except requests.RequestException as e:
            raise APIError(f"Failed to get Splitwise expenses: {e}")


class YNABAPI:
    """Handles YNAB API interactions."""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = 'https://api.youneedabudget.com/v1'
        self.headers = {'Authorization': f'Bearer {token}'}
    
    def get_budget_id(self, budget_name: str) -> str:
        """Get budget ID by name, or return 'last-used' for default."""
        if budget_name == 'last-used':
            return 'last-used'
        
        try:
            response = requests.get(
                f'{self.base_url}/budgets/',
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            budgets = response.json()['data']['budgets']
            for budget in budgets:
                if budget['name'] == budget_name:
                    return budget['id']
            
            raise APIError(f"Budget '{budget_name}' not found in YNAB")
        except requests.RequestException as e:
            raise APIError(f"Failed to get YNAB budgets: {e}")
    
    def get_account_id(self, budget_id: str, account_name: str) -> str:
        """Get account ID by name within a budget."""
        try:
            response = requests.get(
                f'{self.base_url}/budgets/{budget_id}/accounts',
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            accounts = response.json()['data']['accounts']
            for account in accounts:
                if account['name'] == account_name:
                    return account['id']
            
            raise APIError(f"Account '{account_name}' not found in YNAB")
        except requests.RequestException as e:
            raise APIError(f"Failed to get YNAB accounts: {e}")
    
    def get_category_id(self, budget_id: str, category_name: str) -> str:
        """Get category ID by name within a budget."""
        try:
            response = requests.get(
                f'{self.base_url}/budgets/{budget_id}/categories',
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            
            category_groups = response.json()['data']['category_groups']
            for group in category_groups:
                for category in group['categories']:
                    if category['name'] == category_name:
                        return category['id']
            
            raise APIError(f"Category '{category_name}' not found in YNAB")
        except requests.RequestException as e:
            raise APIError(f"Failed to get YNAB categories: {e}")
    
    def get_account_transactions(self, budget_id: str, account_id: str, since_date=None) -> list:
        """Get transactions for a specific account since a given date."""
        try:
            params = {}
            if since_date:
                params['since_date'] = since_date
            
            response = requests.get(
                f'{self.base_url}/budgets/{budget_id}/accounts/{account_id}/transactions',
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()['data']['transactions']
        except requests.RequestException as e:
            raise APIError(f"Failed to get YNAB transactions: {e}")
    
    def get_all_account_transactions(self, budget_id: str, account_id: str) -> list:
        """Get ALL transactions for a specific account (for duplicate checking)."""
        import logging
        logger = logging.getLogger('splitwise_ynab_sync')
        
        try:
            # Try to get all transactions without any date filtering
            response = requests.get(
                f'{self.base_url}/budgets/{budget_id}/accounts/{account_id}/transactions',
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            transactions = response.json()['data']['transactions']
            
            # Log some details about what we retrieved
            logger.debug(f"Retrieved {len(transactions)} transactions from YNAB account")
            if transactions:
                with_import_ids = [tx for tx in transactions if tx.get('import_id')]
                logger.debug(f"{len(with_import_ids)} transactions have import_ids")
                
                # Log some sample transactions for debugging
                for i, tx in enumerate(transactions[:3]):
                    memo_str = tx.get('memo')
                    if memo_str is None:
                        memo_str = 'No memo'
                    else:
                        memo_str = str(memo_str)
                    logger.debug(f"Sample transaction {i+1}: import_id={tx.get('import_id')}, amount={tx.get('amount')}, memo={memo_str[:50]}...")
            
            return transactions
        except requests.RequestException as e:
            raise APIError(f"Failed to get all YNAB transactions: {e}")
    
    def create_transactions(self, budget_id: str, transactions: list) -> dict:
        """Create new transactions in YNAB."""
        if not transactions:
            return {"created": 0, "duplicates": []}
        
        try:
            payload = {"transactions": transactions}
            logger.debug(f"Sending {len(transactions)} transactions to YNAB")
            
            response = requests.post(
                f'{self.base_url}/budgets/{budget_id}/transactions',
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            # Log the response for debugging
            if response.status_code != 200:
                logger.error(f"YNAB API returned {response.status_code}: {response.text}")
                logger.error(f"Transaction payload that caused error: {payload}")
            
            response.raise_for_status()
            
            response_data = response.json()['data']
            logger.debug(f"YNAB response: {response.text}")
            
            return {
                "created": len(response_data.get('transaction_ids', [])),
                "duplicates": response_data.get('duplicate_import_ids', [])
            }
        except requests.RequestException as e:
            # Include the YNAB error response in our exception if available
            error_details = ""
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_details = f" - YNAB error: {e.response.text}"
                except:
                    error_details = f" - HTTP {e.response.status_code}"
            
            raise APIError(f"Failed to create YNAB transactions: {e}{error_details}")