"""DataLad staging contract, tested without access to lab data."""

from copy import deepcopy
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from rich.console import Console
from typer.testing import CliRunner
import yaml

import stagecoach.datalad as adapter
from stagecoach.cli import app
from stagecoach.stagecoach import StageCoach


DATASET_ID = "98c72378-28b0-47a3-9b00-a6d746e31c63"


def manifest_for(project: Path) -> dict:
    return {
        "project": {
            "project_name": "test", "project_working_dir": str(project),
            "input_data_dir": str(project / "data/inputs"),
            "intermediate_data_dir": str(project / "data/intermediates"),
            "output_data_dir": str(project / "data/outputs"),
            "sandbox_dir": str(project / "sandbox"),
        },
        "sources": {"04_datalad": {"enabled": True, "items": [{
            "name": "example", "source": "/unavailable/source", "dataset_id": DATASET_ID,
            "revision": "1" * 40, "paths": ["releases/v1"], "get_source": "goldmine-storage",
            "required": True,
        }]}},
    }


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix="stagecoach-unit-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = manifest_for(self.root)
        self.console = Console(file=StringIO())

    def test_bad_fields_and_paths_are_rejected_before_commands(self):
        bad_fields = [
            ("name", "../escape"), ("name", ".git"), ("name", ""),
            ("source", "--help"), ("source", None), ("dataset_id", "not-an-id"),
            ("revision", "main"), ("revision", "1234"), ("required", "false"),
            ("get_source", "--help"), ("paths", []), ("paths", "file.csv"),
            ("files_regex", ["*.csv"]),
        ]
        bad_fields += [("paths", [p]) for p in (
            "", ".", "..", "/etc/passwd", "../secret", "release/../../secret",
            ".git/config", "release/.git/config", "*.csv", "a?", "a[b]", "a//b",
            "a/./b", "a/", "a\\b", "-a", "a\nb",
        )]
        with patch.object(adapter, "_run", side_effect=AssertionError("command executed")):
            for field, value in bad_fields:
                with self.subTest(field=field, value=value):
                    manifest = deepcopy(self.manifest)
                    manifest["sources"]["04_datalad"]["items"][0][field] = value
                    with self.assertRaises(ValueError):
                        adapter.validate_datalad_manifest(manifest)

    def test_section_types_duplicates_and_receipt_location(self):
        for section in (None, [], {"enabled": "false"}, {"enabled": True, "items": []}):
            with self.subTest(section=section):
                self.manifest["sources"]["04_datalad"] = section
                with self.assertRaises(ValueError):
                    adapter.validate_datalad_manifest(self.manifest)
        self.manifest = manifest_for(self.root)
        items = self.manifest["sources"]["04_datalad"]["items"]
        items.append(items[0].copy())
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            adapter.validate_datalad_manifest(self.manifest)
        items.pop()
        self.manifest["project"]["input_data_dir"] = str(self.root)
        with self.assertRaisesRegex(ValueError, "outside"):
            adapter.validate_datalad_manifest(self.manifest)

    def test_missing_or_disabled_source_needs_no_tools(self):
        for sources in ({}, {"04_datalad": {"enabled": False}}):
            self.manifest["sources"] = sources
            with patch.object(adapter, "_versions", side_effect=AssertionError("tools checked")):
                self.assertTrue(adapter.check_datalad_clearance(self.manifest).cleared)

    def test_json_failure_record_is_failure_even_with_zero_exit(self):
        with patch.object(adapter, "_run", return_value='{"status": "impossible"}\n'):
            with self.assertRaisesRegex(RuntimeError, "failures"):
                adapter._datalad("get", "file")

    def test_selected_subdataset_is_rejected_before_content_commands(self):
        self.manifest["sources"]["04_datalad"]["items"][0]["paths"] = ["nested"]
        item = self.manifest["sources"]["04_datalad"]["items"][0]
        with patch.object(adapter, "_git", return_value=f"160000 commit {'1' * 40}\tnested\x00"), patch.object(
            adapter, "_datalad", side_effect=AssertionError("content command executed")
        ):
            with self.assertRaisesRegex(ValueError, "subdatasets"):
                adapter._inventory(self.root, item, available=False)

    def test_successful_get_without_content_is_not_staging_success(self):
        item = self.manifest["sources"]["04_datalad"]["items"][0]
        item["paths"] = ["data.csv"]
        tree = f"120000 blob {'1' * 40}\tdata.csv\x00"
        status = [{"path": str(self.root / "data.csv"), "key": "SHA256E-s1--abc.csv", "has_content": False}]
        with patch.object(adapter, "_git", return_value=tree), patch.object(adapter, "_datalad", return_value=status):
            with self.assertRaisesRegex(RuntimeError, "not locally readable"):
                adapter._inventory(self.root, item, available=True)

    def test_required_and_optional_failures_have_atomic_receipts(self):
        for required in (True, False):
            with self.subTest(required=required):
                self.manifest["sources"]["04_datalad"]["items"][0]["required"] = required
                with patch.object(adapter, "_versions", return_value={"datalad": "test"}), patch.object(
                    adapter, "_clone", side_effect=RuntimeError("content source unavailable")
                ):
                    result = adapter.stage_data_from_datalad(self.manifest, self.console)
                self.assertEqual(result.staged, not required)
                receipt = json.loads(Path(result.details["receipt"]).read_text())
                self.assertEqual(receipt["status"], "failed" if required else "partial")
                self.assertEqual(receipt["items"][0]["status"], "failed")
                self.assertEqual(len(receipt["manifest_sha256"]), 64)
                self.assertNotIn(".receipt-", result.details["receipt"])
                self.assertFalse(list(Path(result.details["receipt"]).parent.glob(".receipt-*")))

    def test_interruption_leaves_running_receipt_and_releases_lock(self):
        with patch.object(adapter, "_versions", return_value={}), patch.object(
            adapter, "_clone", side_effect=KeyboardInterrupt
        ):
            with self.assertRaises(KeyboardInterrupt):
                adapter.stage_data_from_datalad(self.manifest, self.console)
        receipt_path, = (self.root / ".stagecoach/receipts").glob("*.json")
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual(receipt["status"], "running")
        self.assertNotIn("finished_at", receipt)
        with adapter._item_lock(self.root / ".stagecoach", "example"):
            with self.assertRaisesRegex(RuntimeError, "lock"):
                with adapter._item_lock(self.root / ".stagecoach", "example"):
                    self.fail("concurrent staging must not proceed")

    def test_missing_executables_are_reported_and_receipted(self):
        with patch.object(adapter.shutil, "which", return_value=None):
            result = adapter.stage_data_from_datalad(self.manifest, self.console)
        self.assertFalse(result.staged)
        self.assertIn("executables on PATH", result.message)
        self.assertEqual(json.loads(Path(result.details["receipt"]).read_text())["status"], "failed")

    def test_preflight_blocks_staging_before_creating_directories(self):
        manifest_path = self.root / "manifest.yml"
        manifest_path.write_text(yaml.safe_dump(self.manifest))
        with patch("stagecoach.stagecoach.stage_data_from_datalad") as stage:
            self.assertFalse(StageCoach(manifest_path=manifest_path, console=self.console).stage())
        stage.assert_not_called()
        self.assertFalse((self.root / "data").exists())
        self.assertFalse((self.root / ".stagecoach").exists())

    def test_old_manifest_without_datalad_still_stages_without_tools(self):
        (self.root / ".git").mkdir()
        (self.root / "README.md").write_text("A project\n")
        self.manifest["sources"] = {}
        path = self.root / "manifest.yml"
        path.write_text(yaml.safe_dump(self.manifest))
        with patch.object(adapter, "_versions", side_effect=AssertionError("tools checked")):
            self.assertTrue(StageCoach(manifest_path=path, console=self.console).stage())

    def test_cli_reports_bad_manifest_without_traceback(self):
        path = self.root / "manifest.yml"
        path.write_text("project: null\n")
        for command in ("stage", "inspect"):
            with self.subTest(command=command):
                result = CliRunner().invoke(app, [command, "--manifest", str(path)])
                self.assertEqual(result.exit_code, 1)
                self.assertIn("project mapping", result.output)
                self.assertNotIn("Traceback", result.output)


TOOLS_AVAILABLE = all(shutil.which(t) for t in ("git", "datalad", "git-annex"))


@unittest.skipUnless(TOOLS_AVAILABLE, "requires DataLad CLI and git-annex")
class RIAIntegrationTests(unittest.TestCase):
    """A real RIA publisher and storage sibling, using synthetic bytes only."""

    @classmethod
    def command(cls, *args, cwd=None):
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"{args}: {result.stderr}\n{result.stdout}")
        return result.stdout.strip()

    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory(prefix="stagecoach-ria-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        # Keep DataLad discovery inside the fixture, even if /tmp has a Git parent.
        cls.command("git", "init", "-q", str(cls.root))
        identity = patch.dict(os.environ, {
            "GIT_AUTHOR_NAME": "Stagecoach Tests", "GIT_AUTHOR_EMAIL": "stagecoach@example.invalid",
            "GIT_COMMITTER_NAME": "Stagecoach Tests", "GIT_COMMITTER_EMAIL": "stagecoach@example.invalid",
        })
        identity.start()
        cls.addClassCleanup(identity.stop)
        cls.publisher = cls.root / "publisher"
        cls.command("datalad", "create", str(cls.publisher))
        release = cls.publisher / "releases/v1"
        release.mkdir(parents=True)
        (release / "data.csv").write_text("value\n1\n")
        (release / "datapackage.json").write_text('{"name": "synthetic", "resources": []}\n')
        (cls.publisher / "unselected.csv").write_text("private_to_another_analysis\n2\n")
        (cls.publisher / "ordinary-link").symlink_to("/outside-the-dataset")
        cls.command("git", "-C", str(cls.publisher), "add", "ordinary-link")
        cls.command("datalad", "save", "-d", str(cls.publisher), "-m", "first release")
        cls.first_commit = cls.command("git", "-C", str(cls.publisher), "rev-parse", "HEAD")
        cls.dataset_id = cls.command("git", "-C", str(cls.publisher), "config", "-f", ".datalad/config", "--get", "datalad.dataset.id")
        cls.store = cls.root / "store"
        cls.command("datalad", "create-sibling-ria", "-d", str(cls.publisher), "--name", "goldmine", "--alias", "example", "--new-store-ok", f"ria+file://{cls.store}")
        cls.command("datalad", "push", "-d", str(cls.publisher), "--to", "goldmine", "--data", "anything")
        cls.command("datalad", "unlock", "-d", str(cls.publisher), str(release / "data.csv"))
        (release / "data.csv").write_text("value\n2\n")
        cls.command("datalad", "save", "-d", str(cls.publisher), "-m", "upstream advanced")
        cls.second_commit = cls.command("git", "-C", str(cls.publisher), "rev-parse", "HEAD")
        cls.command("datalad", "push", "-d", str(cls.publisher), "--to", "goldmine", "--data", "anything")
        (cls.publisher / "not-published.csv").write_text("value\n3\n")
        cls.command("datalad", "save", "-d", str(cls.publisher), "-m", "metadata without published bytes")
        cls.unavailable_commit = cls.command("git", "-C", str(cls.publisher), "rev-parse", "HEAD")
        cls.command("datalad", "push", "-d", str(cls.publisher), "--to", "goldmine", "--data", "nothing")

    def setUp(self):
        self.project_temp = TemporaryDirectory(prefix="stagecoach-project-", dir=self.root)
        self.addCleanup(self.project_temp.cleanup)
        self.project = Path(self.project_temp.name)
        self.command("git", "init", "-q", str(self.project))
        (self.project / "README.md").write_text("Synthetic consumer\n")
        self.manifest = manifest_for(self.project)
        self.item = self.manifest["sources"]["04_datalad"]["items"][0]
        self.item.update(source=f"ria+file://{self.store}#~example", dataset_id=self.dataset_id, revision=self.first_commit)
        self.console = Console(file=StringIO())
        self.destination = self.project / "data/inputs/04_datalad/example"

    def stage(self):
        return adapter.stage_data_from_datalad(self.manifest, self.console)

    def test_inspection_pin_selective_retrieval_repeat_and_drop_recovery(self):
        clearance = adapter.check_datalad_clearance(self.manifest)
        self.assertTrue(clearance.cleared, clearance)
        self.assertFalse((self.project / "data").exists())
        self.assertTrue(all(not r["has_content"] for r in clearance.details["items"][0]["files"]))
        path = self.project / "manifest.yml"
        content = yaml.safe_dump(self.manifest).encode()
        path.write_bytes(content)
        self.assertTrue(StageCoach(manifest_path=path, console=self.console).stage(), self.console.file.getvalue())
        self.assertEqual((self.destination / "releases/v1/data.csv").read_text(), "value\n1\n")
        self.assertTrue((self.destination / "releases/v1/datapackage.json").is_file())
        self.assertTrue((self.destination / "unselected.csv").is_symlink())
        self.assertFalse((self.destination / "unselected.csv").exists())
        self.assertEqual(self.command("git", "-C", str(self.destination), "rev-parse", "HEAD"), self.first_commit)
        self.assertFalse((self.project / ".gitmodules").exists())
        receipt_path, = (self.project / ".stagecoach/receipts").glob("*.json")
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual(receipt["manifest_sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(receipt["status"], "success")
        observed = receipt["items"][0]["observed"]
        self.assertEqual(observed["dataset_id"], self.dataset_id)
        self.assertEqual(observed["revision"], self.first_commit)
        self.assertTrue(all(f["annex_key"] and f["has_content"] and f["git_blob"] for f in observed["files"]))
        self.assertTrue(self.stage().staged)
        self.command("git", "-C", str(self.destination), "annex", "drop", "--force", "--", "releases/v1/data.csv")
        self.assertFalse((self.destination / "releases/v1/data.csv").exists())
        self.assertTrue(self.stage().staged)
        self.assertEqual((self.destination / "releases/v1/data.csv").read_text(), "value\n1\n")

    def test_literal_file_does_not_get_other_release_files(self):
        self.item["paths"] = ["releases/v1/data.csv"]
        result = self.stage()
        self.assertTrue(result.staged, result.message)
        self.assertTrue((self.destination / "releases/v1/data.csv").exists())
        self.assertFalse((self.destination / "releases/v1/datapackage.json").exists())

    def test_unpublished_bytes_fail_then_retry_after_publication(self):
        self.item.update(revision=self.unavailable_commit, paths=["not-published.csv"])
        result = self.stage()
        self.assertFalse(result.staged, "must not retrieve from the publisher's worktree")
        self.assertEqual(json.loads(Path(result.details["receipt"]).read_text())["status"], "failed")
        self.assertFalse((self.destination / "not-published.csv").exists())
        self.command("datalad", "push", "-d", str(self.publisher), "--to", "goldmine", "--data", "anything")
        result = self.stage()
        self.assertTrue(result.staged, result.message)
        self.assertEqual((self.destination / "not-published.csv").read_text(), "value\n3\n")
        receipt = json.loads(Path(result.details["receipt"]).read_text())
        self.assertTrue(receipt["items"][0]["metadata_refresh"])
        self.assertEqual(receipt["items"][0]["observed"]["revision"], self.unavailable_commit)

    def test_wrong_identity_revision_and_untracked_paths(self):
        for fields, message in (
            ({"dataset_id": DATASET_ID}, "identity conflict"),
            ({"revision": "1" * 40}, "failed"),
            ({"paths": ["not-tracked.csv"]}, "not tracked"),
            ({"get_source": "missing-storage"}, "not configured"),
            ({"paths": ["ordinary-link"]}, "ordinary symlinks"),
        ):
            with self.subTest(fields=fields):
                manifest = deepcopy(self.manifest)
                manifest["sources"]["04_datalad"]["items"][0].update(fields)
                clearance = adapter.check_datalad_clearance(manifest)
                self.assertFalse(clearance.cleared)
                self.assertIn(message, clearance.details["items"][0]["error"])
        self.assertFalse((self.project / "data").exists())

    def test_existing_clone_conflicts_preserve_local_state(self):
        result = self.stage()
        self.assertTrue(result.staged, result.message)
        changed = self.destination / ".gitattributes"
        original = changed.read_text()
        changed.write_text(original + "\n# consumer edit\n")
        result = self.stage()
        self.assertFalse(result.staged)
        self.assertIn("modified or untracked", result.message)
        self.assertIn("consumer edit", changed.read_text())
        changed.write_text(original)
        self.command("git", "-C", str(self.destination), "checkout", "--detach", self.second_commit)
        result = self.stage()
        self.assertFalse(result.staged)
        self.assertIn("Revision conflict", result.message)
        self.assertEqual(self.command("git", "-C", str(self.destination), "rev-parse", "HEAD"), self.second_commit)

    def test_symlink_destination_is_rejected(self):
        self.destination.parent.mkdir(parents=True)
        self.destination.symlink_to(self.publisher, target_is_directory=True)
        result = self.stage()
        self.assertFalse(result.staged)
        self.assertIn("Unsafe DataLad destination", result.message)
        self.assertTrue(self.destination.is_symlink())


if __name__ == "__main__":
    unittest.main()
