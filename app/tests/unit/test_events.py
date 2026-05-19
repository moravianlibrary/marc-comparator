import json

from adapters.events import (
    LockAcquiredEvent,
    LockReleasedEvent,
    TaskProgressEvent,
    TaskStatusEvent,
    parse_event,
)


class TestEventSerialization:
    def test_task_status_event_round_trip(self):
        event = TaskStatusEvent(
            task_id="abc-123",
            status="Success",
            severity="Info",
            created_by="user-1",
        )
        raw = event.model_dump_json()
        parsed = parse_event(raw)
        assert isinstance(parsed, TaskStatusEvent)
        assert parsed.type == "task.status"
        assert parsed.task_id == "abc-123"
        assert parsed.status == "Success"
        assert parsed.severity == "Info"
        assert parsed.created_by == "user-1"

    def test_task_progress_event_round_trip(self):
        event = TaskProgressEvent(
            task_id="abc-123",
            progress=0.75,
            created_by="user-1",
        )
        raw = event.model_dump_json()
        parsed = parse_event(raw)
        assert isinstance(parsed, TaskProgressEvent)
        assert parsed.type == "task.progress"
        assert parsed.progress == 0.75

    def test_lock_acquired_event_round_trip(self):
        event = LockAcquiredEvent(lock_name="catalog_sync_MZK01")
        raw = event.model_dump_json()
        parsed = parse_event(raw)
        assert isinstance(parsed, LockAcquiredEvent)
        assert parsed.type == "lock.acquired"
        assert parsed.lock_name == "catalog_sync_MZK01"

    def test_lock_released_event_round_trip(self):
        event = LockReleasedEvent(lock_name="catalog_sync_MZK01")
        raw = event.model_dump_json()
        parsed = parse_event(raw)
        assert isinstance(parsed, LockReleasedEvent)
        assert parsed.type == "lock.released"

    def test_discriminated_union_via_type_field(self):
        raw = json.dumps({"type": "task.status", "task_id": "x", "status": "Started", "severity": "Info", "created_by": "u"})
        parsed = parse_event(raw)
        assert isinstance(parsed, TaskStatusEvent)

        raw = json.dumps({"type": "lock.acquired", "lock_name": "test"})
        parsed = parse_event(raw)
        assert isinstance(parsed, LockAcquiredEvent)
