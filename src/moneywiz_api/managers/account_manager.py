from typing import Callable, Dict, List

from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.model.account import (
    Account,
    BankChequeAccount,
    BankSavingAccount,
    CashAccount,
    CreditCardAccount,
    ForexAccount,
    InvestmentAccount,
    LoanAccount,
)
from moneywiz_api.types import ID


class AccountManager(RecordManager[Account]):
    def __init__(self):
        super().__init__()

    @property
    def ents(self) -> Dict[str, Callable]:
        return {
            "BankChequeAccount": BankChequeAccount,
            "BankSavingAccount": BankSavingAccount,
            "CashAccount": CashAccount,
            "CreditCardAccount": CreditCardAccount,
            "LoanAccount": LoanAccount,
            "InvestmentAccount": InvestmentAccount,
            "ForexAccount": ForexAccount,
        }

    def records(self) -> Dict[ID, Account]:
        return dict(sorted(super().records().items(), key=lambda x: x[1].display_order))

    def get_accounts_for_user(self, user_id: ID) -> List[Account]:
        return sorted(
            [x for _, x in self.records().items() if x.user == user_id],
            key=lambda x: (x.group_id, x.display_order),
        )
