"""Transaction processing logic for Splitwise expenses."""

import time
from decimal import Decimal
from typing import Dict, List, Any, Optional
import re
import logging

logger = logging.getLogger('splitwise_ynab_sync')


class TransactionProcessor:
    """Processes Splitwise expenses into YNAB transactions."""
    
    def __init__(self, user_id: int, user_name: str, allow_duplicates: bool):
        self.user_id = user_id
        self.user_name = user_name
        self.allow_duplicates = allow_duplicates
    
    def process_expenses(self, expenses: List[Dict], existing_import_ids: List[str]) -> List[Dict]:
        """Process Splitwise expenses into YNAB transaction format."""
        new_transactions = []
        skipped_duplicates = []
        
        for expense in expenses:
            # Skip deleted expenses
            if self._is_deleted(expense):
                logger.debug(f'Skipping deleted expense ID {expense["id"]}')
                continue
            
            # Skip duplicates if not allowed
            if not self.allow_duplicates and str(expense['id']) in existing_import_ids:
                logger.debug(f'Skipping duplicate expense ID {expense["id"]}: "{expense["description"]}"')
                skipped_duplicates.append(expense["description"])
                continue
            
            # Process different expense types
            transactions = self._process_expense(expense)
            new_transactions.extend(transactions)
            
            if transactions:
                logger.info(f'Processing expense: "{expense["description"]}" -> {len(transactions)} transaction(s)')
        
        # Log summary
        if skipped_duplicates:
            logger.info(f"Skipped {len(skipped_duplicates)} duplicate expenses: {', '.join(skipped_duplicates[:5])}" + 
                       (f" and {len(skipped_duplicates)-5} more" if len(skipped_duplicates) > 5 else ""))
        
        return new_transactions
    
    def _is_deleted(self, expense: Dict) -> bool:
        """Check if expense is deleted."""
        deleted_at = expense.get('deleted_at')
        return deleted_at is not None and deleted_at != '' and deleted_at != False
    
    def _process_expense(self, expense: Dict) -> List[Dict]:
        """Process a single expense into YNAB transactions."""
        expense_id = expense['id']
        expense_date = expense['date'].split('T')[0]
        description = expense['description']
        
        # Check for repayments first
        repayment_transactions = self._process_repayments(expense, expense_id, expense_date, description)
        if repayment_transactions:
            return repayment_transactions
        
        # Process regular expense or split payment
        return self._process_regular_expense(expense, expense_id, expense_date, description)
    
    def _process_repayments(self, expense: Dict, expense_id: int, expense_date: str, description: str) -> List[Dict]:
        """Process repayment transactions."""
        transactions = []
        
        for repayment in expense.get('repayments', []):
            if int(repayment['from']) == self.user_id:
                to_user_name = self._find_user_name(expense['users'], int(repayment['to']))
                
                transaction = self._create_repayment_transaction(
                    expense_id, expense_date, description, repayment['amount'], to_user_name
                )
                transactions.append(transaction)
        
        return transactions
    
    def _process_regular_expense(self, expense: Dict, expense_id: int, expense_date: str, description: str) -> List[Dict]:
        """Process regular expense or split payment."""
        user_data = self._get_user_data(expense['users'])
        
        if user_data['paid_share'] > 0:
            # User paid for the expense - create split transaction
            return [self._create_split_transaction(expense_id, expense_date, description, user_data)]
        elif user_data['owed_share'] != 0:
            # User owes money but didn't pay
            paid_by = self._find_payer(expense['users'])
            return [self._create_owed_transaction(expense_id, expense_date, description, user_data['owed_share'], paid_by)]
        
        return []
    
    def _get_user_data(self, users: List[Dict]) -> Dict[str, float]:
        """Extract current user's payment and owed amounts."""
        for user in users:
            if int(user['user']['id']) == self.user_id:
                return {
                    'paid_share': float(user.get('paid_share', '0')),
                    'owed_share': float(user.get('owed_share', '0'))
                }
        return {'paid_share': 0, 'owed_share': 0}
    
    def _find_user_name(self, users: List[Dict], user_id: int) -> str:
        """Find user's first name by ID."""
        for user in users:
            if int(user['user']['id']) == user_id:
                return user['user']['first_name']
        return "someone"
    
    def _find_payer(self, users: List[Dict]) -> str:
        """Find who paid for the expense."""
        for user in users:
            if float(user.get('paid_share', '0')) > 0:
                return user['user']['first_name']
        return "someone"
    
    def _create_import_id(self, expense_id: int, transaction_type: str) -> str:
        """Create unique import ID for transaction."""
        base_id = str(expense_id)
        if self.allow_duplicates:
            base_id = f"{expense_id}_dup_{int(time.time())}"
        
        return f"{base_id}_{transaction_type}"
    
    def _format_amount(self, amount: Any) -> tuple[int, str]:
        """Convert amount to YNAB milliunits and formatted string."""
        if isinstance(amount, (int, float)):
            milliunits = int(Decimal(str(amount)) * 1000)
            formatted = f'{float(amount):.2f}'
        else:
            cleaned = re.sub(r'[^\d\-.]', '', str(amount))
            milliunits = int(Decimal(cleaned) * 1000)
            formatted = f'{float(cleaned):.2f}'
        
        return milliunits, formatted
    
    def _create_split_transaction(self, expense_id: int, date: str, description: str, user_data: Dict) -> Dict:
        """Create a split transaction for when user paid."""
        user_share_amount, _ = self._format_amount(user_data['owed_share'])
        others_share = user_data['paid_share'] - user_data['owed_share']
        others_share_amount, _ = self._format_amount(others_share)
        
        memo = f"{description}, paid by {self.user_name} ({user_data['paid_share']:.2f}), my share {user_data['owed_share']:.2f}"
        
        return {
            "import_id": self._create_import_id(expense_id, "split"),
            "date": date,
            "amount": -user_share_amount + others_share_amount,
            "memo": memo,
            "cleared": "cleared",
            "subtransactions": [
                {"amount": -user_share_amount},  # My share (outflow)
                {"amount": others_share_amount}  # Others' share (inflow, needs category)
            ]
        }
    
    def _create_repayment_transaction(self, expense_id: int, date: str, description: str, amount: Any, paid_to: str) -> Dict:
        """Create a repayment/settlement transaction."""
        amount_milliunits, formatted_amount = self._format_amount(amount)
        memo = f"{description}, settlement to {paid_to} ({formatted_amount})"
        
        return {
            "import_id": self._create_import_id(expense_id, "repay"),
            "date": date,
            "amount": -amount_milliunits,  # Outflow
            "memo": memo,
            "cleared": "cleared"
        }
    
    def _create_owed_transaction(self, expense_id: int, date: str, description: str, amount: Any, paid_by: str) -> Dict:
        """Create a transaction for money owed to others."""
        amount_milliunits, formatted_amount = self._format_amount(amount)
        
        verb = 'owe' if self.user_name == 'you' else 'owes'
        memo = f"{description}, paid by {paid_by}, {self.user_name} {verb} {formatted_amount}"
        
        return {
            "import_id": self._create_import_id(expense_id, "exp"),
            "date": date,
            "amount": amount_milliunits,  # Inflow (you owe this)
            "memo": memo,
            "cleared": "cleared"
        }