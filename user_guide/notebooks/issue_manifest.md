# Manifest File


The manifest file is a YAML file that describes the terms of use for a
dataset. It includes some simple automated checks to ensure that your
project is compliant with the terms of use. The terms of use are as
follows:

- You must be a person in the frontier

- You must be working in the town of the frontier

- Your project must have a git repository

- Your project must have a name and a description

This is easily translatable to a couple of simple checks.

First, we import the `Sheriff` class from the `sheriff` module. Then, we
create an instance of the `Sheriff` class and call the `check_citizen`
method to perform the checks.

If the sheriff verifies citizenship, the checks will pass.

``` python
from rich.console import Console
from sheriff.sheriff import Sheriff

def check_citizenship(customs_sheriff: Sheriff, console: Console) -> None:
    """
    Validate Frontier citizenship through the sheriff.

    Parameters
    ----------
    customs_sheriff : Sheriff
        Sheriff instance used to verify citizenship.
    console : Console
        Rich console used for progress messages.

    Raises
    ------
    RuntimeError
        Raised when the sheriff does not validate the current user.
    """

    info(console, "Checking citizenship...")

    if not customs_sheriff.check_citizen():
        raise RuntimeError(
            "You are not a citizen of the Frontier. "
            "Please check your citizenship and try again."
        )

    success(console, "Citizenship verified")
```

We can see this function in action below:

``` python
# mysheriff = Sheriff()

# check_citizenship(mysheriff)
```

Now that we know that the user is a citizen, we can check that they are
working in a designated [`town`](#TODO%20create%20town%20documentation).

Next, we can implement the manifest. It’s going to be simple for now,
but what it really needs to know is where IT is, and where the data is,
and figure out how to get the data to the user’s specified location.

``` python
# we don't export this portion of script
# because it will cause side effects to anyone who
# loads it at runtime

# from pyprojroot import here

# manifest_template = {
#     "frontier": {
#         "name": "golden-lab",
#         "schema_version": 1.0,
#         "root": "/n/holylabs/cgolden_lab/Lab/frontier",
#     },

#     "paths": {
#         "goldmine": "goldmine",
#         "works": "works",
#         "town": "town",
#         "governance": "governance",
#     },

#     "citizen": {
#         "name": None,
#         "email": None,
#     },

#     "project": {
#         "project_name": None,
#         "project_working_dir": str(here()),
#         "input_data_dir": str(here() / "data" / "inputs"),
#         "intermediate_data_dir": str(here() / "data" / "intermediates"),
#         "output_data_dir": str(here() / "data" / "outputs"),
#         "sandbox_dir": str(here() / "sandbox"),
#     },

#     "sources": {
#         "01_gold_mine": {
#             "enabled": False,

#             # Each item stages into:
#             # <input_data_dir>/01_gold_mine/<name>/<basename>
#             "items": [
#                 {
#                     "name": "example_goldmine_item",
#                     "path_regex": None,
#                     "required": True,
#                 }
#             ],
#         },

#         "02_globus": {
#             "enabled": False,

#             # Globus collection UUIDs
#             "source_endpoint": None,
#             "destination_endpoint": None,

#             # Each item stages into:
#             # <input_data_dir>/02_globus/<name>/<basename>
#             "items": [
#                 {
#                     "name": "example_globus_item",
#                     "source_path": None,
#                     "destination_path": None,  # optional override
#                     "files_regex": [],
#                     "recursive": True,
#                     "required": True,
#                 }
#             ],
#         },

#         "03_dataverse": {
#             "enabled": False,

#             "server_url": None,
#             "dataset_pid": None,
#             "dataset_version": "latest",
#             "api_token_file": None,

#             # Each item stages into:
#             # <input_data_dir>/03_dataverse/<name>/<basename>
#             "items": [
#                 {
#                     "name": "example_dataverse_item",
#                     "files_regex": [],
#                     "required": True,
#                 }
#             ],
#         },
#     },
# }

# import yaml
# from pathlib import Path

# output_path = Path("src/stagecoach/templates/manifest.yml")
# output_path.parent.mkdir(parents=True, exist_ok=True)

# with output_path.open("w") as f:
#     yaml.dump(manifest_template, f, sort_keys=False)
```

If a citizen can pass the citizenship check, then the stagecoach can
issue a manifest which the user can fill in with the necessary
information to get access to the data. The manifest is a yaml file in
the `src/stagecoach` directory, so to expose it to the user, we can
create a simple function that writes the manifest to the file system.

``` python
import yaml
from typing import Any
from importlib.resources import files

def load_template() -> dict[str, Any]:
    """
    Load the packaged Stagecoach manifest template.

    Returns
    -------
    dict[str, Any]
        Parsed manifest template bundled with the package.
    """

    template_path = files("stagecoach.templates").joinpath("manifest.yml")
    return yaml.safe_load(template_path.read_text())
```

This function makes use of the `importlib.resources` module, and so long
as the user’s version of `stagecoach` is up to date, the above YAML will
be the template they receive.

Next, to actually issue the manifest, we can create a function that
prompts the user to fill in the necessary information. This is intended
to be the primary interface at the command line. This is made by two
subfunctions, `fill_manifest_interactively`, which prompts the user to
fill in the manifest fields, and `write_manifest`, which writes the
manifest to disk.

We use `questionary` to make the function interactive, but it can also
be used in a non-interactive way by passing the necessary information as
arguments.

``` python
import questionary
from typing import Any

def fill_manifest_interactively(manifest: dict[str, Any]) -> dict[str, Any]:
    """
    Prompt the user for manifest values at the command line.

    Parameters
    ----------
    manifest : dict[str, Any]
        Manifest template to populate in place.

    Returns
    -------
    dict[str, Any]
        Updated manifest containing the collected user input.
    """

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

    # use_globus = questionary.confirm(
    #     "Use Globus for transport?",
    #     default=False,
    # ).ask()

    # manifest.setdefault("citizen", {})
    # manifest.setdefault("project", {})
    # manifest.setdefault("source", {})
    # manifest["source"].setdefault("globus", {})
    manifest["citizen"]["name"] = citizen_name
    manifest["citizen"]["email"] = citizen_email
    manifest["project"]["project_name"] = project_name
    manifest["project"]["project_working_dir"] = project_working_dir
    manifest["project"]["input_data_dir"] = input_data_dir
    manifest["project"]["output_data_dir"] = output_data_dir

    # if use_globus:
    #     manifest["source"]["02_globus"]["globus_username"] = questionary.text(
    #         "Globus username:"
    #     ).ask()
    #     manifest["source"]["02_globus"]["globus_endpoint"] = questionary.text(
    #         "Globus endpoint:"
    #     ).ask()
    
    # if use_dataverse:
    #     manifest["source"]["03_dataverse"]["dataverse_server_url"] = questionary.text(
    #         "Dataverse server URL:"
    #     ).ask()
    #     manifest["source"]["03_dataverse"]["dataverse_dataset_pid"] = questionary.text(
    #         "Dataverse dataset PID:"
    #     ).ask()

    return manifest
```

In practice, this process looks like:

``` python
# mymanifest = load_template()

# filled_manifest = fill_manifest_interactively(mymanifest)
```

Next, writing the manifest should be straight forward:

``` python
from pathlib import Path
from rich.console import Console

def write_manifest(
    manifest: dict[str, Any],
    output_path: str | Path,
    console: Console,
    overwrite: bool = False
    ) -> None:
    """
    Write a manifest to disk as YAML.

    Parameters
    ----------
    manifest : dict[str, Any]
        Manifest data to serialize.
    output_path : str | Path
        Destination path for the YAML file.
    console : Console
        Rich console used for progress messages.
    overwrite : bool, default=False
        Whether to bypass the overwrite confirmation prompt.

    Raises
    ------
    RuntimeError
        Raised when the target file exists and overwrite is declined.
    """

    output_path = Path(output_path)

    if output_path.exists() and not overwrite:
        overwrite_confirmed = questionary.confirm(
            f"{output_path} already exists. Overwrite?",
            default=False,
        ).ask()

        if not overwrite_confirmed:
            raise RuntimeError(f"Manifest not written: {output_path} already exists.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    info(console, f"Writing manifest to: {output_path}")
    with console.status("[bold green]Saving manifest..."):
        with output_path.open("w") as f:
            yaml.dump(manifest, f, sort_keys=False)

    success(console, "Manifest created successfully")
```

To test:

``` python
# from tempfile import TemporaryDirectory

# with TemporaryDirectory() as tmpdir:
#     temp_manifest_path = Path(tmpdir) / "my_manifest.yml"
#     write_manifest(mymanifest, temp_manifest_path, overwrite=True)

#     # show contents of the file
#     with temp_manifest_path.open() as f:
#         print(f.read())
```

Looks great! We now have the pieces to issue a manifest:

``` python
from rich.console import Console
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
    Generate a Stagecoach manifest for a project.

    Parameters
    ----------
    customs_sheriff : Sheriff
        Sheriff instance used to validate Frontier citizenship.
    console : Console
        Rich console used for progress messages.
    interactive : bool, default=True
        Whether to prompt the user for manifest fields.
    output_path : str | Path, default=here() / "stagecoach_manifest.yml"
        Destination path for the generated manifest.
    overwrite : bool, default=False
        Whether to overwrite an existing manifest at the output path.

    Returns
    -------
    None
        This function is called for its side effect of writing the manifest.
    """

    check_citizenship(customs_sheriff, console)
    info(console, "Loading manifest template...")
    manifest = load_template()
    success(console, "Template loaded\n")

    if interactive:
        manifest = fill_manifest_interactively(manifest)

    write_manifest(manifest, output_path, overwrite=overwrite, console=console)

    success(console, "Next step: stagecoach inspect")
```

Issuing a manifest writes the manifest to the file system, where the
user can modify the necessary bits and pieces to ensure they have
correct access to the Gold Mine.

Next, check out the CLI module to see how we “hail,” a stagecoach.
