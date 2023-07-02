from abc import ABC, abstractmethod
from typing import Dict, Generic, TypeVar, Callable

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.model.record import Record
from moneywiz_api.types import ID


T = TypeVar("T", bound=Record)


class RecordManager(ABC, Generic[T]):
    def __init__(self):
        self._records: Dict[ID, T] = {}

    @property
    @abstractmethod
    def ents(self) -> Dict[str, Callable]:
        raise NotImplementedError()

    def load(self, db_accessor: DatabaseAccessor) -> None:
        records = db_accessor.query_objects(self.ents.keys())

        for record in records:
            typename = db_accessor.typename_for(record["Z_ENT"])
            if typename in self.ents:
                obj = self.ents[typename](record)
                self.add(obj)

    def add(self, record: T) -> None:
        self._records[record.id] = record

    def get(self, record_id: ID) -> T | None:
        return self._records.get(record_id)

    def records(self) -> Dict[ID, T]:
        return self._records

    def __repr__(self):
        return "\n".join(f"{key}: {value}" for key, value in self.records().items())
