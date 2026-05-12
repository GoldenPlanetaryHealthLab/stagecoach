import yaml
from pathlib import Path
from stagecoach.checks import *

class ManifestChecker:
    """
    Check whether a project directory satisfies minimum Frontier expectations.
    The checker is intentionally lightweight.
    Each check returns a structured result that Stagecoach can display
    nicely in `stagecoach inspect`.
    """
    def __init__(self, manifest_file: str | Path, severity_level: Severity):
        self.manifest =  yaml.safe_load(Path(manifest_file).read_text())
        self.project_dir = self.manifest['project']['project_working_dir']
        self.severity_level = severity_level

    def run_all(self) -> list[CheckResult]:
        """
        Run all manifest checks.
        """

        return [
            check_project_exists(Path(self.project_dir)),
            check_git_repo_exists(Path(self.project_dir)),
            check_readme_exists(Path(self.project_dir)),
            check_environment_exists(Path(self.project_dir)),
            check_code_exists(Path(self.project_dir)),
            check_narrative_exists(Path(self.project_dir)),
            check_project_structure(Path(self.project_dir))
        ]

    def passes(self) -> bool:
        """
        Return True if no check result is at or above the configured
        severity threshold.

        If severity_level is Severity.ERROR, warnings are allowed.
        If severity_level is Severity.WARNING, warnings and errors fail.
        """

        results = self.run_all()
        threshold = SEVERITY_RANK[self.severity_level]

        return all(
            SEVERITY_RANK[check_result.state] < threshold
            for check_result in results
        )
