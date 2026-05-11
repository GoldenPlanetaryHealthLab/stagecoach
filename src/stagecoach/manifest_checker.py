import yaml
from pathlib import Path
from stagecoach.checks import *

class ManifestChecker():
    """
    Check whether a project directory satisfies minimum Frontier expectations.
    The checker is intentionally lightweight. It does not use pytest internally.
    Instead, each check returns a structured result that Stagecoach can display
    nicely in `stagecoach inspect`.
    """
    def __init__(self, manifest_file: str | Path):
        self.manifest =  yaml.safe_load(Path(manifest_file).read_text())
        self.project_dir = self.manifest['project']['project_working_dir']

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
        Return True if all error-level checks pass.
        """

        return all(
            result.passed
            for result in self.run_all()
            if result.severity == "error"
        )


from pyprojroot import here

manifest_checker = ManifestChecker(here() / "stagecoach_manifest.yml")
if manifest_checker.passes():
    print("Manifest checks passed!")
else:
    print("Manifest checks failed. Please review the results.")
