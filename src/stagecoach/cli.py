from pathlib import Path
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from typing import Annotated
from sheriff.sheriff import Sheriff
from stagecoach.stagecoach import StageCoach
from stagecoach.checks import Severity, PRINCIPLES
from stagecoach.ui import failure_panel
import typer

app = typer.Typer(
    name="stagecoach",
    help="Stage authorized Frontier data into reproducible working environments.",
)

class FailureLevel(str, Enum):
    WARNING = "warning"
    ERROR = "error"

@app.command()
def hail(
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        help="Prompt for manifest fields interactively.",
    ),
    output_path: Path = typer.Option(
        Path("stagecoach_manifest.yml"),
        "--output",
        "-o",
        help="Where to write the manifest.",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite/--no-overwrite",
        help="Whether to overwrite an existing manifest.",
    ),
) -> None:
    """
    Create a Stagecoach manifest.
    """

    console = Console()
    customs_sheriff = Sheriff(console)

    try:
        StageCoach(
            sheriff=customs_sheriff,
            manifest_path=output_path,
            console=console,
        ).hail(
            interactive=interactive,
            overwrite=overwrite,
        )

    except Exception as exc:
        failure_panel(console, str(exc))
        raise typer.Exit(code=1)


@app.command()
def inspect(
    manifest_path: Path = typer.Option(
        Path("stagecoach_manifest.yml"),
        "--manifest",
        "-m",
        help="Path to the manifest to inspect.",
    ),
    level: Annotated[
        FailureLevel,
        typer.Option(
            "--level",
            "-l",
            help="Minimum severity that causes the manifest check to fail.",
            case_sensitive=False,
        ),
    ] = FailureLevel.ERROR,

) -> None:
    """
    Inspect a Stagecoach manifest.
    """

    console = Console()
    customs_sheriff = Sheriff(console)

    try:
        passed = StageCoach(
            sheriff=customs_sheriff,
            manifest_path=manifest_path,
            console=console,
        ).inspect(
            level=Severity(level.value),
        )

    except Exception as exc:
        failure_panel(console, str(exc))
        raise typer.Exit(code=1)
    if not passed:
        raise typer.Exit(code=1)


@app.command()
def stage():
    console = Console()
    customs_sheriff = Sheriff(console)
    pass


if __name__ == "__main__":
    app()
