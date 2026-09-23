"""What a task names as its subject, so two runs of one type read differently."""

import uuid

from entities.task import Task, TaskType


def task(task_type: TaskType, data) -> Task:
    return Task(type=task_type, name="x", created_by=uuid.uuid4(), data=data)


class TestTarget:
    def test_a_plugin_harvest_names_its_plugin(self):
        # Without this every harvest reads "Stažení dat pro rozšíření", whichever
        # plugin it ran for, and the task list cannot tell two of them apart.
        assert (
            task(TaskType.HarvestPlugin, {"plugin": "marcxml-dump", "full_rebuild": False}).target
            == "marcxml-dump"
        )

    def test_a_sync_names_its_base(self):
        assert task(TaskType.SyncRecords, {"base": "MZK01", "from_date": None}).target == "MZK01"

    def test_linking_and_comparison_name_their_target_base(self):
        assert task(TaskType.CompareRecords, {"target_base": "SKC"}).target == "SKC"
        assert task(TaskType.LinkRecordsToAuthorities, {"target_base": "SKC"}).target == "SKC"

    def test_a_task_over_a_selection_has_no_single_subject(self):
        # Processing runs over whatever is unprocessed; naming one thing would
        # claim a scope it does not have, so the plain label stands.
        assert task(TaskType.ProcessRecords, {"processed": False}).target is None
        assert task(TaskType.DeleteTasks, {"max_age_days": 30}).target is None

    def test_missing_or_unusable_data_is_not_an_error(self):
        assert task(TaskType.HarvestPlugin, None).target is None
        assert task(TaskType.HarvestPlugin, {}).target is None
        assert task(TaskType.HarvestPlugin, {"plugin": ""}).target is None
        assert task(TaskType.HarvestPlugin, {"plugin": 7}).target is None
        assert task(TaskType.SyncRecords, ["MZK01"]).target is None
