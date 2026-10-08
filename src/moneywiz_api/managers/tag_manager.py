from moneywiz_api.schema_profile import SchemaProfile
from typing import Dict

from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.model import Tag


class TagManager(RecordManager[Tag]):
    def __init__(self, schema_profile: SchemaProfile):
        super().__init__(schema_profile)

    @property
    def ents(self) -> Dict[str, type[Tag]]:
        return {
            "Tag": Tag,
        }
