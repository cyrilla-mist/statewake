import os
import unittest
from unittest.mock import patch

from app import config
from scripts.run_real_reentry_demo import _validate_vertex_configuration


class VertexConfigurationTest(unittest.TestCase):
    def test_enterprise_mode_selects_vertex_without_api_key(self):
        with (
            patch.object(config, "GOOGLE_GENAI_USE_ENTERPRISE", True),
            patch.object(config, "GOOGLE_CLOUD_PROJECT", "statewake-agentic-2026"),
            patch.object(config, "GOOGLE_CLOUD_LOCATION", "global"),
            patch.dict(os.environ, {"GOOGLE_API_KEY": "", "GEMINI_API_KEY": ""}, clear=False),
            patch("scripts.run_real_reentry_demo.google_auth_default"),
        ):
            self.assertEqual(config.get_model_backend(), "VERTEX_AI")
            _validate_vertex_configuration()

    def test_vertex_alias_alone_does_not_select_production_backend(self):
        with (
            patch.object(config, "GOOGLE_GENAI_USE_ENTERPRISE", False),
            patch.object(config, "GOOGLE_GENAI_USE_VERTEXAI", True),
        ):
            self.assertEqual(config.get_model_backend(), "UNCONFIGURED")

    def test_api_keys_cannot_switch_backend(self):
        with (
            patch.object(config, "GOOGLE_GENAI_USE_ENTERPRISE", False),
            patch.object(config, "GOOGLE_GENAI_USE_VERTEXAI", False),
            patch.dict(os.environ, {"GOOGLE_API_KEY": "legacy", "GEMINI_API_KEY": "legacy"}, clear=False),
        ):
            self.assertEqual(config.get_model_backend(), "UNCONFIGURED")

    def test_missing_cloud_project_fails_clearly(self):
        with (
            patch.object(config, "GOOGLE_GENAI_USE_ENTERPRISE", True),
            patch.object(config, "GOOGLE_CLOUD_PROJECT", None),
            patch.object(config, "GOOGLE_CLOUD_LOCATION", "global"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Google Cloud project"):
                config.validate_vertex_configuration()

    def test_missing_location_fails_clearly(self):
        with (
            patch.object(config, "GOOGLE_GENAI_USE_ENTERPRISE", True),
            patch.object(config, "GOOGLE_CLOUD_PROJECT", "statewake-agentic-2026"),
            patch.object(config, "GOOGLE_CLOUD_LOCATION", None),
        ):
            with self.assertRaisesRegex(RuntimeError, "Google Cloud location"):
                config.validate_vertex_configuration()

    def test_enterprise_mode_is_required(self):
        with (
            patch.object(config, "GOOGLE_GENAI_USE_ENTERPRISE", False),
            patch.object(config, "GOOGLE_CLOUD_PROJECT", "statewake-agentic-2026"),
            patch.object(config, "GOOGLE_CLOUD_LOCATION", "global"),
        ):
            with self.assertRaisesRegex(RuntimeError, "GOOGLE_GENAI_USE_ENTERPRISE"):
                config.validate_vertex_configuration()


if __name__ == "__main__":
    unittest.main()
