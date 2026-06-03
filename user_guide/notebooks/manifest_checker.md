# Manifest Checker Class


Here’s a manifest checker class that performs various checks on a
project directory based on a manifest file. Each check returns a
structured result that can be displayed nicely in `stagecoach inspect`.
The class also includes a method to determine if all error-level checks
pass.

``` python
import yaml
from pathlib import Path
from stagecoach.checks import *

class ManifestChecker:
    """
    Run the standard Stagecoach manifest checks for a project.

    Parameters
    ----------
    manifest_file : str | Path
        Path to the manifest file that defines the project directory.
    severity_level : Severity
        Minimum severity that should cause ``passes`` to return ``False``.

    Attributes
    ----------
    manifest : dict
        Parsed manifest contents.
    project_dir : str
        Project working directory declared by the manifest.
    severity_level : Severity
        Failure threshold used by ``passes``.
    """
    def __init__(self, manifest_file: str | Path, severity_level: Severity):
        self.manifest =  yaml.safe_load(Path(manifest_file).read_text())
        self.project_dir = self.manifest['project']['project_working_dir']
        self.severity_level = severity_level

    def run_all(self) -> list[CheckResult]:
        """
        Run all configured project checks.

        Returns
        -------
        list[CheckResult]
            Results from each Stagecoach project validation check.
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
        Determine whether the manifest passes the configured threshold.

        Returns
        -------
        bool
            ``True`` when every check result falls below
            ``self.severity_level`` and ``False`` otherwise.
        """

        results = self.run_all()
        threshold = SEVERITY_RANK[self.severity_level]

        return all(
            SEVERITY_RANK[check_result.state] < threshold
            for check_result in results
        )
```

So, to ensure that a manifest passes, we just issue:
