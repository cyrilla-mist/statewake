import unittest
from pathlib import Path


UI_JS = Path(__file__).parents[1] / "ui" / "app.js"
UI_CSS = Path(__file__).parents[1] / "ui" / "styles.css"


class UiStructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = UI_JS.read_text(encoding="utf-8")
        cls.styles = UI_CSS.read_text(encoding="utf-8")

    def test_recover_has_one_canonical_comparison_and_decision(self):
        recover_source = self.source.split("function resumeScreen", 1)[0]
        self.assertEqual(recover_source.count('class="comparison"'), 1)
        self.assertEqual(recover_source.count('class="what-matters glass"'), 1)
        self.assertEqual(recover_source.count('data-action="resolution"'), 1)
        self.assertEqual(recover_source.count('data-evidence>'), 1)
        self.assertEqual(recover_source.count('data-action="defer"'), 2)
        self.assertEqual(recover_source.count("Decide later"), 1)
        self.assertIn("Current implementation path", recover_source)

    def test_resume_and_valid_keep_state_notes_inside_their_cards(self):
        resume_source = self.source.split("function validScreen", 1)[0]
        valid_source = self.source.split("function validScreen", 1)[1]
        self.assertEqual(resume_source.count("Ignore for Now"), 1)
        self.assertEqual(resume_source.count("Committed continuation point"), 1)
        self.assertEqual(valid_source.count("No new checkpoint created."), 1)

    def test_mobile_layout_has_single_column_signal_rows(self):
        self.assertIn(".signal-list li { grid-template-columns: 1fr;", self.styles)
        self.assertIn(".comparison { grid-template-columns: 1fr; }", self.styles)


if __name__ == "__main__":
    unittest.main()
