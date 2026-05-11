# Command Line Interface


To run stagecoach, we define a simple CLI using the `typer` library.
This allows users to run stagecoach from the command line, and provides
a nice interface for specifying options.

Once the CLI is defined as “hailing” the stagecoach, stagecoach will run
`issue_manifest` to create the manifest, and then proceed with the rest
of the stagecoach.

``` python
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
```

``` python
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
```

``` python
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
```

``` python
if __name__ == "__main__":
    app()
```
