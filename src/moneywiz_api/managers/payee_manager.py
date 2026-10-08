from moneywiz_api.schema_profile import SchemaProfile
from typing import Dict

from moneywiz_api.model.payee import Payee
from moneywiz_api.managers.record_manager import RecordManager


class PayeeManager(RecordManager[Payee]):
    def __init__(self, schema_profile: SchemaProfile):
        super().__init__(schema_profile)

    @property
    def ents(self) -> Dict[str, type[Payee]]:
        return {
            "Payee": Payee,
        }
