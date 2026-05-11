from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from sheriff.sheriff import Sheriff
from stagecoach.stagecoach import StageCoach
import typer

app = typer.Typer(
    name="stagecoach",
    help="Stage authorized Frontier data into reproducible working environments.",
)

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

    # set up the printer
    console = Console()
    
    # create a sheriff to check citizenship, sorta like going through customs!
    customs_sheriff = Sheriff()

    try:
        StageCoach(
            sheriff = customs_sheriff,
            manifest_path=output_path).hail(
            interactive=interactive,
            overwrite=overwrite
        )

    except Exception as exc:
        console.print(f"[red]✖ {exc}[/red]")
        raise typer.Exit(code=1)


@app.command()
def inspect(
    manifest_path: Path = typer.Option(
        Path("stagecoach_manifest.yml"),
        "--manifest",
        "-m",
        help="Path to the manifest to inspect.",
    )
    )-> None:
    """
    Inspect a Stagecoach manifest.
    """
    
    # set up the printer
    console = Console()
    
    # create a sheriff to check citizenship, sorta like going through customs!
    customs_sheriff = Sheriff()

    try:
        StageCoach(
            sheriff = customs_sheriff,
            manifest_path=output_path,
            console=console).inspect()
    except Exception as exc:
        console.print(f"[red]✖ {exc}[/red]")
        raise typer.Exit(code=1)


@app.command()
def stage():
    
    # set up the printer
    console = Console()
    
    # create a sheriff to check citizenship, sorta like going through customs!
    customs_sheriff = Sheriff()

    # try:
    #     StageCoach(
    #         sheriff = customs_sheriff,
    #         manifest_path=output_path).stage(
    #         console=console
    #     )

    # except Exception as exc:
    #     console.print(f"[red]✖ {exc}[/red]")
    #     raise typer.Exit(code=1)
    pass


if __name__ == "__main__":
    app()
