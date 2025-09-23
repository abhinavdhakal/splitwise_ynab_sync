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
    
    def get_recent_expenses(self, days_back) -> Dict[str, Any]:
        """Get expenses updated in the last N days."""
        try:
            response = requests.get(
                f'{self.base_url}/get_expenses',
                headers=self.headers,
                params={'updated_after': days_back},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
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
    
    def get_account_transactions(self, budget_id: str, account_id: str, since_date) -> list:
        """Get transactions for a specific account since a given date."""
        try:
            response = requests.get(
                f'{self.base_url}/budgets/{budget_id}/accounts/{account_id}/transactions',
                headers=self.headers,
                params={'since_date': since_date},
                timeout=30
            )
            response.raise_for_status()
            return response.json()['data']['transactions']
        except requests.RequestException as e:
            raise APIError(f"Failed to get YNAB transactions: {e}")
    
    def create_transactions(self, budget_id: str, transactions: list) -> dict:
        """Create new transactions in YNAB."""
        if not transactions:
            return {"created": 0, "duplicates": []}
        
        try:
            payload = {"transactions": transactions}
            response = requests.post(
                f'{self.base_url}/budgets/{budget_id}/transactions',
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            response_data = response.json()['data']
            logger.debug(f"YNAB response: {response.text}")
            
            return {
                "created": len(response_data.get('transaction_ids', [])),
                "duplicates": response_data.get('duplicate_import_ids', [])
            }
        except requests.RequestException as e:
            raise APIError(f"Failed to create YNAB transactions: {e}")