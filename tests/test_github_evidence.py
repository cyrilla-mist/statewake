import unittest

from app.config import HERO_BASELINE_SHA
from app.tools.github_evidence import (
    get_recent_evidence,
)


class GitHubEvidenceTest(
    unittest.TestCase
):
    def test_real_hero_evidence(
        self,
    ):
        result = (
            get_recent_evidence()
        )

        self.assertEqual(
            result["status"],
            "success",
        )

        self.assertEqual(
            result["baseline_cursor"],
            HERO_BASELINE_SHA,
        )

        self.assertEqual(
            result[
                "commits_since_baseline"
            ],
            5,
        )

        evidence = result[
            "evidence"
        ]

        ids = {
            item["id"]
            for item in evidence
        }

        self.assertIn(
            "state:active-route",
            ids,
        )

        self.assertIn(
            "state:feature-a",
            ids,
        )

        self.assertIn(
            "state:feature-b",
            ids,
        )

        self.assertIn(
            "state:deployment",
            ids,
        )

        self.assertIn(
            "state:presentation",
            ids,
        )

        self.assertIn(
            "docs:readme",
            ids,
        )

        self.assertIn(
            "issue:1",
            ids,
        )

        active_route = next(
            item
            for item in evidence
            if item["id"]
            == "state:active-route"
        )

        self.assertEqual(
            active_route[
                "data"
            ]["state"][
                "activeFeature"
            ],
            "feature-b",
        )

        deployment = next(
            item
            for item in evidence
            if item["id"]
            == "state:deployment"
        )

        self.assertTrue(
            deployment[
                "data"
            ]["state"][
                "blocksHostedDemo"
            ]
        )

        presentation = next(
            item
            for item in evidence
            if item["id"]
            == "state:presentation"
        )

        self.assertFalse(
            presentation[
                "data"
            ]["state"][
                "behaviorChanged"
            ]
        )


if __name__ == "__main__":
    unittest.main()