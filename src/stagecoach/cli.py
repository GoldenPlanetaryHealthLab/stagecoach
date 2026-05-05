from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from sheriff.sheriff import Sheriff
from stagecoach.issue_manifest import issue_manifest
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
    ) -> None:

    """
    Create a Stagecoach manifest.
    """

    # set up the printer
    console = Console()
    
    # create a sheriff to check citizenship, sorta like going through customs!
    customs_sheriff = Sheriff()

    console.print(Panel.fit("🚛 Hailing the Stagecoach", style="bold cyan"))
    try:
        issue_manifest(
            sheriff=customs_sheriff,
            interactive=interactive,
            output_path=str(output_path),
        )

    except Exception as exc:
        console.print(f"[red]✖ {exc}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
