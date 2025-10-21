import asyncio
from enum import StrEnum
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import typer
from marcdantic import MarcRecord

from marc_comparator_sdk.validators.kramerius_links import (
    KrameriusLinksValidator,
)

app = typer.Typer(help="MARC Comparator CLI tool")


class Validator(StrEnum):
    KrameriusLinks = "kramerius-links"


VALIDATORS = {
    Validator.KrameriusLinks: KrameriusLinksValidator,
}


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
        return VALIDATORS[validator]()

    if not config_path.exists():
        typer.echo(f"Config file does not exist: {config_path}", err=True)
        typer.exit(1)

    if not config_path.is_file():
        typer.echo(f"Not a file: {config_path}", err=True)
        typer.exit(1)

    with config_path.open("r", encoding="utf-8") as f:
        config_data = f.read()

    validator_cls = VALIDATORS[validator]
    return validator_cls(
        validator_cls.config_model.model_validate_json(config_data)
    )


@app.command()
def validate(
    mrc_file_paths: List[Path] = typer.Argument(
        ..., help="Paths to MARC record files"
    ),
    validators: List[str] = typer.Option(
        [str(val) for val in VALIDATORS.keys()],
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


def main():
    app()


if __name__ == "__main__":
    main()
