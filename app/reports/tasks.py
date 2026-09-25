import io
import zipfile
from collections import defaultdict
from collections.abc import Iterator, Sequence

from marc_comparator.comparators import ComparisonReportInput, ReportFile
from marc_comparator.validators import ReportInput, ValidationResult, Validator
from marcdantic import MarcRecord

from adapters.database import DatabaseSession
from adapters.marc_sectors import read_marc_for_ids
from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from authority_linking.tasks import LINK_PREFETCH_WINDOW, windows
from catalog_records.search import build_filtered_query
from config import config
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.report_artifact import ReportArtifact
from entities.validation import Validation

from .models import CreateReportData, ReportToolKind


def _failing_results_for(
    db_session: DatabaseSession, record_ids: Sequence[str], tool: str
) -> dict[str, list[ValidationResult]]:
    """One window's not-valid results for one validator, keyed by record.

    One query for the window in place of one per record. The results are read
    out of the rows here rather than handed back as rows: the caller cycles
    its session as it walks the window, which would detach them.
    """

    failing: dict[str, list[ValidationResult]] = defaultdict(list)
    if not record_ids:
        return failing
    for validation in (
        db_session.query(Validation)
        .filter(
            Validation.catalog_record_id.in_(record_ids),
            Validation.validator == tool,
            Validation._result["status"].astext != "Valid",
        )
        .all()
    ):
        failing[validation.catalog_record_id].append(validation.validation_result)
    return failing


def _comparison_inputs_for(
    db_session: DatabaseSession, record_ids: Sequence[str], tool: str
) -> dict[str, list[ComparisonReportInput]]:
    """One window's stored comparisons, keyed by record, already built.

    One query for the window in place of one per record, and built into report
    inputs here for the same reason as above.
    """

    stored: dict[str, list[ComparisonReportInput]] = defaultdict(list)
    if not record_ids:
        return stored
    for comparison in (
        db_session.query(Comparison)
        .filter(
            Comparison.main_record_id.in_(record_ids),
            Comparison.comparator == tool,
        )
        .all()
    ):
        stored[comparison.main_record_id].append(
            ComparisonReportInput(
                catalog_record_id=comparison.main_record_id,
                base=comparison.base,
                other_record_id=comparison.other_record_id,
                result=comparison.record_result,
            )
        )
    return stored


def _filtered_record_ids(ctx: ManagedTask, data: CreateReportData) -> list[str]:
    return [
        r.id
        for r in build_filtered_query(ctx.db_session, data.filters)
        .with_entities(CatalogRecord.id)
        .all()
    ]


def _validator_report_files(ctx: ManagedTask, data: CreateReportData) -> list[ReportFile]:
    from validation.tasks import load_validators

    validator = Validator(data.tool)
    instances = load_validators(ctx.db_session, [validator], ctx.logger)
    if not instances:
        raise ValueError(f"Validator '{data.tool}' could not be initialized")

    instance = instances[0].instance
    if not instance.can_generate_report:
        raise ValueError(f"Validator '{data.tool}' does not support report generation")

    record_ids = _filtered_record_ids(ctx, data)
    ctx.total = len(record_ids)

    def inputs() -> Iterator[ReportInput]:
        for window in windows(record_ids, LINK_PREFETCH_WINDOW):
            # Two queries for the window, where it was four per record: the
            # row, its validations, and two more to locate and decompress the
            # MARC. Only the records with something to report need their MARC,
            # so the read is asked for those and not for the whole window.
            failing = _failing_results_for(ctx.db_session, window, data.tool)
            marc_by_id = read_marc_for_ids(ctx.db_session, list(failing))

            for record_id in window:
                results = failing.get(record_id)
                found = marc_by_id.get(record_id) if results else None
                if results and found is None:
                    ctx.logger.warning(f"Skipping {record_id}: no MARC record found in storage")
                elif results and found is not None:
                    base, _system_number, raw = found
                    yield ReportInput(
                        catalog_record_id=record_id,
                        base=base,
                        marc=MarcRecord.from_mrc(raw),
                        results=results,
                    )
                handle_batch_progress_snippet(ctx)
        handle_final_batch_snippet(ctx)

    return instance.generate_report(inputs())


def _comparator_report_files(ctx: ManagedTask, data: CreateReportData) -> list[ReportFile]:
    from comparison.tasks import load_comparator

    comparator = load_comparator(ctx.db_session)
    if not comparator:
        raise ValueError("Comparator could not be initialized")
    if not comparator.can_generate_report:
        raise ValueError(f"Comparator '{data.tool}' does not support report generation")

    record_ids = _filtered_record_ids(ctx, data)
    ctx.total = len(record_ids)

    def inputs() -> Iterator[ComparisonReportInput]:
        for window in windows(record_ids, LINK_PREFETCH_WINDOW):
            stored = _comparison_inputs_for(ctx.db_session, window, data.tool)
            for record_id in window:
                yield from stored.get(record_id, ())
                handle_batch_progress_snippet(ctx)
        handle_final_batch_snippet(ctx)

    return comparator.generate_report(inputs())


async def create_report(task_id: str) -> None:
    async with ManagedTask(task_id=task_id, lock_key=f"task-run-{task_id}") as ctx:
        data = CreateReportData.model_validate(ctx.task.data)

        if data.kind == ReportToolKind.Validator:
            report_files = _validator_report_files(ctx, data)
        else:
            report_files = _comparator_report_files(ctx, data)

        if not report_files:
            # Not an error — the tool ran fine, the filtered set just held
            # nothing repairable. Warn so the task does not finish green with
            # no download and no explanation.
            ctx.logger.warning(
                f"'{data.tool}' produced no report data for the selected records — "
                "nothing to download. The filtered set has no stored results this "
                "tool can act on."
            )
            return

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for report_file in report_files:
                archive.writestr(report_file.filename, report_file.content)
        blob = buffer.getvalue()

        # There is one comparator and it is called "default", so its name adds
        # nothing to "comparator". Validators are plural — theirs identifies it.
        stem = (
            data.kind.value
            if data.kind is ReportToolKind.Comparator
            else f"{data.kind.value}_{data.tool}"
        )
        filename = f"{stem}_{config.timestamp:%Y-%m-%d}.zip"
        ReportArtifact(
            task_id=ctx.task.task_id,
            tool=data.tool,
            filename=filename,
            content_type="application/zip",
            blob=blob,
            size=len(blob),
        ).save(ctx.db_session, commit=False)

        ctx.logger.info(
            f"Generated report '{filename}' ({len(report_files)} file(s), {len(blob)} bytes)"
        )
