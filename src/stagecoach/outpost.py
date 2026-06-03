from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
import os
import yaml


@contextmanager
def create_outpost(
    *,
    mode: str = "outpost",
    frontier_dirname: str = "frontier",
    frontier_file: str = "frontier.yml",
):
    """
    Create a temporary mock Frontier file and point THE_FRONTIER at it.

    This does not grant access to real Frontier resources. It only satisfies
    Sheriff's file-based citizenship check for commands that need to run
    outside the assigned Frontier, such as `stagecoach hail --outpost`.
    """
    old_the_frontier = os.environ.get("THE_FRONTIER")

    with TemporaryDirectory(prefix="stagecoach-outpost-") as tmp:
        root = Path(tmp)
        frontier_root = root / frontier_dirname
        frontier_root.mkdir(parents=True, exist_ok=True)

        frontier_path = frontier_root / frontier_file

        mock_frontier = {
            "frontier": {
                "mode": mode,
                "kind": "mock",
                "created_by": "stagecoach.forger",
                "purpose": "temporary citizenship scaffold",
            }
        }

        frontier_path.write_text(
            yaml.safe_dump(mock_frontier, sort_keys=False),
            encoding="utf-8",
        )

        os.environ["THE_FRONTIER"] = str(frontier_path)

        try:
            yield frontier_path
        finally:
            if old_the_frontier is None:
                os.environ.pop("THE_FRONTIER", None)
            else:
                os.environ["THE_FRONTIER"] = old_the_frontier
