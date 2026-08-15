from typing import Callable, Dict

from moneywiz_api.managers.record_manager import RecordManager
from moneywiz_api.model import Tag


class TagManager(RecordManager[Tag]):
    def __init__(self):
        super().__init__()

    @property
    def ents(self) -> Dict[str, Callable]:
        return {
            "Tag": Tag,
        }
