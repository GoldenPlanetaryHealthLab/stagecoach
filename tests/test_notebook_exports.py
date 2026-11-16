"""Check that committed modules still match the notebook code selected for export."""

import ast
from pathlib import Path
import re
import unittest


class NotebookExportTests(unittest.TestCase):
    def test_selected_python_matches_committed_modules(self):
        root = Path(__file__).resolve().parents[1]
        for path in sorted((root / "notebooks").glob("*.qmd")):
            with self.subTest(notebook=path.name):
                blocks = re.findall(
                    r"^```\{python\}[^\n]*\n(.*?)^```\s*$", path.read_text(),
                    re.MULTILINE | re.DOTALL,
                )
                selected = [b for b in blocks if not re.search(
                    r"^#\| sorting-hat: remove\s*$", b, re.MULTILINE,
                )]
                module = root / "src/stagecoach" / (path.stem + ".py")
                self.assertEqual(
                    ast.dump(ast.parse("\n\n".join(selected))),
                    ast.dump(ast.parse(module.read_text())),
                    f"Regenerate {module.name} using quarto render {path.name} --no-execute",
                )


if __name__ == "__main__":
    unittest.main()
