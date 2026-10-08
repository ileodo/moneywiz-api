from typing import Dict

from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.model import Tag


class TagManager(RecordManager[Tag]):
    @property
    def ents(self) -> Dict[str, type[Tag]]:
        return {
            "Tag": Tag,
        }
