import yaml
from stagecoach.issue_manifest import issue_manifest
from stagecoach.manifest_checker import ManifestChecker
from sheriff.sheriff import Sheriff
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

class StageCoach:
    """
    Orchestrate Stagecoach workflows.

    Methods
    -------
    hail
        Create or partially fill a manifest.

    inspect
        Read and validate a manifest without moving data.

    stage
        Symlink or materialize declared data into project directories.
    """
    def __init__(
        self,
        sheriff: Sheriff | None = None,
        manifest_path: str | Path = "stagecoach_manifest.yml",
        console: Console | None = None,
    ) -> None:
        self.sheriff = sheriff or Sheriff()
        self.manifest_path = Path(manifest_path)
        self.console = console or Console()

    def hail(
        self,
        interactive: bool = True,
        overwrite: bool = False,
        sheriff: Sheriff | None = None,
        console: Console | None = None,
        manifest_path: str | Path | None = None,
    ) -> None:
        """Create a StageCoach manifest."""
        sheriff = sheriff or self.sheriff
        console = console or self.console
        manifest_path = Path(manifest_path) if manifest_path else self.manifest_path
        console.print(Panel.fit("🚂 Hailing the Stagecoach..", style="bold cyan"))

        issue_manifest(
            customs_sheriff=sheriff,
            interactive=interactive,
            output_path=manifest_path,
            overwrite=overwrite,
            console=console,
        )

    def inspect(
        self,
        console: Console | None = None,
    ) -> None:
        """Inspect a StageCoach manifest."""

        console = console or self.console
        console.print(Panel.fit("📋 Inspecting the manifest...", style="bold cyan"))
        checker = ManifestChecker(self.manifest_path)
        checks = checker.run_all()

        for result in checks:
            if result.passed:
                console.print(
                    f"- [bold green]{result.name} check passed:[/bold green] "
                    f"{result.message}"
                )
            else:
                console.print(
                    f"- [bold red]{result.name} check failed:[/bold red] "
                    f"{result.message}"
                )

        if not checker.passes():
            console.print("Manifest checks failed. Please review the results:")
            console.print(
                "- [bold red]See handbook for explanation of principles[/bold red] "
                "https://goldenplanetaryhealthlab.github.io/01_orientation/start-here.html#the-working-philosophy"
            )
            raise RuntimeError("Manifest checks failed. Please review the results.")

        manifest = yaml.safe_load(self.manifest_path.read_text())

        if manifest.get("remote", {}).get("globus", {}).get("use_globus"):
            console.print(
                "- [bold yellow]Globus access requested. Checking with the Sheriff...[/bold yellow]"
            )

            clearance = self.sheriff.issue_globus_transfer(
                globus_info=manifest.get("remote", {}).get("globus", {}),
                console=console,
                issue_transfer=False,
            )
            if clearance:
                console.print("- [bold green]Globus credentials validated![/bold green]")
            else:
                raise RuntimeError(
                    "Globus credentials validation failed. Please check your credentials."
                )
        

    def stage(self):
        pass
