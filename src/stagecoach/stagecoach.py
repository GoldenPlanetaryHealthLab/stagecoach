from stagecoach.issue_manifest import issue_manifest
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
    ) -> None:
        """Create a Stagecoach manifest."""

        self.console.print(Panel.fit("🚂 Hailing the Stagecoach", style="bold cyan"))
        issue_manifest(
            customs_sheriff=self.sheriff,
            interactive=interactive,
            output_path=self.manifest_path,
            overwrite=overwrite
        )

    def inspect(self):
        pass

    def stage(self):
        pass
