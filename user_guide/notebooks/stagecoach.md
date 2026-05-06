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
from stagecoach.issue_manifest import issue_manifest
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
    ) -> None:
        """Create a Stagecoach manifest."""

        self.console.print(Panel.fit("🚂 Hailing the Stagecoach", style="bold cyan"))
        issue_manifest(
            customs_sheriff=self.sheriff,
            interactive=interactive,
            output_path=self.manifest_path,
            overwrite=overwrite
        )

    def inspect(self):
        pass

    def stage(self):
        pass
```

Click on each section below to learn how stagecoach works in more
detail, and to see examples of how to use it.

1.  [Manifest File](#manifest-file)
