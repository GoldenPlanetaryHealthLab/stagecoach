"""Explicitly opt in to the private-store acceptance check; CI uses synthetic data."""

from copy import deepcopy
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from rich.console import Console
import yaml

from stagecoach.stagecoach import StageCoach


@unittest.skipUnless(os.environ.get("STAGECOACH_TEST_KIRIBATI") == "1", "opt-in private RIA acceptance check")
class KiribatiAcceptanceTest(unittest.TestCase):
    def test_published_release_can_be_staged_and_repeated(self):
        example = Path(__file__).resolve().parents[1] / "examples/kiribati-biomarkers.yml"
        manifest = yaml.safe_load(example.read_text())
        with TemporaryDirectory(prefix="stagecoach-kiribati-") as tmp:
            project = Path(tmp)
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            (project / "README.md").write_text("Temporary Kiribati staging acceptance check.\n")
            for field, relative in {
                "project_working_dir": ".", "input_data_dir": "data/inputs",
                "intermediate_data_dir": "data/intermediates", "output_data_dir": "data/outputs",
                "sandbox_dir": "sandbox",
            }.items():
                manifest["project"][field] = str(project / relative)
            path = project / "stagecoach_manifest.yml"
            path.write_text(yaml.safe_dump(manifest))
            console = Console(file=StringIO())
            coach = StageCoach(manifest_path=path, console=console)
            self.assertTrue(coach.inspect(), console.file.getvalue())
            self.assertFalse((project / "data").exists())
            self.assertTrue(coach.stage(), console.file.getvalue())
            receipts = project / ".stagecoach/receipts"
            first_path, = receipts.glob("*.json")
            first = json.loads(first_path.read_text())
            self.assertEqual(first["status"], "success")
            observed = first["items"][0]["observed"]
            item = manifest["sources"]["04_datalad"]["items"][0]
            self.assertEqual(observed["dataset_id"], item["dataset_id"])
            self.assertEqual(observed["revision"], item["revision"])
            self.assertEqual({f["path"] for f in observed["files"]}, {
                "releases/v0.2.2/biomarker_ptx.csv", "releases/v0.2.2/datapackage.json",
            })
            self.assertTrue(all(f["has_content"] and f["annex_key"] for f in observed["files"]))
            self.assertTrue(coach.stage(), console.file.getvalue())
            second_path, = set(receipts.glob("*.json")) - {first_path}
            second = json.loads(second_path.read_text())
            self.assertEqual(second["status"], "success")
            self.assertEqual(second["items"][0]["observed"], deepcopy(observed))
            # Emit identifiers only; never print rows or package metadata.
            print(f"Kiribati verified: {item['dataset_id']} @ {item['revision']}; two files, repeat successful.")


if __name__ == "__main__":
    unittest.main()
