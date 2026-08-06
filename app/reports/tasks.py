import io
import zipfile
from collections.abc import Iterator

from marc_comparator.comparators import ComparisonReportInput, ReportFile
from marc_comparator.validators import ReportInput, Validator

from adapters.tasks import (
    ManagedTask,
    handle_batch_progress_snippet,
    handle_final_batch_snippet,
)
from catalog_records.search import build_filtered_query
from config import config
from entities.catalog_record import CatalogRecord
from entities.comparison import Comparison
from entities.report_artifact import ReportArtifact
from entities.validation import Validation

from .models import CreateReportData, ReportToolKind


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
        for record_id in record_ids:
            record = ctx.db_session.get(CatalogRecord, record_id)
            validations = (
                ctx.db_session.query(Validation)
                .filter(
                    Validation.catalog_record_id == record_id,
                    Validation.validator == data.tool,
                    Validation._result["status"].astext != "Valid",
                )
                .all()
            )
            if validations and record is not None:
                results = [v.validation_result for v in validations]
                try:
                    marc = record.get_record(ctx.db_session)
                    yield ReportInput(
                        catalog_record_id=record.id,
                        base=record.base,
                        marc=marc,
                        results=results,
                    )
                except ValueError as exc:
                    ctx.logger.warning(f"Skipping {record_id}: {exc}")
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
        for record_id in record_ids:
            comparisons = (
                ctx.db_session.query(Comparison)
                .filter(
                    Comparison.main_record_id == record_id,
                    Comparison.comparator == data.tool,
                )
                .all()
            )
            for comparison in comparisons:
                yield ComparisonReportInput(
                    catalog_record_id=comparison.main_record_id,
                    base=comparison.base,
                    other_record_id=comparison.other_record_id,
                    result=comparison.record_result,
                )
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

        filename = f"{data.tool}_{config.timestamp:%Y-%m-%d}.zip"
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
