# `stagecoach`: A manifest-driven CLI for staging authorized data dependencies into reproducible local or remote working environments

`stagecoach` is a Python library that provides a manifest-driven CLI for staging authorized 
data dependencies into reproducible local or remote working environments. It is designed to 
help scientists and students in The Golden Planetary Health lab manage their project's 
dataset dependencies in a secure and efficient way, while also ensuring reproducibility and 
consistency across different environments.

## Installation

Use `uv` to install `stagecoach` as a tool:

```bash
uv tool install stagecoach
```

## Usage

Hail the `stagecoach`:

```
stagecoach hail
```

Modify your manifest, and inspect:

```
stagecoach inspect --manifest stagecoach_manifest.yaml
```

Stage your data:

```
stagecoach stage --manifest stagecoach_manifest.yaml
```

See the [docs](https://goldenplanetaryhealthlab.github.io/stagecoach/) for more details on how to use `stagecoach` and how to write your manifest file.

## DataLad staging

Enable `sources.04_datalad` to stage a published DataLad dataset at a pinned Git
commit. Stagecoach clones metadata, checks the dataset ID and commit, retrieves
only the requested annex content, and verifies local availability. Install the
`datalad` CLI and `git-annex` separately; they are not needed for other sources.
The initial supported deployment is a local RIA store on Linux or macOS.

Start with [the Kiribati manifest](examples/kiribati-biomarkers.yml), copy it into
your own project, and adjust the project paths and source as needed. Run from
the project root:

```bash
stagecoach inspect --manifest stagecoach_manifest.yml
stagecoach stage --manifest stagecoach_manifest.yml
```

The project must pass the existing Git/README checks before staging. DataLad
clones live under `data/inputs/04_datalad/<name>`; JSON provenance receipts live
under `.stagecoach/receipts/`. Repeating staging retrieves missing selected
content. Conflicting dataset identities, revisions, and local edits fail without
discarding the existing clone. See [the DataLad guide](notebooks/datalad.qmd) for
field definitions, optional-item behavior, and operational limits.

## Development

Implementation notebooks in `notebooks/` export Python modules through Quarto's
`sorting-hat` and `ripper` filters. Edit a notebook, then regenerate its module
and rendered guide without executing examples:

```bash
quarto render notebooks/datalad.qmd --no-execute
uv run --locked python -m unittest discover -s tests -v
```

The integration tests create synthetic RIA stores in temporary directories and
never access lab datasets. They require the DataLad CLI and git-annex, and are
skipped if those tools are absent; CI installs both and runs the full suite.
With authorized access to the Kiribati store, run the disposable acceptance check
explicitly. It retrieves the pinned release, verifies it, repeats staging, and
removes the temporary project without printing data:

```bash
STAGECOACH_TEST_KIRIBATI=1 uv run --locked python -m unittest discover -s tests -p test_kiribati.py -v
```
