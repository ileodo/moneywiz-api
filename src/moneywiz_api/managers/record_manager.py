from abc import ABC, abstractmethod
from typing import Callable, Dict, Generic, TypeVar

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.model.record import Record
from moneywiz_api.model.schema_mapped_row import mapped_row
from moneywiz_api.types import GID, ID

T = TypeVar("T", bound=Record)


class RecordManager(ABC, Generic[T]):
    def __init__(self) -> None:
        self._records: Dict[ID, T] = {}
        self._gid_to_id: Dict[GID, ID] = {}

    @property
    @abstractmethod
    def ents(self) -> Dict[str, Callable]:
        raise NotImplementedError()

    def load(self, db_accessor: DatabaseAccessor) -> None:
        records = db_accessor.query_objects(self.ents.keys())

        for record in records:
            typename = db_accessor.typename_for(record["Z_ENT"])
            assert typename in self.ents, (
                f"Unknown typename {typename} for record {record}"
            )

            model_cls = self.ents[typename]
            obj = model_cls(mapped_row(record, model_cls))
            obj.validate()
            self.add(obj)

    def add(self, record: T) -> None:
        self._records[record.id] = record
        if record.gid in self._gid_to_id:
            raise RuntimeError(
                f"Duplicate gid for {record}, existing record Id {self._gid_to_id[record.gid]}"
            )

        self._gid_to_id[record.gid] = record.id

    def get(self, record_id: ID) -> T | None:
        return self._records.get(record_id)

    def get_by_gid(self, gid: GID) -> T | None:
        return self._records.get(self._gid_to_id.get(gid))

    def records(self) -> Dict[ID, T]:
        return self._records

    def __repr__(self):
        return "\n".join(f"{key}: {value}" for key, value in self.records().items())
