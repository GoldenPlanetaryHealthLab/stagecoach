import yaml
from stagecoach.issue_manifest import issue_manifest
from stagecoach.manifest_checker import ManifestChecker
from stagecoach.customs import Clearance, check_globus_clearance, build_globus_transfer
from stagecoach.checks import Severity
from stagecoach.stage import create_stage_directories, stage_data_from_fasrc, stage_data_from_globus, StageResult
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
    ) -> bool:
        """Create a StageCoach manifest."""
        sheriff = sheriff or self.sheriff
        console = console or self.console
        manifest_path = Path(manifest_path) if manifest_path else self.manifest_path
        
        banner(console, "🚂 Hailing the Stagecoach...")

        banner(console, "The stagecoach manifest is a YAML file that describes the data sources for your project and how to access them. You can create a manifest interactively, or stagecoach will provide a template manifest and you will fill in the details. The manifest will also include information about the data dependencies for your project, and how to access those dependencies.")

        issue_manifest(
            customs_sheriff=sheriff,
            interactive=interactive,
            output_path=manifest_path,
            overwrite=overwrite,
            console=console,
        )

        banner(console, f"✅ Manifest created at: {manifest_path}. Fill it out and then run `stagecoach inspect` to check it!")

        return True

    def inspect(
        self,
        console: Console | None = None,
        level: Severity = Severity.ERROR
    ) -> bool:
        """Inspect a StageCoach manifest."""

        console = console or self.console
        banner(console, f"📋 Inspecting manifest at level: {level.value}")
        
        checker = ManifestChecker(self.manifest_path, level)
        checks = checker.run_all()

        for result in checks:
            check_result(console, result)

        manifest = yaml.safe_load(self.manifest_path.read_text())

        # check gold mine access
        if manifest.get("sources", {}).get("01_gold_mine", {}).get("enabled"):
            info(console, "Gold Mine access requested. Checking with customs...")
            gold_mine_info = manifest.get("sources", {}).get("01_gold_mine", {})
            gold_mine_items = gold_mine_info.get("items", [])
            for item in gold_mine_items:
                item_name = item.get("name", "Unnamed Item")
                item_path = item.get("path_regex", "No path provided")
                # if not Path(item_path).exists() or 

        # check globus
        if manifest.get("sources", {}).get("02_globus", {}).get("enabled"):
            info(console, "Globus access requested. Checking with customs...")

            globus_info = manifest.get("sources", {}).get("02_globus", {})

            clearance = check_globus_clearance(
                globus_info=globus_info
                )
            
            if clearance.cleared:
                success(console, "Globus credentials validated.")
            else:
                error(
                    console,
                    "Globus credentials validation failed. Please check your credentials.",
                )
                console.print(clearance)
                raise ValueError("Globus credentials validation failed.")
        # check dataverse
        if manifest.get("sources", {}).get("03_dataverse", {}).get("enabled"):
            info(console, "Dataverse access requested. Checking with customs...")
            warning(console, "Dataverse access checks are not yet implemented. Please ensure you have access to the Dataverse dataset before proceeding.")

        if not checker.passes():
            console.print()
            banner(console, "⚠️ Manifest checks failed. Please review the results above.")
            handbook_note(console)

            return False
        
        console.print()
        banner(console, "✅ Manifest checks passed, you're cleared for staging! Run `stagecoach stage` to bring the data into your environment.")
        
        return True
        

    def stage(
        self,
        console: Console | None = None,
    ) -> bool:
        
        """Stage data according to a StageCoach manifest."""
        console = console or self.console
        banner(console, "🚂 Staging the data...")

        manifest = yaml.safe_load(self.manifest_path.read_text())

        # create stage directories
        create_stage_directories(manifest, console, gitignore=True)

        # fasrc
        fasrc = manifest.get("sources", {}).get("01_gold_mine", {})
        if fasrc['enabled']:
            fasrc_stageresult = stage_data_from_fasrc(manifest, console)
            if fasrc_stageresult.staged:
                success(console, "Gold Mine data staged successfully.")
            else:
                error(console, f"Gold Mine staging failed: {fasrc_stageresult.message}")
        
        # globus
        globus = manifest.get("sources", {}).get("02_globus", {})
        if globus['enabled']:
            globus_stageresult = stage_data_from_globus(manifest, console)
            if globus_stageresult.staged:
                success(console, "Globus data staged successfully.")
            else:
                error(console, f"Globus staging failed: {globus_stageresult.message}")

        # dataverse
        dataverse = manifest.get("sources", {}).get("03_dataverse", {})
        if dataverse['enabled']:
            warning(console, "Dataverse staging is not yet implemented. Please stage the data manually and place it in the appropriate directory.")
            dataverse_stageresult = StageResult(
                source="03_dataverse",
                staged=True,
                message="Dataverse staging is not yet implemented.",
            )
        else:
            dataverse_stageresult = StageResult(
                source="03_dataverse",
                staged=True,
                message="Dataverse staging not requested.",
            )
        
        final_staging = all(
            result.staged
            for result in [fasrc_stageresult, globus_stageresult, dataverse_stageresult]
        )

        if final_staging:
            banner(console, "🪎 All data staged successfully! You're ready to start working!")
            return True
        else:
            error(console, "Some data sources failed to stage. Please review the messages above and address any issues in your manifest.")

            banner(console, "⚠️ Staging failed. Please try again.")
            return False
