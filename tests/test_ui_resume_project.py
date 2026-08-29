import unittest
from pathlib import Path


UI_JS = Path(__file__).parents[1] / "ui" / "app.js"


class UiResumeProjectTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = UI_JS.read_text(encoding="utf-8")
        cls.resume_handler = cls.source.split("async function requestResumeProject()", 1)[1].split(
            "async function requestResolution()", 1
        )[0]

    def test_resume_project_is_an_explicit_action(self):
        self.assertIn('data-action="resume-project"', self.source)
        self.assertNotIn('actionButton("Resume Project", "resume")', self.source)

    def test_resume_project_reads_project_state_and_returns_to_return(self):
        self.assertIn('fetch(`${apiBase}/api/project`)', self.resume_handler)
        self.assertIn("currentTrustedState = payload.project_state", self.resume_handler)
        self.assertIn('window.location.hash = "return"', self.resume_handler)
        self.assertIn("Trusted state response was malformed", self.resume_handler)

    def test_return_cards_render_committed_state_with_cp01_fallback(self):
        cards = self.source.split("function returnStateCards()", 1)[1].split(
            "function button(", 1
        )[0]
        self.assertIn("currentTrustedState || latestApiResponse?.trusted_state", cards)
        self.assertIn('checkpoint_id: "CP-01"', cards)
        self.assertIn("trusted.direction", cards)
        self.assertIn("trusted.current_next_action", cards)

    def test_resume_project_does_not_call_mutation_endpoints(self):
        self.assertNotIn("/api/reentry", self.resume_handler)
        self.assertNotIn("/api/reentry/resolution", self.resume_handler)
        self.assertNotIn("/api/reentry/memory", self.resume_handler)


if __name__ == "__main__":
    unittest.main()
