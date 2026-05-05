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

Now that we know that the user is a citizen, we can check that they are
working in a designated [`town`](#TODO%20create%20town%20documentation).

Finally, we can implement the manifest. It’s going to be simple for now,
but what it really needs to know is where IT is, and where the data is,
and figure out how to get the data to the user’s specified location.

<div class="sorting-hat-collapsed">

<details><summary>PYTHON code (click to expand)</summary>

<div class="cell-collapsed">

``` python
from pyprojroot import here
import os
import yaml

manifest = {
    "frontier": {
        # the name of the frontier may be used in future
        "name": "golden-lab",
        # the version may be used in future
        "schema_version": 1.0,

        # critical: we must know where the frontier starts
        "root": "/n/holylabs/cgolden_lab/Lab/frontier"
    },
    "paths": {
        # this is the general structure of the frontier
        "goldmine": "goldmine",
        "works": "works",
        "town": "town",
        "governance": "governance"
    },
    # we only have two compute options for now, but this may expand in the future
    "remote": {
        "globus": {
            # globus credentials for ferrying data to and from the frontier; only necessary if you want to ferry data to and from the frontier via globus
            "use_globus": False,
            "globus_username": None,
            "globus_endpoint": None
        }
    },
    # FILL IN THE BELOW SECTIONS WITH THE NECESSARY INFORMATION TO GET ACCESS TO THE DATA
    "citizen": {

        # your name must match your name in town
        "name": None,

        # email may be used in future for authentications
        "email": None
    },

    "project": {
        # this must match the name of your project repository
        "project_name": None,

        # must match above
        "project_working_dir": str(here()),

        # this is the name of the folder that stagecoach will ferry 
        # your input data to
        "input_data_dir": str(here() / "data" / "inputs"),

        # this is the name of the folder that stagecoach
        # will ferry your output data from;
        # only necessary if you want to ferry output data back to the frontier,
        # eg via globus
        "output_data_dir": str(here() / "data" / "outputs"),
    }
}

yaml_manifest = yaml.dump(manifest)

output_path = here() / "src" / "stagecoach" / "templates" / "manifest.yml"

with open(output_path, "w") as f:
    f.write(yaml_manifest)
```

</div>

</details>

</div>

If a citizen can pass the citizenship check, then the stagecoach can
issue a manifest which the user can fill in with the necessary
information to get access to the data. The manifest is a yaml file in
the `src/stagecoach` directory, so to expose it to the user, we can
create a simple function that writes the manifest to the file system.

``` python
from importlib.resources import files

def load_template():
    """
    Load the manifest template from the package resources.
    """
    template_path = files("stagecoach.templates").joinpath("manifest.yml")

    content = template_path.read_text()

    return yaml.safe_load(content)
```

This function makes use of the `importlib.resources` module, and so long
as the user’s version of `stagecoach` is up to date, the above YAML will
be the template they receive.

Next, to actually issue the manifest, we can create a function that
checks citizenship and then writes the manifest to the file system. This
function can be called from the command line, or from a notebook, or
from anywhere else.

We use `questionary` to make the function interactive, but it can also
be used in a non-interactive way by passing the necessary information as
arguments.

``` python
import questionary

from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from sheriff.sheriff import Sheriff

console = Console()

def issue_manifest(
    customs_sheriff: Sheriff,
    interactive: bool = True,
    output_path: str = str(here() / "stagecoach_manifest.yml")
    ) -> None:
    """
    Generate a Stagecoach manifest.
    This function validates Frontier citizenship, loads a template manifest,
    optionally fills it interactively, and writes the result to disk.

    Parameters
    ----------
    sheriff
        Sheriff instance used to validate Frontier citizenship.

    interactive
        Whether to prompt the user for manifest fields.

    output_path
        Destination path for the generated manifest.
    """
    
    console.print("[bold]Checking citizenship...[/bold]")
    citizen_ok = customs_sheriff.check_citizen()
    if not citizen_ok:
        raise RuntimeError(
            "You are not a citizen of the Frontier. "
            "Please check your citizenship and try again."
        )
    console.print("[green]✔ Citizenship verified[/green]\n")

    console.print("[bold]Loading manifest template...[/bold]")
    manifest = load_template()
    console.print("[green]✔ Template loaded[/green]\n")
    
    if interactive:
        
        # citizen
        citizen_name = questionary.text("Citizen name (Your name as it appears in town): ").ask()
        citizen_email = questionary.text("Citizen email (optional): ").ask()

        # project
        project_name = questionary.text("Project name: ").ask()
        project_working_dir = questionary.text(
            "Project working directory: ",
            default = str(here())
            ).ask()
        input_data_dir = questionary.text("Input data directory (relative to project working directory): ", default = "data/inputs").ask()
        output_data_dir = questionary.text("Output data directory (relative to project working directory, optional): ", default = "data/outputs").ask()

        use_globus = questionary.confirm("Use Globus for transport?", default = False).ask()

        if use_globus:
            globus_username = questionary.text("Globus username: ").ask()
            globus_endpoint = questionary.text("Globus endpoint: ").ask()
    
    # apply answers to manifest
    manifest["citizen"]["name"] = citizen_name
    manifest["citizen"]["email"] = citizen_email
    manifest["project"]["project_working_dir"] = project_working_dir
    manifest["project"]["input_data_dir"] = input_data_dir
    manifest["project"]["output_data_dir"] = output_data_dir

    if use_globus:
        manifest["remote"]["use_globus"] = True
        manifest["remote"]["globus_username"] = globus_username
        manifest["remote"]["globus_endpoint"] = globus_endpoint

    output_path_Path = Path(output_path)

    if output_path_Path.exists():
        overwrite = questionary.confirm(
            f"{output_path_Path} already exists. Overwrite?",
            default=False,
        ).ask()

        if not overwrite:
            raise Exception(f"Manifest not written: {output_path_Path} already exists.")

    output_path_Path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold]Writing manifest to:[/bold] {output_path_Path}")

    console.print(f"[bold]Writing manifest to:[/bold] {output_path_Path}")
    with console.status("[bold green]Saving manifest..."):
        with output_path_Path.open("w") as f:
            yaml.dump(manifest, f, sort_keys=False)
    
    console.print("[green]✔ Manifest created successfully[/green]\n")

    console.print(
        Panel.fit(
            "Next step:\n[bold]stagecoach stage[/bold]",
            title="Ready to Ride",
            style="bold green",
        )
    )
```

Issuing a manifest writes the manifest to the file system, where the
user can modify the necessary bits and pieces to ensure they have
correct access to the Gold Mine.

Next, check out the CLI module to see how we “hail,” a stagecoach.
