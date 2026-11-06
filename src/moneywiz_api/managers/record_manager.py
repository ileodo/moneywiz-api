from abc import ABC, abstractmethod
from typing import Dict, Generic, TypeVar

from moneywiz_api.database_accessor import DatabaseAccessor
from moneywiz_api.managers.failed_record import FailedRecord, RecordLoadError
from moneywiz_api.model.record import Record
from moneywiz_api.types import GID, ID

T = TypeVar("T", bound=Record)


class RecordManager(ABC, Generic[T]):
    def __init__(self) -> None:
        self._records: Dict[ID, T] = {}
        self._gid_to_id: Dict[GID, ID] = {}
        self.failed_records: list[FailedRecord] = []

    @property
    @abstractmethod
    def ents(self) -> Dict[str, type[T]]:
        raise NotImplementedError()

    def load(
        self,
        db_accessor: DatabaseAccessor,
        strict: bool = False,
        wrap_errors: bool = False,
    ) -> None:
        self._records = {}
        self._gid_to_id = {}
        self.failed_records = []
        records = db_accessor.query_objects(list(self.ents.keys()))

        for record in records:
            typename = db_accessor.typename_for(record["Z_ENT"])
            assert typename in self.ents, (
                f"Unknown typename {typename} for record {record}"
            )

            model_cls = self.ents[typename]
            obj = None
            try:
                obj = db_accessor.schema_profile.create_record(record, model_cls)
                obj.validate()
            except Exception as error:
                if strict:
                    if wrap_errors:
                        raise RecordLoadError(
                            FailedRecord(typename, dict(record), error, obj)
                        ) from error
                    raise
                self.failed_records.append(
                    FailedRecord(typename, dict(record), error, obj)
                )
                continue
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
        record_id = self._gid_to_id.get(gid)
        if record_id is None:
            return None
        return self._records.get(record_id)

    def records(self) -> Dict[ID, T]:
        return self._records

    def __repr__(self):
        return "\n".join(f"{key}: {value}" for key, value in self.records().items())
