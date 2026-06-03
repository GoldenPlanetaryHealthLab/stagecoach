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
