from pathlib import Path
from enum import Enum
from rich.console import Console
from typing import Annotated
from sheriff.sheriff import Sheriff
from stagecoach.stagecoach import StageCoach
from stagecoach.checks import Severity
from stagecoach.ui import failure_panel
import typer

app = typer.Typer(
    name="stagecoach",
    help="Stage authorized Frontier data into reproducible working environments.",
)

class FailureLevel(str, Enum):
    """
    Severity thresholds exposed by the CLI.

    Attributes
    ----------
    WARNING : str
        Treat warnings as command failures.
    ERROR : str
        Treat only errors as command failures.
    """
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

    Parameters
    ----------
    interactive : bool, default=True
        Whether to prompt for manifest fields interactively.
    output_path : Path, default=Path("stagecoach_manifest.yml")
        Destination path for the generated manifest.
    overwrite : bool, default=False
        Whether to overwrite an existing manifest file.
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

    Parameters
    ----------
    manifest_path : Path, default=Path("stagecoach_manifest.yml")
        Path to the manifest to validate.
    level : FailureLevel, default=FailureLevel.ERROR
        Minimum severity that should cause the command to exit with failure.
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
    """
    Stage data declared by the manifest.

    Returns
    -------
    None
        The command exits with a nonzero status when staging fails.
    """
    console = Console()
    customs_sheriff = Sheriff(console)
    staged = StageCoach(
        sheriff=customs_sheriff,
        console=console,
    ).stage()
    if not staged:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
