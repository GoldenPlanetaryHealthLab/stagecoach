# Stagecoach: A CLI tool for Staging Analysis Data

Stage coach is a CLI tool for "staging" analysis
data to your project. It helps you organize and orchestrate input
data for your projects in a consistent, reproducible way, 
making it easy to scaffold your data science project. 
All of the configuration is done through a `stagecoach_manifest.yaml` 
file, which you can customize to fit your needs. 
Simply run `stagecoach hail` to request a manifest, edit it to source your,
data, and request the data to be staged with `stagecoach stage`. The tool
will run the necessary checks to ensure you have permission to access the 
data. Additionally, `stagecoach` gently promotes best practices for data 
management, such as symlinking source data, using R or Python projects,
using `git` for version control, `gitignore`-ing sensitive data,
and more! You can use the `stagecoach inspect` command to have it inspect 
your manifest and report any issues before you stage your data.

The best way to get `stagecoach` is to install it using `uv`.
First, make sure you have [`uv` installed](https://docs.astral.sh/uv/getting-started/installation/): 

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, [create a project](https://docs.astral.sh/uv/concepts/projects/init/#creating-a-minimal-project) that `uv` will isolate for you with a 
virtual environment:

```bash
uv init my-project
uv venv
```

Finally, you can install `stagecoach` to your virtual environment 
with the following command:

```bash
# by using tool install, you get this tool available as a command line tool
uv tool install  https://github.com/GoldenPlanetaryHealthLab/stagecoach/tree/2-Stage-Data
```

## Usage

First, hail a `stagecoach`:

```bash
stagecoach hail
```

If you are NOT part of a Frontier workspace,
you must use the `--outpost` flag to mock a
Frontier workspace. This flag was designed with
collaborators in mind who might not be on FASRC but still want to use `stagecoach` to stage data for their projects.

```bash
stagecoach hail --outpost
```

Following this command, you will be prompted to answer a few questions 
about your project and the data you want to stage.
This will help prefill a `stagecoach_manifest.yaml` file for you, which you 
can then edit to customize your data staging.

Once you've filled in the manifest, use the `stagecoach inspect` command to check for any issues with your manifest:

```bash
stagecoach inspect
```

If there are no issues, you can proceed to stage your data with the `stagecoach stage` command:

```bash
stagecoach stage
```

This will run the necessary checks to ensure you have permission to access 
the data, and then stage the data according to your manifest configuration.

Run `stagecoach [COMMAND] --help` to see more details about each command and its options.
