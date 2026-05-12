from rich.console import Console
from sheriff.sheriff import Sheriff

def check_citizenship(customs_sheriff: Sheriff, console: Console) -> None:
    """Validate Frontier citizenship using the Sheriff."""

    console.print("[bold]Checking citizenship...[/bold]")

    if not customs_sheriff.check_citizen():
        raise RuntimeError(
            "You are not a citizen of the Frontier. "
            "Please check your citizenship and try again."
        )

    console.print("[green]✔ Citizenship verified[/green]\n")


# mysheriff = Sheriff()

# check_citizenship(mysheriff)


# we don't export this portion of script
# because it will cause side effects to anyone who
# loads it at runtime
# from pyprojroot import here
# import os
# import yaml

# manifest = {
#     "frontier": {
#         # the name of the frontier may be used in future
#         "name": "golden-lab",
#         # the version may be used in future
#         "schema_version": 1.0,

#         # critical: we must know where the frontier starts
#         "root": "/n/holylabs/cgolden_lab/Lab/frontier"
#     },
#     "paths": {
#         # this is the general structure of the frontier
#         "goldmine": "goldmine",
#         "works": "works",
#         "town": "town",
#         "governance": "governance"
#     },
#     # we only have two compute options for now, but this may expand in the future
#     "remote": {
#         "globus": {
#             # globus credentials for ferrying data to and from the frontier; only necessary if you want to ferry data to and from the frontier via globus
#             "use_globus": False,
#             "globus_username": None,
#             "globus_source_endpoint": None,
#             "globus_source_path": None,
#             "globus_destination_endpoint": None,
#             "globus_destination_path": None
#         }
#     },
#     # FILL IN THE BELOW SECTIONS WITH THE NECESSARY INFORMATION TO GET ACCESS TO THE DATA
#     "citizen": {

#         # your name must match your name in town
#         "name": None,

#         # email may be used in future for authentications
#         "email": None
#     },

#     "project": {
#         # this must match the name of your project repository
#         "project_name": None,

#         # must match above
#         "project_working_dir": str(here()),

#         # this is the name of the folder that stagecoach will ferry 
#         # your input data to
#         "input_data_dir": str(here() / "data" / "inputs"),

#         # this is the name of the folder that stagecoach
#         # will ferry your output data from;
#         # only necessary if you want to ferry output data back to the frontier,
#         # eg via globus
#         "output_data_dir": str(here() / "data" / "outputs"),
#     }
# }

# yaml_manifest = yaml.dump(manifest)

# output_path = here() / "src" / "stagecoach" / "templates" / "manifest.yml"

# with open(output_path, "w") as f:
#     f.write(yaml_manifest)


import yaml
from typing import Any
from importlib.resources import files

def load_template() -> dict[str, Any]:
    """Load the packaged Stagecoach manifest template."""

    template_path = files("stagecoach.templates").joinpath("manifest.yml")
    return yaml.safe_load(template_path.read_text())


import questionary
from typing import Any

def fill_manifest_interactively(manifest: dict[str, Any]) -> dict[str, Any]:

    """Prompt the user and fill in manifest fields."""

    citizen_name = questionary.text(
        "Citizen name (Your name as it appears in Town):"
    ).ask()

    citizen_email = questionary.text("Citizen email (optional):").ask()

    project_name = questionary.text("Project name:").ask()

    project_working_dir = questionary.text(
        "Project working directory:",
        default=str(here()),
    ).ask()

    input_data_dir = questionary.text(
        "Input data directory:",
        default=str(Path(project_working_dir) / "data" / "inputs"),
    ).ask()

    output_data_dir = questionary.text(
        "Output data directory:",
        default=str(Path(project_working_dir) / "data" / "outputs"),
    ).ask()

    use_globus = questionary.confirm(
        "Use Globus for transport?",
        default=False,
    ).ask()

    manifest.setdefault("citizen", {})
    manifest.setdefault("project", {})
    manifest.setdefault("remote", {})
    manifest["remote"].setdefault("globus", {})
    manifest["citizen"]["name"] = citizen_name
    manifest["citizen"]["email"] = citizen_email
    manifest["project"]["project_name"] = project_name
    manifest["project"]["project_working_dir"] = project_working_dir
    manifest["project"]["input_data_dir"] = input_data_dir
    manifest["project"]["output_data_dir"] = output_data_dir
    manifest["remote"]["globus"]["use_globus"] = use_globus

    if use_globus:
        manifest["remote"]["globus"]["globus_username"] = questionary.text(
            "Globus username:"
        ).ask()
        manifest["remote"]["globus"]["globus_endpoint"] = questionary.text(
            "Globus endpoint:"
        ).ask()

    return manifest


# mymanifest = load_template()

# filled_manifest = fill_manifest_interactively(mymanifest)


import questionary
from pathlib import Path
from rich.console import Console

def write_manifest(
    manifest: dict[str, Any],
    output_path: str | Path,
    console: Console,
    overwrite: bool = False
    ) -> None:
    """Write a manifest to disk."""

    output_path = Path(output_path)

    if output_path.exists() and not overwrite:
        overwrite_confirmed = questionary.confirm(
            f"{output_path} already exists. Overwrite?",
            default=False,
        ).ask()

        if not overwrite_confirmed:
            raise RuntimeError(f"Manifest not written: {output_path} already exists.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    console.print(f"[bold]Writing manifest to:[/bold] {output_path}")
    with console.status("[bold green]Saving manifest..."):
        with output_path.open("w") as f:
            yaml.dump(manifest, f, sort_keys=False)

    console.print("[green]✔ Manifest created successfully[/green]\n")


# from tempfile import TemporaryDirectory

# with TemporaryDirectory() as tmpdir:
#     temp_manifest_path = Path(tmpdir) / "my_manifest.yml"
#     write_manifest(mymanifest, temp_manifest_path, overwrite=True)

#     # show contents of the file
#     with temp_manifest_path.open() as f:
#         print(f.read())


from rich.console import Console
from rich.panel import Panel
from stagecoach.ui import info, success
from sheriff.sheriff import Sheriff
from pyprojroot import here

def issue_manifest(
    customs_sheriff: Sheriff,
    console: Console,
    interactive: bool = True,
    output_path: str | Path = here() / "stagecoach_manifest.yml",
    overwrite: bool = False
) -> None:

    """
    Generate a Stagecoach manifest.
    This function validates Frontier citizenship, loads a template manifest,
    optionally fills it interactively, and writes the result to disk.

    Parameters
    ----------
    customs_sheriff
        Sheriff instance used to validate Frontier citizenship.

    interactive
        Whether to prompt the user for manifest fields.

    output_path
        Destination path for the generated manifest.
    
    overwrite
        Whether to overwrite an existing manifest at the output path.
    """

    check_citizenship(customs_sheriff, console)
    info(console, "[bold]Loading manifest template...[/bold]")
    manifest = load_template()
    info(console, "[green]✔ Template loaded[/green]\n")

    if interactive:
        manifest = fill_manifest_interactively(manifest)

    write_manifest(manifest, output_path, overwrite=overwrite, console=console)

    success(console, "Next step:\n[bold]stagecoach inspect[/bold]")
