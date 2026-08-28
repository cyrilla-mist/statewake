import unittest

from fastapi.testclient import TestClient

from app.server import app


class ProductionServingTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_serves_statewake_ui(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("STATEWAKE", response.text)

    def test_static_assets_resolve(self):
        css = self.client.get("/static/styles.css")
        js = self.client.get("/static/app.js")
        self.assertEqual(css.status_code, 200)
        self.assertEqual(js.status_code, 200)
        self.assertIn("--ice-0", css.text)
        self.assertIn("apiBase", js.text)

    def test_api_status_remains_functional(self):
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
