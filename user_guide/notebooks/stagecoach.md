# StageCoach Explained


The stagecoach is a data ferrying system that automagically configures
how to get access to source data for your project. It is primarily
designed to be used in two ways:

1.  To get access to data on FASRC while developing on FASRC

2.  To get access to data on FASRC while developing on your local
    machine

To do this, stagecoach uses a manifest file that provides the user with
options for how to access the data. Once the user has made a selection,
stagecoach will try to set up the necessary access to the data, and when
ready, ferry ONLY what is needed to the user.

If you are on FASRC, this will likely be setting up a symbolic link to
the Gold Mine. If you are on your local machine, stagecoach will work
with you to access Globus and set up an economical, minimal — but secure
— transfer to get the data to you.

To get access to data, stagecoach will first ask you to select a
manifest file. This file is a YAML file that contains information about
the data and how to access it. The manifest file will also contain
information about the data dependencies for your project, and how to
access those dependencies. When you agree to a manifest, stagecoach will
read your manifest file and set up the necessary access to the data.
This may involve setting up a symbolic link to the Gold Mine, or it may
involve setting up a Globus transfer to get the data to you. Once you’ve
been authorized to access, the data will be ferried to your project
directory, and you can start working with it.

Here, we define the `stagecoach` class, while each of the methods are
defined in their own modules. There are three main methods that are
defined in the `stagecoach` class:

- `hail`: This is the first method that is called when you run
  `stagecoach` from the command line. It is responsible for creating the
  manifest file.

- `inspect`: This is the second step of staging, in which the
  `stagecoach` class reads the manifest file and checks that everything
  is in order. This is where we check that the user has access to the
  data, and that the data dependencies are met.

- `stage`: This is the final step of staging, in which the `stagecoach`
  class brings the data into the user’s environment. This is where we
  set up the symbolic link to the `Gold Mine`, or set up the Globus
  transfer to get the data to the user.

``` python
import yaml
from stagecoach.issue_manifest import issue_manifest
from stagecoach.manifest_checker import ManifestChecker
from sheriff.sheriff import Sheriff
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

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
        console.print(Panel.fit("🚂 Hailing the Stagecoach..", style="bold cyan"))

        issue_manifest(
            customs_sheriff=sheriff,
            interactive=interactive,
            output_path=manifest_path,
            overwrite=overwrite,
            console=console,
        )

    def inspect(
        self,
        console: Console | None = None,
    ) -> None:
        """Inspect a StageCoach manifest."""

        console = console or self.console
        console.print(Panel.fit("📋 Inspecting the manifest...", style="bold cyan"))
        checker = ManifestChecker(self.manifest_path)
        checks = checker.run_all()

        for result in checks:
            if result.passed:
                console.print(
                    f"- [bold green]{result.name} check passed:[/bold green] "
                    f"{result.message}"
                )
            else:
                console.print(
                    f"- [bold red]{result.name} check failed:[/bold red] "
                    f"{result.message}"
                )

        if not checker.passes():
            console.print("Manifest checks failed. Please review the results:")
            console.print(
                "- [bold red]See handbook for explanation of principles[/bold red] "
                "https://goldenplanetaryhealthlab.github.io/01_orientation/start-here.html#the-working-philosophy"
            )
            raise RuntimeError("Manifest checks failed. Please review the results.")

        manifest = yaml.safe_load(self.manifest_path.read_text())

        if manifest.get("remote", {}).get("globus", {}).get("use_globus"):
            console.print(
                "- [bold yellow]Globus access requested. Checking with the Sheriff...[/bold yellow]"
            )

            clearance = self.sheriff.issue_globus_transfer(
                globus_info=manifest.get("remote", {}).get("globus", {}),
                console=console,
                issue_transfer=False,
            )
            if clearance:
                console.print("- [bold green]Globus credentials validated![/bold green]")
            else:
                raise RuntimeError(
                    "Globus credentials validation failed. Please check your credentials."
                )
        

    def stage(self):
        pass
```

    Manifest checks passed!

Click on each section below to learn how stagecoach works in more
detail, and to see examples of how to use it.

1.  [Manifest File](#manifest-file)
