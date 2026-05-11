# Manifest Checks


The goal of this module is simple: once the user has filled out the
manifest, we want to make sure all is compliant with the lab and
Frontier’s working philosophy. Only once this is done can the user then
run `stagecoach haul` to stage the data they requested in their
environment.

Validating a manifest is critical as it ensures that downstream data
access will be successful and/or fail gracefully with informative error
messages. This is the step where we check that the user has access to
the data they requested, and that the data dependencies they specified
are met. This is also the step where we check that the manifest is
compliant with the lab’s working philosophy, which is to only access
data that is necessary for the project, and to do so in a way that is
secure and reproducible.

We implement this using a series of checks against our [4 core
principles](https://goldenplanetaryhealthlab.github.io/01_orientation/start-here.html#the-working-philosophy):

1.  Always Strive for Remote and Reproducible Workflows 🌐

2.  Code is The Source of Truth 💎

3.  Analysis Should Be Narrated 📇

4.  Robust Habits Compound 🌱

To implement this test, we’ll first define a dataclass that will hold
the result of any given test. This will make it easy to generate a large
number of tests, and gather or manipulate the results in a standard
procedure.

``` python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"

PRINCIPLES = {
    1: "Remote and reproducible workflows 🌐",
    2: "Code is the source of truth 💎",
    3: "Analysis should be narrated 📇",
    4: "Robust habits compound 🌱"
}

@dataclass
class CheckResult:
    """
    Result from a single Stagecoach manifest check.
    """
    name: str
    passed: bool
    message: str
    principle: int | list[int]
    severity: Severity = Severity.ERROR
```

``` python
ex_check = CheckResult(
    name="Example Check",
    passed=True,
    message="This is an example check that passed.",
    principle=1,
    severity=Severity.ERROR
)

ex_check
```

And with that, we can propagate checks to any number of manifest fields.
In future, this may prove useful in enumerating checks across projects,
or in generating a manifest scorecard that can be used to track
improvements in project quality over time.

Now, let’s define a few checks:

``` python
def check_project_exists(directory: Path) -> CheckResult:
    if directory.exists() and directory.is_dir():
        return CheckResult(
            name="project_exists",
            passed=True,
            message=f"Project directory exists: {directory}",
            principle=1
        )
    return CheckResult(
        name="project_exists",
        passed=False,
        message=f"Project directory does not exist: {directory}",
        principle=1,
        severity=Severity.ERROR
    )

def check_git_repo_exists(directory: Path) -> CheckResult:
    if (directory / ".git").exists():
        return CheckResult(
            name="git_repo",
            passed=True,
            message="Project is under git version control.",
            principle=[1, 4]
        )

    return CheckResult(
        name="git_repo",
        passed=False,
        message="Project must be a git repository before data can be staged.",
        principle=[1, 4],
        severity=Severity.ERROR
    )

def check_environment_exists(directory: Path) -> CheckResult:
    candidates = [
        "rv.lock",
        "renv.lock",
        "environment.yml",
        "requirements.txt",
        "pyproject.toml",
        "uv.lock",
        "DESCRIPTION"
    ]
    found = [name for name in candidates if (directory / name).exists()]
    if found:
        return CheckResult(
            name="environment_spec_exists",
            passed=True,
            message=f"Environment specification found: {', '.join(found)}",
            principle=1
        )

    return CheckResult(
        name="environment_spec_exists",
        passed=False,
        message=(
            "Project needs a lockfile or environment specification, such as "
            "rv.lock, renv.lock, environment.yml, requirements.txt, "
            "pyproject.toml, uv.lock, or DESCRIPTION."
        ),
        principle=1,
        severity=Severity.ERROR
    )
```

To assert principle 2, we can simply check that there is at least one
code file in the project directory. This is a very basic check and will
only raise a warning, but it serves to illustrate the point, just in
case a user hasn’t yet started writing code:

``` python
def check_code_exists(directory: Path) -> CheckResult:
    patterns = [
        "**/*.py",
        "**/*.R",
        "**/*.Rmd",
        "**/*.qmd",
        "**/*.ipynb",
        "**/*.sh",
        "**/Snakefile",
        "**/_targets.R",
    ]

    ignored_parts = {
        ".git",
        ".venv",
        "renv",
        "rv",
        "__pycache__",
        ".quarto",
        "_site",
        "_targets",
        "node_modules",
    }
    
    files: list[Path] = []
    
    for pattern in patterns:
        files.extend(
            path
            for path in directory.glob(pattern)
            if not any(part in ignored_parts for part in path.parts)
        )
    if files:
        return CheckResult(
            name="analysis_code_exists",
            passed=True,
            message=f"Found {len(files)} script or notebook file(s).",
            principle=2,
        )

    return CheckResult(
        name="analysis_code_exists",
        passed=True,
        message=(
            "WARNING: Project must include code scripts or notebooks..."
        ),
        principle=2,
        severity=Severity.WARNING
    )
```

Principle 3 is similar to principle 2, but we check for the presence of
things like READMEs, notebooks, or markdown files:

``` python
def check_narrative_exists(directory: Path) -> CheckResult:

    patterns = [
        "**/*.qmd",
        "**/*.Rmd",
        "**/*.ipynb",
    ]

    ignored_parts = {
        ".git",
        ".venv",
        "renv",
        "rv",
        "__pycache__",
        ".quarto",
        "_site",
        "_targets",
        "node_modules",
    }
    files: list[Path] = []
    for pattern in patterns:
        files.extend(
            path
            for path in directory.glob(pattern)
            if not any(part in ignored_parts for part in path.parts)
        )

    if files:
        return CheckResult(
            name="notebook_exists",
            passed=True,
            message=f"Found {len(files)} narrated analysis file(s).",
            principle=3,
            severity=Severity.WARNING
        )

    return CheckResult(
        name="notebook_exists",
        passed=True,
        message=(
            "WARNING: Project should include narrated analysis using Quarto, "
            "Marimo, R Markdown, or Jupyter notebooks."
        ),
        principle=3,
        severity=Severity.WARNING
    )

def check_readme_exists(directory: Path) -> CheckResult:
    if (directory / "README.md").exists() or (directory / "README.Rmd").exists() or (directory / "README.qmd").exists():
        return CheckResult(
            name="readme_exists",
            passed=True,
            message="README.md file exists.",
            principle=3,
        )

    return CheckResult(
        name="readme_exists",
        passed=False,
        message=(
            "Project should include a README.md file that describes the project, "
            "data sources, and analysis plan."
        ),
        principle=3,
        severity=Severity.WARNING
    )
```

Finally, for principle 4, we’ll gently nudge the user to scaffold their
project using an R project file, or a Python project structure with a
`src` directory.

``` python
def check_project_structure(directory: Path) -> CheckResult:
    has_rproj = (directory / "project.Rproj").exists()
    has_src = (directory / "src").exists() and (directory / "src").is_dir()

    if has_rproj or has_src:
        return CheckResult(
            name="project_structure",
            passed=True,
            message="Project structure looks good.",
            principle=4,
        )

    return CheckResult(
        name="project_structure",
        passed=False,
        message=(
            "Project should be scaffolded using an R project file, or a Python "
            "project structure with a `src` directory."
        ),
        principle=4,
        severity=Severity.WARNING
    )
```

In the next module, we define the ManifestChecker class, which will run
all of these checks and more, and return a structured report that can be
displayed in `stagecoach inspect`.
