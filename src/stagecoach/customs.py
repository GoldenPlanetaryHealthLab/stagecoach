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
    with UserApp(
        "Frontier-Stagecoach",
        client_id="7723dff4-fa63-4639-903b-ba6541e24e98",
        config=GlobusAppConfig(auto_redrive_gares=True),
    ) as app:
        with TransferClient(app=app) as client:
            yield client


from dataclasses import dataclass, field
from typing import Any
from rich.console import Console

@dataclass
class Clearance:
    """
    Result of a Stagecoach source access check.
    """
    
    source: str
    cleared: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

def check_globus_clearance(
    globus_info: dict
    ) -> Clearance:
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
    globus_info: dict,
    clearance: Clearance
    ) -> TransferData:
    if not clearance.cleared:
        raise ValueError(f"Cannot build transfer: clearance failed with message: {clearance.message}")
    transfer = TransferData(
        source_endpoint=globus_info["source_endpoint"],
        destination_endpoint=globus_info["destination_endpoint"],
        label="Stagecoach transfer",
    )

    for item in globus_info["items"]:
        transfer.add_item(
            item["source_path"],
            item["destination_path"],
            recursive=item.get("recursive", True),
        )

    return transfer


import glob

def check_gold_mine_clearance(
    gold_mine_info: dict
    ) -> Clearance:

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
