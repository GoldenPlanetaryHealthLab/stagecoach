import os
import re
import glob
from pathlib import Path
from stagecoach.ui import info, error, success, warning
from rich.console import Console


def create_stage_directories(manifest: dict, console: Console, gitignore=True):
    """
    Create the stage directories if they don't exist. 
    """
    
    input_dir = manifest.get("project", {}).get("input_data_dir")
    intermediate_dir = manifest.get("project", {}).get("intermediate_data_dir")
    output_dir = manifest.get("project", {}).get("output_data_dir")
    sandbox_dir = manifest.get("project", {}).get("sandbox_dir")

    paths = [input_dir, intermediate_dir, output_dir, sandbox_dir]

    for p in paths:
        if p is None:
            error(console, f"Stage directory {p} is not defined in the manifest.")
            raise ValueError("One or more stage directories are not defined in the manifest.")
        if not os.path.exists(p):
            os.makedirs(p)
            info(console, f"Created stage directory at {p}")
        else:
            info(console, f"Stage directory already exists at {p}")
        
        if gitignore:
            gitignore_path = Path(p) / ".gitignore"
            if not gitignore_path.exists():
                with open(gitignore_path, "w") as f:
                    f.write("*\n!.gitignore\n")
                info(console, f"Created .gitignore in {p}")
            else:
                info(console, f".gitignore already exists in {p}")
    
    success(console, "Stage directories are set up.")


from dataclasses import dataclass, field
from typing import Any

@dataclass
class StageResult:
    source: str
    staged: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


from stagecoach.customs import (
    Clearance, 
    check_globus_clearance, 
    build_globus_transfer,
    globus_transfer_client,

    check_gold_mine_clearance
) 

def stage_data_from_globus(
    manifest: dict,
    console: Console,
    issue_transfer: bool = True
) -> bool:
    """
    Stage data from Globus based on the manifest.
    """

    if not issue_transfer:
        info(console, "Globus clearance check passed. Skipping transfer as per configuration.")
        return StageResult(
            source="02_globus",
            staged=False,
            message="Globus clearance passed. Transfer skipped.",
        )

    globus_info = manifest.get("sources", {}).get("02_globus", {})
    if not globus_info:
        error(console, "No Globus information found in the manifest.")
        raise ValueError("Globus information is missing from the manifest.")
    clearance = check_globus_clearance(globus_info)
    transfer = build_globus_transfer(globus_info, clearance)
    try:
        with globus_transfer_client() as client:
            client.get_endpoint(globus_info["source_endpoint"])
            client.get_endpoint(globus_info["destination_endpoint"])
            task = client.submit_transfer(transfer)
            info(console, f"Globus transfer submitted with task ID: {task['task_id']}")

            return StageResult(
                source="02_globus",
                staged=True,
                message=f"Globus transfer submitted with task ID: {task['task_id']}",
                details=task,
            )
    except Exception as exc:
        error(console, f"Error during Globus staging: {exc}")
        return StageResult(
            source="02_globus",
            staged=False,
            message="Globus staging failed with transfer client error.",
            details=exc,
        )


from pathlib import Path
import glob
import os

def stage_data_from_fasrc(
    manifest: dict,
    console: Console,
) -> StageResult:
    fasrc_info = manifest.get("sources", {}).get("01_gold_mine", {})
    items = fasrc_info.get("items", [])

    task_list = {
        "succeeded": [],
        "failed": [],
        "skipped": [],
    }

    if not items:
        return StageResult(
            source="01_gold_mine",
            staged=False,
            message="No FASRC source items found in the manifest.",
            details=task_list,
        )

    try:
        input_root = Path(manifest["project"]["input_data_dir"])
        source_root = input_root / "01_gold_mine"
        source_root.mkdir(parents=True, exist_ok=True)

        for item in items:
            item_name = item.get("name")
            path_regex = item.get("path_regex")

            if not item_name or not path_regex:
                task_list["failed"].append(item)
                continue

            info(console, f"Staging Gold Mine item: {item_name}")

            item_stage_dir = source_root / item_name
            item_stage_dir.mkdir(parents=True, exist_ok=True)

            files_found = glob.glob(path_regex)

            if not files_found:
                warning(console, f"No files found matching pattern: {path_regex}")
                task_list["skipped"].append(path_regex)
                continue

            for source_path_raw in files_found:
                source_path = Path(source_path_raw).resolve()
                destination_path = item_stage_dir / source_path.name

                if destination_path.exists() or destination_path.is_symlink():
                    existing_target = None

                    if destination_path.is_symlink():
                        existing_target = Path(os.readlink(destination_path)).resolve()

                    if existing_target == source_path:
                        task_list["skipped"].append(str(source_path))
                        continue

                    task_list["failed"].append(str(source_path))
                    continue

                try:
                    os.symlink(
                        source_path,
                        destination_path,
                        target_is_directory=source_path.is_dir(),
                    )
                    task_list["succeeded"].append(str(source_path))

                except OSError:
                    task_list["failed"].append(str(source_path))

    except Exception as exc:
        return StageResult(
            source="01_gold_mine",
            staged=False,
            message=f"Gold Mine staging failed: {exc}",
            details=task_list,
        )

    staged = len(task_list["succeeded"]) > 0 or len(task_list["skipped"]) > 0
    failed = len(task_list["failed"]) > 0

    return StageResult(
        source="01_gold_mine",
        staged=staged and not failed,
        message=(
            "Symlink staging summary: "
            f"{len(task_list['succeeded'])} succeeded, "
            f"{len(task_list['skipped'])} skipped, "
            f"{len(task_list['failed'])} failed."
        ),
        details=task_list,
    )
