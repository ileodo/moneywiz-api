from typing import Dict

from moneywiz_api.model.payee import Payee
from moneywiz_api.managers.record_manager import RecordManager


class PayeeManager(RecordManager[Payee]):
    @property
    def ents(self) -> Dict[str, type[Payee]]:
        return {
            "Payee": Payee,
        }
