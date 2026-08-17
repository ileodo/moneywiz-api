from typing import Dict

from moneywiz_api.model.payee import Payee
from moneywiz_api.managers.record_manager import RecordManager


class PayeeManager(RecordManager[Payee]):
    def __init__(self):
        super().__init__()

    @property
    def ents(self) -> Dict[str, type[Payee]]:
        return {
            "Payee": Payee,
        }
