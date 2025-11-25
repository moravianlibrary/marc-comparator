import asyncio
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import typer
from marcdantic import MarcRecord

from marc_comparator.authority_linkers import (
    AUTHORITY_LINKER_DISPATCHER,
    AuthorityLinker,
)
from marc_comparator.comparators import COMPARATOR_DISPATCHER, Comparator
from marc_comparator.validators import VALIDATOR_DISPATCHER, Validator

app = typer.Typer(help="MARC Comparator CLI tool")


def _print_marc_record(record: MarcRecord):
    typer.echo(f"Leader: {record.leader}")
    typer.echo("Fixed Fields:")
    for tag, data in record.fixed_fields.root.items():
        typer.echo(f"  {tag} {data}")
    typer.echo("Variable Fields:")
    for tag, fields in record.variable_fields.root.items():
        for field in fields:
            ind1 = field.ind1 or "-"
            ind2 = field.ind2 or "-"
            subfields_str = " ".join(
                f"|{code} {value}"
                for code, values in field.subfields.items()
                for value in values
            )
            typer.echo(f"  {tag} {ind1}{ind2}  {subfields_str}")


@app.command()
def print(
    mrc_file_paths: List[Path] = typer.Argument(
        ..., help="Paths to MARC record files"
    )
):
    """
    Print the paths of the provided MARC record files.
    """
    for path in mrc_file_paths:
        if not path.exists():
            typer.echo(f"File does not exist: {path}")
            continue

        if not path.is_file():
            typer.echo(f"Not a file: {path}")
            continue

        if path.suffix != ".mrc":
            typer.echo(f"Not a MARC file (expected .mrc extension): {path}")
            continue

        with path.open("rb") as f:
            record = MarcRecord.from_mrc(f.read())

            typer.echo("=" * 80)
            typer.echo(f"File: {path}")
            _print_marc_record(record)


@app.command()
def to_json(
    mrc_file_paths: List[Path] = typer.Argument(
        ..., help="Paths to MARC record files"
    )
):
    """
    Print the paths of the provided MARC record files.
    """
    for path in mrc_file_paths:
        if not path.exists():
            typer.echo(f"File does not exist: {path}")
            continue

        if not path.is_file():
            typer.echo(f"Not a file: {path}")
            continue

        if path.suffix != ".mrc":
            typer.echo(f"Not a MARC file (expected .mrc extension): {path}")
            continue

        with path.open("rb") as f:
            record = MarcRecord.from_mrc(f.read())

        json_path = path.with_suffix(".json")
        with json_path.open("w", encoding="utf-8") as f:
            f.write(
                record.model_dump_json(
                    indent=2, exclude_unset=True, exclude_none=True
                )
            )


def init_validator(validator: Validator, config_path: Path | None):
    if config_path is None:
        return VALIDATOR_DISPATCHER[validator]()

    if not config_path.exists():
        typer.echo(f"Config file does not exist: {config_path}", err=True)
        exit(1)

    if not config_path.is_file():
        typer.echo(f"Not a file: {config_path}", err=True)
        exit(1)

    with config_path.open("r", encoding="utf-8") as f:
        config_data = f.read()

    validator_cls = VALIDATOR_DISPATCHER[validator]
    return validator_cls(
        validator_cls.config_model.model_validate_json(config_data)
    )


@app.command()
def validate(
    mrc_file_paths: List[Path] = typer.Argument(
        ..., help="Paths to MARC record files"
    ),
    validators: List[str] = typer.Option(
        [str(val) for val in VALIDATOR_DISPATCHER.keys()],
        "--validator",
        "-v",
        help="Names of validators to apply",
    ),
    output: Path = typer.Option(
        Path("report.csv"),
        "--output",
        "-o",
        help="Path to output report file (CSV format).",
    ),
):
    validator_props: List[Tuple[str, Path | None]] = []
    for pair in validators:
        if "=" in pair:
            name, path = pair.split("=", 1)
            validator_props.append((Validator(name), Path(path)))
        else:
            validator_props.append((Validator(pair), None))

    report_data = []

    for path in mrc_file_paths:
        for validator, config_path in validator_props:
            validator_inst = init_validator(validator, config_path)

            with path.open("rb") as f:
                record = MarcRecord.from_mrc(f.read())

            for result in asyncio.run(validator_inst.run(record)):
                report_data.append(
                    {
                        "path": path,
                        "validator": validator,
                        "tag": result.target.tag,
                        "codes": (
                            ",".join(result.target.codes)
                            if result.target.codes
                            else None
                        ),
                        "status": result.status.value,
                        "reason": result.reason,
                        "details": result.details,
                        "hint": result.hint,
                    }
                )

    report = pd.DataFrame(report_data)
    report.to_csv(output, index=False)


@app.command()
def link(
    linker: AuthorityLinker = typer.Argument(
        ..., help="Authority linker to use"
    ),
    base: str = typer.Argument(
        ..., help="Source catalog base or dataset identifier"
    ),
    system_number: str = typer.Argument(
        ..., help="System number of the record"
    ),
    mrc_file_path: Path = typer.Argument(
        ..., help="Paths to MARC record files"
    ),
    target_base: str = typer.Argument(..., help="Target authority base"),
    linker_config: Path | None = typer.Option(
        None, help="Path to authority linker configuration file"
    ),
):
    linker_cls = AUTHORITY_LINKER_DISPATCHER[linker]

    if linker_cls.config_model is not None and linker_config is not None:
        if not linker_config.exists():
            typer.echo(
                f"Config file does not exist: {linker_config}", err=True
            )
            typer.exit(1)

        if not linker_config.is_file():
            typer.echo(f"Not a file: {linker_config}", err=True)
            typer.exit(1)

        with linker_config.open("r", encoding="utf-8") as f:
            config_data = f.read()

        config = linker_cls.config_model.model_validate_json(config_data)
        linker_inst = linker_cls(config)
    elif linker_cls.config_model is not None and linker_config is None:
        linker_inst = linker_cls(linker_cls.config_model())
    else:
        linker_inst = linker_cls()

    with mrc_file_path.open("rb") as f:
        record = MarcRecord.from_mrc(f.read())

    link = asyncio.run(
        linker_inst.run(base, system_number, record, target_base)
    )

    if link is not None:
        typer.echo("Authority link found:")
        typer.echo(f"  Base: {link.base}")
        typer.echo(f"  System Number: {link.system_number}")
        typer.echo(f"  Confidence: {link.confidence}")
        typer.echo("  Linked Record:")
        _print_marc_record(link.record)
    else:
        typer.echo("No authority link found.")


@app.command()
def compare(
    comparator: Comparator = typer.Argument(..., help="Comparator to use"),
    config: Path = typer.Argument(
        ..., help="Path to comparator configuration file"
    ),
    mrc_a: Path = typer.Argument(..., help="Paths to MARC record files"),
    mrc_b: Path = typer.Argument(..., help="Paths to MARC record files"),
):
    """
    Compare two MARC records.
    """

    comparator_cls = COMPARATOR_DISPATCHER[comparator]

    if not config.exists():
        typer.echo(f"Config file does not exist: {config}", err=True)
        typer.exit(1)

    if not config.is_file():
        typer.echo(f"Not a file: {config}", err=True)
        typer.exit(1)

    with config.open("r", encoding="utf-8") as f:
        config_data = f.read()

    comparator_inst = comparator_cls(
        comparator_cls.config_model.model_validate_json(config_data)
    )

    with mrc_a.open("rb") as f:
        record_a = MarcRecord.from_mrc(f.read())

    with mrc_b.open("rb") as f:
        record_b = MarcRecord.from_mrc(f.read())

    comparison = asyncio.run(comparator_inst.run(record_a, record_b))

    typer.echo(f"Overall Score: {comparison.overall_score:.4f}")

    for field_comparison in comparison.field_results or []:
        field_strs = [f"Tag: {field_comparison.tag}"]

        if field_comparison.tagB:
            field_strs.append(f"TagB: {field_comparison.tagB}")

        field_strs.append(f"IdxA: {field_comparison.idxA}")
        field_strs.append(f"IdxB: {field_comparison.idxB}")

        if field_comparison.explanation:
            field_strs.append(f"Explanation: {field_comparison.explanation}")

        typer.echo(", ".join(field_strs))

        for subfield_comparison in field_comparison.subfield_results or []:
            subfield_strs = [f"Codes: {subfield_comparison.code}"]
            subfield_strs.append(f"IdxA: {subfield_comparison.idxA}")
            subfield_strs.append(f"IdxB: {subfield_comparison.idxB}")

            if subfield_comparison.explanation:
                subfield_strs.append(
                    f"Explanation: {subfield_comparison.explanation}"
                )

            subfield_strs.append(f"Score: {subfield_comparison.score:.4f}")
            typer.echo("  " + ", ".join(subfield_strs))


def main():
    app()


if __name__ == "__main__":
    main()
