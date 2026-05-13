# import yaml
# from pathlib import Path
# from pprint import pprint
# from pyprojroot import here

# manifest = yaml.safe_load(Path(here() / "stagecoach_manifest.yml").read_text())
# pprint(manifest['sources'])


from globus_sdk import GlobusAppConfig, TransferClient, UserApp, TransferData
from contextlib import contextmanager

@contextmanager
def globus_transfer_client():
    """
    Yield an authenticated Globus transfer client.

    Yields
    ------
    TransferClient
        Transfer client configured for the Frontier Stagecoach app.
    """
    with UserApp(
        "Frontier-Stagecoach",
        client_id="7723dff4-fa63-4639-903b-ba6541e24e98",
        config=GlobusAppConfig(auto_redrive_gares=True),
    ) as app:
        with TransferClient(app=app) as client:
            yield client


from dataclasses import dataclass, field
from typing import Any

@dataclass
class Clearance:
    """
    Represent the outcome of a source access check.

    Attributes
    ----------
    source : str
        Source identifier being validated.
    cleared : bool
        Whether access validation succeeded.
    message : str, default=""
        Human-readable summary of the validation result.
    details : dict[str, Any]
        Source-specific metadata captured during validation.
    """
    
    source: str
    cleared: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

def check_globus_clearance(
    globus_info: dict
    ) -> Clearance:
    """
    Validate access to Globus endpoints and requested source paths.

    Parameters
    ----------
    globus_info : dict
        Manifest subsection describing Globus endpoints and staged items.

    Returns
    -------
    Clearance
        Clearance result describing whether Globus access checks passed.
    """
    try:
        with globus_transfer_client() as client:
            client.get_endpoint(globus_info["source_endpoint"])
            client.get_endpoint(globus_info["destination_endpoint"])
            for item in globus_info["items"]:
                client.operation_stat(
                    globus_info["source_endpoint"],
                    path=item["source_path"],
                )

        return Clearance(
            source="02_globus",
            cleared=True, 
            message="Globus clearance passed.",
            details={
                    "source_endpoint": globus_info["source_endpoint"],
                    "destination_endpoint": globus_info["destination_endpoint"],
                    "items_checked": len(globus_info["items"])
                }
            )

    except Exception as exc:
        return Clearance(
            source="02_globus",
            cleared=False,
            message=str(exc),
            details={
                "source_endpoint": globus_info.get("source_endpoint"),
                "destination_endpoint": globus_info.get("destination_endpoint"),
            }
        )


def build_globus_transfer(
    manifest: dict,
    clearance: Clearance,
    fix_holylabs: bool = True,
    label: str = "Stagecoach transfer",
    ) -> TransferData:
    """
    Build a Globus transfer request from manifest settings.

    Parameters
    ----------
    globus_info : dict
        Manifest subsection describing Globus endpoints and staged items.
    clearance : Clearance
        Successful clearance result for the same Globus configuration.
    fix_holylabs : bool, default=True
        Whether to apply Holylabs-specific path fix to the transfer (removes redundant LAB segment from paths).
    label: str, optional
        Optional label for the transfer task.

    Returns
    -------
    TransferData
        Transfer request populated with all requested items.

    Raises
    ------
    ValueError
        Raised when ``clearance`` indicates that access checks failed.
    """
    globus_info = manifest.get("sources", {}).get("02_globus", {})

    if not globus_info:
        raise ValueError("Globus information is missing from the manifest.")

    if not clearance.cleared:
        raise ValueError(f"Cannot build transfer: clearance failed with message: {clearance.message}")
    
    transfer = TransferData(
        source_endpoint=globus_info["source_endpoint"],
        destination_endpoint=globus_info["destination_endpoint"],
        label=label,
    )

    for item in globus_info["items"]:
        
        source_path = item["source_path"].replace("/n/holylabs/LABS/", "/n/holylabs/") if fix_holylabs else item["source_path"]
        destination_root = manifest["project"]["input_data_dir"].replace("/n/holylabs/LABS/", "/n/holylabs/") if fix_holylabs else manifest["project"]["input_data_dir"]
        destination_path = Path(destination_root) / "02_globus" / item['name'] / Path(source_path).name
        
        transfer.add_item(
            str(source_path),
            str(destination_path),
            recursive=item.get("recursive", True),
        )

    return transfer


import glob
import os
from pathlib import Path

def check_gold_mine_clearance(
    gold_mine_info: dict
    ) -> Clearance:
    """
    Validate readability of requested Gold Mine paths on FASRC.

    Parameters
    ----------
    gold_mine_info : dict
        Manifest subsection describing Gold Mine staging items.

    Returns
    -------
    Clearance
        Clearance result describing whether all required paths were found
        and were readable.
    """

    try:
        items = gold_mine_info.get("items", [])
        checked = []

        for item in items:
            name = item.get("name", "unnamed")
            path_regex = item.get("path_regex")

            if not path_regex:
                return Clearance(
                    source="01_gold_mine",
                    cleared=False,
                    message=f"{name}: missing path_regex",
                )

            matches = [Path(p) for p in glob.glob(path_regex)]

            if not matches and item.get("required", True):
                return Clearance(
                    source="01_gold_mine",
                    cleared=False,
                    message=f"{name}: no matches for {path_regex}",
                )

            for match in matches:
                if not os.access(match, os.R_OK):
                    return Clearance(
                        source="01_gold_mine",
                        cleared=False,
                        message=f"{name}: path is not readable: {match}",
                    )

            checked.append(
                {
                    "name": name,
                    "path_regex": path_regex,
                    "matches": [str(p) for p in matches],
                }
            )

        return Clearance(
            source="01_gold_mine",
            cleared=True,
            message="Gold Mine clearance passed.",
            details={"items_checked": checked},
        )

    except Exception as exc:
        return Clearance(
            source="01_gold_mine",
            cleared=False,
            message=str(exc),
        )
