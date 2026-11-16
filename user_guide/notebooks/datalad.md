# Stage pinned DataLad datasets


DataLad staging consumes a published dataset without changing the
publisher’s store. A standalone clone lives in
`<input_data_dir>/04_datalad/<name>`; the project does not need to
become a DataLad superdataset or register submodules. Depot remains
responsible for publication and scientific validation.

Install the `datalad` CLI (tested with 1.4.1), Git, and `git-annex` in
the shell environment used to run Stagecoach. For example, install
git-annex through your system or cluster package manager and
`uv tool install datalad==1.4.1`. These executables are required only
when `04_datalad` is enabled. Credentials and storage permissions remain
the responsibility of DataLad and its transports. The initial supported
deployment is a local RIA store on Linux or macOS.

Add this section alongside any other sources in your manifest:

The name is a unique destination component. The dataset ID guards
against an alias pointing to another dataset; the full Git commit pins
the revision even when the publisher advances its main branch. `paths`
must be a nonempty list of literal dataset-relative files or
directories. A directory selects all tracked files below it. To retrieve
less, list `releases/v0.2.2/datapackage.json` and the desired resource
paths explicitly. Cloning still obtains Git metadata for the dataset,
including filenames and Git-managed files outside the selection.
Wildcards, parent traversal, ordinary symlinks, and selected subdatasets
are rejected. `get_source` is optional; when specified, retrieval uses
that remote exclusively. The Kiribati clone exposes its RIA content as
`goldmine-storage`.

Run `stagecoach inspect --manifest stagecoach_manifest.yml`, then
`stagecoach stage --manifest stagecoach_manifest.yml`. Inspection clones
only metadata into a temporary directory, checks identity, revision,
paths, and destination conflicts, and leaves the project’s data
directories untouched. It cannot guarantee that content is retrievable.
Staging creates a normal clone, checks out the commit detached,
retrieves the selection, and checks each file’s availability. Neither
operation writes to the RIA store deliberately; DataLad manages any
transport logging in accordance with store configuration.

Repeat staging to retrieve dropped content or resume a failed transfer.
An existing clone must have the expected identity and commit and a clean
worktree, including no untracked files. Stagecoach does not change an
existing clone’s revision, discard edits, unlock files, push data, or
use reckless cloning. When selected content is missing in an existing
clone, Stagecoach first uses
`datalad update --sibling origin --how fetch` to refresh availability
metadata. This does not advance the checked-out content commit. It
allows a retry to discover content published after an earlier failed
attempt. Use a new item name for a different revision. A clone
interrupted before its initial checkout may require manual inspection
before retrying. Keep analysis outputs in intermediates or outputs. Each
item is locked during staging on the local machine; do not rely on this
lock across hosts with incompatible shared filesystem locking.

JSON receipts are written atomically under
`<project_working_dir>/.stagecoach/receipts/`, outside the input
directory. They record the manifest SHA256, tool versions, requested and
observed dataset identity and commit, actual Git origin, selected file
inventory with Git blob IDs and annex keys, availability, and errors.
Interrupted attempts retain a `running` receipt; only verified attempts
become `success`. An optional item (`required: false`) may fail without
failing the command, but is recorded as failed in a `partial` receipt.
Invalid configuration always fails. Receipts contain paths and source
locations; apply the project’s data governance rules before sharing
them. Retain the manifest and appropriate receipts for provenance.

The source URL is explicit: Stagecoach does not scrape Depot’s HTML or
infer an off-cluster endpoint from a local path. Obtain the published
commit and approved source from Depot. Remote deployment and nested
datasets require separate validation before extending this
implementation.

The implementation uses the supported DataLad CLI with JSON result
records. Git plumbing provides the pinned tree inventory, including
files whose annex content is absent. Availability checks distinguish
those files from usable inputs. The notebook exports the following
module without executing transfers.

``` python
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
from tempfile import NamedTemporaryFile, TemporaryDirectory
from uuid import UUID, uuid4

from rich.console import Console

from stagecoach.customs import Clearance
from stagecoach.stage import StageResult
from stagecoach.ui import info, warning


SOURCE = "04_datalad"


def validate_datalad_manifest(manifest: dict) -> list[dict]:
    """Validate enabled DataLad items without requiring DataLad executables."""
    sources = manifest.get("sources", {})
    if not isinstance(sources, dict):
        raise ValueError("Manifest sources must be a mapping.")
    section = sources.get(SOURCE, {})
    if not isinstance(section, dict) or not isinstance(section.get("enabled", False), bool):
        raise ValueError("04_datalad must be a mapping with a boolean enabled field.")
    if not section.get("enabled", False):
        return []
    if section.keys() - {"enabled", "items"}:
        raise ValueError("Unknown 04_datalad section fields.")
    items = section.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Enabled 04_datalad requires a nonempty items list.")
    names = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each DataLad item must be a mapping.")
        if item.keys() - {"name", "source", "dataset_id", "revision", "paths", "get_source", "required"}:
            raise ValueError("Unknown DataLad item fields.")
        name = item.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
            raise ValueError("DataLad item names must be safe single directory names.")
        if name in names:
            raise ValueError(f"Duplicate DataLad item name: {name}")
        names.add(name)
        for field in ("source", "dataset_id", "revision"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip() or any(c in value for c in "\x00\n\r"):
                raise ValueError(f"{name}: {field} must be a nonempty string.")
        if item["source"].startswith("-"):
            raise ValueError(f"{name}: source cannot start with '-'.")
        try:
            UUID(item["dataset_id"])
        except ValueError as exc:
            raise ValueError(f"{name}: dataset_id must be a DataLad UUID.") from exc
        if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", item["revision"]):
            raise ValueError(f"{name}: revision must be a full lowercase Git commit hash.")
        if not isinstance(item.get("required", True), bool):
            raise ValueError(f"{name}: required must be boolean.")
        remote = item.get("get_source")
        if remote is not None and (
            not isinstance(remote, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", remote)
        ):
            raise ValueError(f"{name}: get_source must be a remote name.")
        paths = item.get("paths")
        if not isinstance(paths, list) or not paths:
            raise ValueError(f"{name}: paths must be a nonempty list.")
        for path in paths:
            if (
                not isinstance(path, str) or not path or path.startswith("-")
                or any(c in path for c in "\x00\n\r\\*?[]")
                or PurePosixPath(path).is_absolute()
                or any(p in ("", ".", "..", ".git") for p in path.split("/"))
            ):
                raise ValueError(f"{name}: paths must be literal relative files or directories: {path!r}")
    _locations(manifest)
    return items


def _locations(manifest: dict) -> tuple[Path, Path]:
    project = manifest.get("project", {})
    if not isinstance(project, dict):
        raise ValueError("DataLad staging requires a project mapping.")
    for field in ("project_working_dir", "input_data_dir"):
        if not isinstance(project.get(field), str) or not project[field].strip():
            raise ValueError(f"DataLad staging requires project.{field}.")
    inputs = Path(project["input_data_dir"]).resolve()
    state = Path(project["project_working_dir"]).resolve() / ".stagecoach"
    if state.resolve().is_relative_to(inputs.resolve()):
        raise ValueError("Stagecoach receipts must be outside the input data directory.")
    return inputs, state


def _run(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-3000:]
        raise RuntimeError(f"{args[0]} failed (exit {result.returncode}): {detail}")
    return result.stdout


def _git(repo: Path, *args: str) -> str:
    return _run(["git", "-C", str(repo), *args])


def _datalad(*args: str, cwd: Path | None = None) -> list[dict]:
    output = _run(["datalad", "-f", "json", *args], cwd=cwd)
    records = [json.loads(line) for line in output.splitlines() if line.strip()]
    failures = [r for r in records if r.get("status") in ("error", "impossible")]
    if failures:
        raise RuntimeError(f"DataLad reported failures: {json.dumps(failures)}")
    return records


def _versions() -> dict:
    missing = [name for name in ("git", "datalad", "git-annex") if shutil.which(name) is None]
    if missing:
        raise RuntimeError("DataLad staging requires executables on PATH: " + ", ".join(missing))
    try:
        stagecoach_version = version("stagecoach")
    except PackageNotFoundError:
        stagecoach_version = "unknown"
    return {
        "stagecoach": stagecoach_version,
        "git": _run(["git", "--version"]).strip(),
        "datalad": _run(["datalad", "--version"]).strip(),
        "git_annex": _run(["git-annex", "version", "--raw"]).strip(),
    }


def _destination(inputs: Path, name: str) -> Path:
    destination = inputs / SOURCE / name
    if destination.is_symlink() or not destination.resolve().is_relative_to(inputs.resolve()):
        raise ValueError(f"Unsafe DataLad destination: {destination}")
    return destination


def _inventory(repo: Path, item: dict, *, available: bool) -> list[dict]:
    tree = []
    for entry in _git(repo, "ls-tree", "-r", "-z", "--full-tree", "HEAD").split("\x00"):
        if entry:
            metadata, path = entry.split("\t", 1)
            mode, kind, blob = metadata.split()
            tree.append({"path": path, "mode": mode, "git_blob": blob})
    selected = {}
    for path in item["paths"]:
        matches = [r for r in tree if r["path"] == path or r["path"].startswith(path + "/")]
        if not matches:
            raise ValueError(f"Requested path is not tracked at the pinned commit: {path}")
        if any(r["mode"] == "160000" for r in matches):
            raise ValueError(f"Selected subdatasets are not supported: {path}")
        selected.update((r["path"], r.copy()) for r in matches)
    # Check ancestors as well: a request inside an uninstalled subdataset must fail.
    for record in tree:
        if record["mode"] == "160000" and any(
            p.startswith(record["path"] + "/") for p in item["paths"]
        ):
            raise ValueError(f"Selected subdatasets are not supported: {record['path']}")
    records = _datalad(
        "status", "-d", str(repo), "--annex", "availability", "--untracked", "no",
        "--", *item["paths"], cwd=repo,
    )
    status = {str(Path(r["path"]).relative_to(repo)): r for r in records if "path" in r}
    for path, record in selected.items():
        result = status.get(path)
        if result is None:
            raise RuntimeError(f"DataLad returned no status for selected file: {path}")
        target = repo / path
        key = result.get("key")
        if record["mode"] == "120000" and not key:
            raise ValueError(f"Selected ordinary symlinks are not supported: {path}")
        if target.is_symlink() and key and not target.resolve().is_relative_to(
            (repo / ".git" / "annex" / "objects").resolve()
        ):
            raise ValueError(f"Annex link escapes the local object store: {path}")
        record.update(annex_key=key, bytes=result.get("bytesize"), has_content=(
            bool(result.get("has_content")) if key else target.is_file()
        ))
        if available and (not record["has_content"] or not target.is_file() or not os.access(target, os.R_OK)):
            raise RuntimeError(f"Selected content is not locally readable: {path}")
    return [selected[p] for p in sorted(selected)]


def _examine(repo: Path, item: dict, observed: dict) -> None:
    if not (repo / ".git").is_dir() or (repo / ".git").is_symlink():
        raise ValueError(f"Destination must be a standalone DataLad clone: {repo}")
    if (repo / ".git/annex").is_symlink() or (repo / ".git/annex/objects").is_symlink():
        raise ValueError(f"Destination must have its own annex object store: {repo}")
    if Path(_git(repo, "rev-parse", "--show-toplevel").strip()).resolve() != repo.resolve():
        raise ValueError(f"Destination is not a dataset root: {repo}")
    observed["dataset_id"] = _git(
        repo, "config", "--blob", "HEAD:.datalad/config", "--get", "datalad.dataset.id"
    ).strip()
    observed["revision"] = _git(repo, "rev-parse", "HEAD").strip()
    observed["origin"] = _git(repo, "remote", "get-url", "origin").strip()
    if observed["dataset_id"] != item["dataset_id"]:
        raise ValueError(f"Dataset identity conflict at {repo}")
    if observed["revision"] != item["revision"]:
        raise ValueError(f"Revision conflict at {repo}; use a new item name for a different revision.")
    if _git(repo, "status", "--porcelain=v1", "--untracked-files=normal").strip():
        raise ValueError(f"Dataset has modified or untracked files: {repo}")
    remote = item.get("get_source")
    if remote and remote not in _git(repo, "remote").splitlines():
        raise ValueError(f"Requested content remote is not configured: {remote}")
    observed["files"] = _inventory(repo, item, available=False)


def _clone(item: dict, destination: Path) -> None:
    _datalad("clone", item["source"], str(destination))
    _git(destination, "checkout", "--detach", item["revision"])


def check_datalad_clearance(manifest: dict) -> Clearance:
    """Inspect pinned metadata and destination conflicts without retrieving content."""
    checks = []
    try:
        items = validate_datalad_manifest(manifest)
        if not items:
            return Clearance(SOURCE, True, "DataLad staging not requested.")
        versions = _versions()
        inputs, _ = _locations(manifest)
        for item in items:
            record = {"name": item["name"], "required": item.get("required", True)}
            checks.append(record)
            try:
                destination = _destination(inputs, item["name"])
                if destination.exists():
                    _examine(destination, item, {})
                with TemporaryDirectory(prefix="stagecoach-inspect-") as tmp:
                    clone = Path(tmp) / "dataset"
                    _clone(item, clone)
                    _examine(clone, item, record)
                record["cleared"] = True
            except (OSError, ValueError, RuntimeError) as exc:
                record.update(cleared=False, error=str(exc))
        passed = all(r["cleared"] or not r["required"] for r in checks)
        return Clearance(SOURCE, passed, "Metadata inspection complete; content retrieval is checked during staging.", {
            "items": checks, "tools": versions,
        })
    except (OSError, ValueError, RuntimeError) as exc:
        return Clearance(SOURCE, False, str(exc), {"items": checks})


def _write_receipt(directory: Path, path: Path, receipt: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", dir=directory, prefix=".receipt-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(receipt, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _item_lock(state: Path, name: str):
    import fcntl

    directory = state / "locks"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / f"{name}.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Another staging process holds the lock for {name}.") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def stage_data_from_datalad(
    manifest: dict, console: Console, *, manifest_sha256: str | None = None
) -> StageResult:
    """Retrieve pinned selections and persist a receipt only marked successful after verification."""
    receipt = {
        "schema_version": 1, "source": SOURCE, "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(), "items": [],
        "manifest_sha256": manifest_sha256 or hashlib.sha256(
            json.dumps(manifest, sort_keys=True, default=str).encode()
        ).hexdigest(),
        "tools": {},
    }
    receipt_path = None
    try:
        inputs, state = _locations(manifest)
        directory = state / "receipts"
        receipt_path = directory / f"datalad-{uuid4().hex}.json"
        _write_receipt(directory, receipt_path, receipt)
        items = validate_datalad_manifest(manifest)
        if not items:
            receipt["status"] = "success"
        else:
            receipt["tools"] = _versions()
            for item in items:
                record = {
                    "name": item["name"], "required": item.get("required", True),
                    "requested": item.copy(), "status": "running", "observed": {},
                }
                receipt["items"].append(record)
                _write_receipt(directory, receipt_path, receipt)
                try:
                    with _item_lock(state, item["name"]):
                        destination = _destination(inputs, item["name"])
                        record["destination"] = str(destination)
                        reused = destination.exists()
                        if not reused:
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            info(console, f"Cloning DataLad metadata for {item['name']}...")
                            _clone(item, destination)
                        _examine(destination, item, record["observed"])
                        if reused and any(not f["has_content"] for f in record["observed"]["files"]):
                            info(console, f"Refreshing DataLad availability metadata for {item['name']}...")
                            record["metadata_refresh"] = _datalad(
                                "update", "-d", str(destination), "--sibling", "origin", "--how", "fetch",
                                cwd=destination,
                            )
                        _write_receipt(directory, receipt_path, receipt)
                        info(console, f"Retrieving pinned DataLad content for {item['name']}...")
                        args = ["get", "-d", str(destination)]
                        if item.get("get_source"):
                            args += ["--source", item["get_source"]]
                        record["retrieval"] = _datalad(*args, "--", *item["paths"], cwd=destination)
                        _examine(destination, item, record["observed"])
                        record["observed"]["files"] = _inventory(destination, item, available=True)
                        record["status"] = "success"
                except (OSError, ValueError, RuntimeError) as exc:
                    record.update(status="failed", error=str(exc))
                    if not record["required"]:
                        warning(console, f"Optional DataLad item {item['name']} failed: {exc}")
                _write_receipt(directory, receipt_path, receipt)
            failed = [r for r in receipt["items"] if r["status"] != "success"]
            receipt["status"] = "failed" if any(r["required"] for r in failed) else (
                "partial" if failed else "success"
            )
    except (OSError, ValueError, RuntimeError) as exc:
        receipt.update(status="failed", error=str(exc))
    receipt["finished_at"] = datetime.now(timezone.utc).isoformat()
    if receipt_path is not None:
        try:
            _write_receipt(receipt_path.parent, receipt_path, receipt)
            info(console, f"DataLad staging receipt: {receipt_path}")
        except OSError as exc:
            receipt.update(status="failed", error=f"Cannot persist staging receipt: {exc}")
    errors = [r["error"] for r in receipt["items"] if "error" in r]
    message = receipt.get("error") or "; ".join(errors) or "Selected DataLad content is locally available."
    return StageResult(SOURCE, receipt["status"] in ("success", "partial"), message, {
        "receipt": str(receipt_path) if receipt_path else None, "attempt": receipt,
    })
```
