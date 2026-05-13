from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class Severity(Enum):
    """
    Severity levels for manifest validation results.

    Attributes
    ----------
    PASS : str
        The check succeeded.
    WARNING : str
        The check surfaced a non-blocking issue.
    ERROR : str
        The check found a blocking issue.
    """
    PASS = "pass"
    WARNING = "warning"
    ERROR = "error"

SEVERITY_RANK = {
    Severity.PASS: 0,
    Severity.WARNING: 1,
    Severity.ERROR: 2,
}

PRINCIPLES = {
    1: "Remote and reproducible workflows 🌐",
    2: "Code is the source of truth 💎",
    3: "Analysis should be narrated 📇",
    4: "Robust habits compound 🌱"
}

@dataclass
class CheckResult:
    """
    Represent the outcome of a single manifest check.

    Attributes
    ----------
    name : str
        Stable identifier for the check.
    state : Severity
        Severity assigned to the check result.
    message : str
        Human-readable explanation of the outcome.
    principle : int | list[int]
        Frontier principle number, or numbers, associated with the check.
    """
    name: str
    state: Severity
    message: str
    principle: int | list[int]


ex_check = CheckResult(
    name="Example Check",
    state=Severity.WARNING,
    message="This is an example check that passed with a warning.",
    principle=1
)

ex_check


def check_project_exists(directory: Path) -> CheckResult:
    """
    Verify that the project directory exists.

    Parameters
    ----------
    directory : Path
        Directory declared as the project working directory.

    Returns
    -------
    CheckResult
        Passes when ``directory`` exists and is a directory.
    """
    if directory.exists() and directory.is_dir():
        return CheckResult(
            name="project_exists",
            state=Severity.PASS,
            message=f"Project directory exists: {directory}",
            principle=1
        )
    return CheckResult(
        name="project_exists",
        state=Severity.ERROR,
        message=f"Project directory does not exist: {directory}",
        principle=1
    )

def check_git_repo_exists(directory: Path) -> CheckResult:
    """
    Verify that the project directory is under Git version control.

    Parameters
    ----------
    directory : Path
        Project directory to inspect.

    Returns
    -------
    CheckResult
        Passes when a ``.git`` directory is present.
    """
    if (directory / ".git").exists():
        return CheckResult(
            name="git_repo",
            state=Severity.PASS,
            message="Project is under git version control.",
            principle=[1, 4]
        )

    return CheckResult(
        name="git_repo",
        state=Severity.ERROR,
        message="Project must be a git repository before data can be staged.",
        principle=[1, 4]
    )

def check_environment_exists(directory: Path) -> CheckResult:
    """
    Look for a project environment specification or lockfile.

    Parameters
    ----------
    directory : Path
        Project directory to inspect.

    Returns
    -------
    CheckResult
        Passes when at least one supported environment file exists and
        warns otherwise.
    """
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
            state=Severity.PASS,
            message=f"Environment specification found: {', '.join(found)}",
            principle=1
        )

    return CheckResult(
        name="environment_spec_exists",
        state=Severity.WARNING,
        message=(
            "Project needs a lockfile or environment specification, such as "
            "rv.lock, renv.lock, environment.yml, requirements.txt, "
            "pyproject.toml, uv.lock, or DESCRIPTION."
        ),
        principle=1
    )


def check_code_exists(directory: Path) -> CheckResult:
    """
    Check whether the project contains analysis or source code files.

    Parameters
    ----------
    directory : Path
        Project directory to inspect recursively.

    Returns
    -------
    CheckResult
        Passes when at least one supported code or notebook file is found
        outside ignored directories.
    """
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
            state=Severity.PASS,
            message=f"Found {len(files)} script or notebook file(s).",
            principle=2,
        )

    return CheckResult(
        name="analysis_code_exists",
        state=Severity.WARNING,
        message=(
            "WARNING: Project must include code scripts or notebooks..."
        ),
        principle=2
    )


def check_narrative_exists(directory: Path) -> CheckResult:
    """
    Check whether the project contains narrated analysis notebooks.

    Parameters
    ----------
    directory : Path
        Project directory to inspect recursively.

    Returns
    -------
    CheckResult
        Passes when Quarto, R Markdown, or Jupyter notebooks are present
        outside ignored directories.
    """

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
            state=Severity.PASS,
            message=f"Found {len(files)} narrated analysis file(s).",
            principle=3
        )

    return CheckResult(
        name="notebook_exists",
        state=Severity.WARNING,
        message=(
            "WARNING: Project should include narrated analysis using Quarto, "
            "Marimo, R Markdown, or Jupyter notebooks."
        ),
        principle=3
    )

def check_readme_exists(directory: Path) -> CheckResult:
    """
    Check whether the project contains a top-level README document.

    Parameters
    ----------
    directory : Path
        Project directory to inspect.

    Returns
    -------
    CheckResult
        Passes when a supported README filename exists and errors
        otherwise.
    """
    if (directory / "README.md").exists() or (directory / "README.Rmd").exists() or (directory / "README.qmd").exists() or (directory / "README").exists():
        return CheckResult(
            name="readme_exists",
            state=Severity.PASS,
            message="README file found.",
            principle=3,
        )

    return CheckResult(
        name="readme_exists",
        state=Severity.ERROR,
        message=(
            "Project should include a README.md file that describes the project, "
            "data sources, and analysis plan."
        ),
        principle=3
    )


def check_project_structure(directory: Path) -> CheckResult:
    """
    Check for a minimal project scaffold.

    Parameters
    ----------
    directory : Path
        Project directory to inspect.

    Returns
    -------
    CheckResult
        Passes when the project contains either an R project file or a
        Python-style ``src`` directory.
    """
    has_rproj = (directory / "project.Rproj").exists()
    has_src = (directory / "src").exists() and (directory / "src").is_dir()

    if has_rproj or has_src:
        return CheckResult(
            name="project_structure",
            state=Severity.PASS,
            message="Project structure looks good.",
            principle=4,
        )

    return CheckResult(
        name="project_structure",
        state=Severity.WARNING,
        message=(
            "Project should be scaffolded using an R project file, or a Python "
            "project structure with a `src` directory."
        ),
        principle=4
    )
