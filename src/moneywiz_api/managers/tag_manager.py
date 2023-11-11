from typing import Dict, Callable

from moneywiz_api.model import Tag
from moneywiz_api.managers.record_manager import RecordManager


class TagManager(RecordManager[Tag]):
    def __init__(self):
        super().__init__()

    @property
    def ents(self) -> Dict[str, Callable]:
        return {
            "Tag": Tag,
        }
