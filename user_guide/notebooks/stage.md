# Stage Data


Finally, it’s time to deliver the user’s data to them. In this module,
we define several staging methods that the stagecoach can use.

There are a couple of things that will need to happen to make this work.
One of them will be creating the directories for data usage:

``` python
from stagecoach.ui import info
from rich.console import Console
import os
```

``` python
def create_stage_directories(manifest: dict, console: Console, gitignore=True):
    """
    Create the stage directories if they don't exist. 
    """
    
    input_dir = manifest.get("project", {}).get("input_data_dir")
    intermediate_dir = manifest.get("project", {}).get("intermediate_data_dir")
    output_dir = manifest.get("project", {}).get("output_data_dir")
    sandbox_dir = manifest.get("project", {}).get("sandbox_dir")
    
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        info(console, f"Created input data directory at [bold]{input_dir}[/bold]")
    else:
        info(console, f"Input data directory already exists at [bold]{input_dir}[/bold]")
    
    if not os.path.exists(intermediate_dir):
        os.makedirs(intermediate_dir)
        info(console, f"Created intermediate data directory at [bold]{intermediate_dir}[/bold]")
    else:
        info(console, f"Intermediate data directory already exists at [bold]{intermediate_dir}[/bold]")

    if not os.path.exists(sandbox_dir):
        os.makedirs(sandbox_dir)
        info(console, f"Created sandbox directory at [bold]{sandbox_dir}[/bold]")
    else:
        info(console, f"Sandbox directory already exists at [bold]{sandbox_dir}[/bold]")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        info(console, f"Created output data directory at [bold]{output_dir}[/bold]")
    else:
        info(console, f"Output data directory already exists at [bold]{output_dir}[/bold]")

    # if gitignore:
    #     paths = [''.join('.gitignore') for dir in [input_dir, intermediate_dir, output_dir, sandbox_dir]]
    #     gitignore_path = os.path.join(sandbox_dir, ".gitignore")
    #     if not os.path.exists(gitignore_path):
    #         with open(gitignore_path, "w") as f:
    #             f.write("*\n")
    #         info(console, f"Created .gitignore in sandbox directory at [bold]{gitignore_path}[/bold]")
    #     else:
    #         info(console, f".gitignore already exists in sandbox directory at [bold]{gitignore_path}[/bold]")
```

# Script file

The code for this document can be found here:

- [../src/stagecoach/stage.py](../src/stagecoach/stage.py)
