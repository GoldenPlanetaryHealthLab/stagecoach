import yaml
from stagecoach.issue_manifest import issue_manifest
from stagecoach.manifest_checker import ManifestChecker
from stagecoach.customs import GlobusClearance, issue_globus_transfer
from stagecoach.checks import Severity
from sheriff.sheriff import Sheriff
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

from stagecoach.ui import (
    banner,
    success,
    warning,
    error,
    info,
    failure_panel,
    handbook_note,
    check_result,
)

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
        
        banner(console, "🚂 Hailing the Stagecoach...")

        issue_manifest(
            customs_sheriff=sheriff,
            interactive=interactive,
            output_path=manifest_path,
            overwrite=overwrite,
            console=console,
        )

        banner(console, f"Manifest created at: {manifest_path}. Fill it out and then run `stagecoach inspect` to check it!")

    def inspect(
        self,
        console: Console | None = None,
        level: Severity = Severity.ERROR
    ) -> None:
        """Inspect a StageCoach manifest."""

        console = console or self.console
        banner(console, f"📋 Inspecting manifest at level: {level.value}")
        
        checker = ManifestChecker(self.manifest_path, level)
        checks = checker.run_all()

        manifest = yaml.safe_load(self.manifest_path.read_text())

        if manifest.get("remote", {}).get("globus", {}).get("use_globus"):
            info(console, "Globus access requested. Checking with customs...")

            clearance = issue_globus_transfer(
                globus_info=manifest.get("remote", {}).get("globus", {}),
                console=console,
                issue_transfer=False,
            )
            if clearance.cleared:
                success(console, "Globus credentials validated.")
            else:
                error(
                    console,
                    "Globus credentials validation failed. Please check your credentials.",
                )
                console.print(clearance)

                return False

        for result in checks:
            check_result(console, result)

        if not checker.passes():
            console.print()
            error(console, "Manifest checks failed. Please review the results above.")
            handbook_note(console)

            return False
        
        console.print()
        success(console, "Manifest checks passed.")
        
        return True
        

    def stage(self):
        pass
