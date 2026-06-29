"""Converts Splitwise expenses into YNAB transactions."""

import hashlib
import time
import re
import logging
from decimal import Decimal
from typing import Dict, List, Any

logger = logging.getLogger('splitwise_ynab_sync')


class TransactionProcessor:
    """Processes Splitwise expenses into YNAB transaction format."""

    def __init__(self, user_id: int, user_name: str, allow_duplicates: bool):
        self.user_id = user_id
        self.user_name = user_name
        self.allow_duplicates = allow_duplicates

    # -------------------------------------------------------------------------
    # Public interface
    # -------------------------------------------------------------------------

    def process_expenses(self, expenses: List[Dict], existing_import_ids: List[str]) -> List[Dict]:
        """Convert a list of Splitwise expenses into new YNAB transactions."""
        new_transactions = []
        sorted_expenses = sorted(expenses, key=lambda x: x.get('date', ''), reverse=True)

        for expense in sorted_expenses:
            date_str = expense['date'][:10]

            if self._is_deleted(expense):
                logger.debug(f'Skipping deleted expense {expense["id"]} ({date_str})')
                continue

            is_edited = (
                expense.get('created_at') and expense.get('updated_at')
                and expense['created_at'] != expense['updated_at']
            )

            transactions = self._process_expense(expense, existing_import_ids)
            new_transactions.extend(transactions)

            if transactions:
                edit_note = " (edited)" if is_edited else ""
                logger.info(f'New ({date_str}): "{expense["description"]}"{edit_note} → {len(transactions)} transaction(s)')
            else:
                logger.debug(f'Skipped ({date_str}): "{expense["description"]}" — already in YNAB')

        return new_transactions

    # -------------------------------------------------------------------------
    # Expense routing
    # -------------------------------------------------------------------------

    def _process_expense(self, expense: Dict, existing_import_ids: List[str]) -> List[Dict]:
        expense_id = expense['id']
        transaction_date = (
            expense['created_at'].split('T')[0] if expense.get('created_at')
            else expense['date'].split('T')[0]
        )
        description = expense['description']

        # If you owe someone (repayment FROM you), always take the repayment path.
        # This is critical: when the repayment is already in YNAB, _process_repayments
        # returns [] — without this guard, the code would fall through to
        # _process_regular_expense and create the same debt with the opposite sign.
        has_user_repayment = any(
            int(r['from']) == self.user_id
            for r in expense.get('repayments', [])
        )
        if has_user_repayment:
            return self._process_repayments(expense, expense_id, transaction_date, description, existing_import_ids)

        return self._process_regular_expense(expense, expense_id, transaction_date, description, existing_import_ids)

    def _process_repayments(self, expense: Dict, expense_id: int, date: str, description: str, existing_import_ids: List[str]) -> List[Dict]:
        """Handle expenses where you owe money to someone."""
        transactions = []
        for repayment in expense.get('repayments', []):
            if int(repayment['from']) != self.user_id:
                continue

            import_id = self._repayment_import_id(expense_id, int(repayment['to']))
            if not self.allow_duplicates and import_id in existing_import_ids:
                to_name = self._find_user_name(expense['users'], int(repayment['to']))
                logger.info(f'Duplicate repayment for expense {expense_id} to {to_name} — skipping')
                continue

            to_name = self._find_user_name(expense['users'], int(repayment['to']))
            transactions.append(self._make_repayment(expense_id, date, description, repayment['amount'], to_name, import_id))

        return transactions

    def _process_regular_expense(self, expense: Dict, expense_id: int, date: str, description: str, existing_import_ids: List[str]) -> List[Dict]:
        """Handle expenses where you paid for others, or others paid for you."""
        user_data = self._get_user_data(expense['users'])

        if user_data['paid_share'] > 0:
            import_id = self._import_id(expense_id, "split")
            if not self.allow_duplicates and import_id in existing_import_ids:
                logger.info(f'Duplicate split for expense {expense_id} — skipping')
                return []
            return [self._make_split(expense_id, date, description, user_data)]

        if user_data['owed_share'] != 0:
            import_id = self._import_id(expense_id, "exp")
            if not self.allow_duplicates and import_id in existing_import_ids:
                logger.info(f'Duplicate owed for expense {expense_id} — skipping')
                return []
            paid_by = self._find_payer(expense['users'])
            return [self._make_owed(expense_id, date, description, user_data['owed_share'], paid_by)]

        return []

    # -------------------------------------------------------------------------
    # Transaction builders
    # -------------------------------------------------------------------------

    def _make_repayment(self, expense_id: int, date: str, description: str, amount: Any, paid_to: str, import_id: str) -> Dict:
        """Outflow: you are paying someone back."""
        milliunits, formatted = self._to_milliunits(amount)
        return {
            "import_id": import_id,
            "date": date,
            "amount": -milliunits,  # negative = outflow
            "memo": f"{description}, settlement to {paid_to} ({formatted})",
            "cleared": "cleared"
        }

    def _make_split(self, expense_id: int, date: str, description: str, user_data: Dict) -> Dict:
        """Inflow: you paid, others owe you their share."""
        others_share = user_data['paid_share'] - user_data['owed_share']
        milliunits, formatted = self._to_milliunits(others_share)
        memo = f"{description} | Total: {user_data['paid_share']:.2f} | My: {user_data['owed_share']:.2f} | Others: {formatted}"
        return {
            "import_id": self._import_id(expense_id, "split"),
            "date": date,
            "amount": milliunits,  # positive = inflow
            "memo": memo,
            "cleared": "cleared"
        }

    def _make_owed(self, expense_id: int, date: str, description: str, amount: Any, paid_by: str) -> Dict:
        """Inflow: someone paid for you (debt recorded in Splitwise account)."""
        milliunits, formatted = self._to_milliunits(amount)
        verb = 'owe' if self.user_name == 'you' else 'owes'
        return {
            "import_id": self._import_id(expense_id, "exp"),
            "date": date,
            "amount": milliunits,  # positive = inflow (debt owed)
            "memo": f"{description}, paid by {paid_by}, {self.user_name} {verb} {formatted}",
            "cleared": "cleared"
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _is_deleted(self, expense: Dict) -> bool:
        deleted_at = expense.get('deleted_at')
        if deleted_at not in (None, '', False, '0'):
            return True
        if expense.get('deleted_by') is not None:
            return True
        if expense.get('deleted') is True:
            return True
        return False

    def _get_user_data(self, users: List[Dict]) -> Dict[str, float]:
        for user in users:
            if int(user['user']['id']) == self.user_id:
                return {
                    'paid_share': float(user.get('paid_share', '0')),
                    'owed_share': float(user.get('owed_share', '0'))
                }
        return {'paid_share': 0.0, 'owed_share': 0.0}

    def _find_user_name(self, users: List[Dict], user_id: int) -> str:
        for user in users:
            if int(user['user']['id']) == user_id:
                return user['user']['first_name']
        return "someone"

    def _find_payer(self, users: List[Dict]) -> str:
        for user in users:
            if float(user.get('paid_share', '0')) > 0:
                return user['user']['first_name']
        return "someone"

    def _to_milliunits(self, amount: Any) -> tuple[int, str]:
        """Convert an amount to YNAB milliunits and a formatted string."""
        if isinstance(amount, (int, float)):
            milliunits = int(Decimal(str(amount)) * 1000)
            formatted = f'{float(amount):.2f}'
        else:
            cleaned = re.sub(r'[^\d\-.]', '', str(amount))
            milliunits = int(Decimal(cleaned) * 1000)
            formatted = f'{float(cleaned):.2f}'
        return milliunits, formatted

    def _import_id(self, expense_id: int, tx_type: str) -> str:
        """Stable import ID for deduplication (max 36 chars for YNAB)."""
        base = f"{expense_id}_{tx_type}" if not self.allow_duplicates else f"{expense_id}_{tx_type}_{int(time.time())}"
        if len(base) <= 36:
            return base
        suffix = hashlib.md5(base.encode()).hexdigest()[:8]
        return f"{expense_id}_{tx_type[:4]}_{suffix}"

    def _repayment_import_id(self, expense_id: int, to_user_id: int) -> str:
        """Stable import ID for repayment transactions (max 36 chars for YNAB)."""
        base = f"{expense_id}_repay_{to_user_id}" if not self.allow_duplicates else f"{expense_id}_repay_{to_user_id}_{int(time.time())}"
        if len(base) <= 36:
            return base
        suffix = hashlib.md5(base.encode()).hexdigest()[:8]
        return f"{expense_id}_rp{to_user_id}_{suffix}"
