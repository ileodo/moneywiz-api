from typing import Dict, Callable

from src.moneywiz_api.model.payee import Payee
from src.moneywiz_api.managers.record_manager import RecordManager


class PayeeManager(RecordManager[Payee]):
    def __init__(self):
        super().__init__()

    @property
    def ents(self) -> Dict[str, Callable]:
        return {
            "Payee": Payee,
        }
