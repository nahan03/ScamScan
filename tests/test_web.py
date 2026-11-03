"""Tests for the Django page (FR-1, FR-10, FR-8 and the security design)."""

import os
import re
import unittest
from unittest import mock

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.settings")
os.environ.setdefault("DJANGO_DEBUG", "1")

import django

django.setup()

from django.test import Client, SimpleTestCase, override_settings

from scamscan.constants import MAX_CHARS

from . import samples


@override_settings(ALLOWED_HOSTS=["testserver"])
class PageTests(SimpleTestCase):
    def setUp(self):
        # No model needed to test the page itself; rules-only keeps these tests fast and stable.
        patcher = mock.patch("checker.views.default_classifier", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = Client()

    def test_get_shows_the_form_and_the_disclaimer(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('name="ad"', html)
        self.assertIn("csrfmiddlewaretoken", html)
        self.assertIn("not a verdict", html)
        self.assertIn("not stored", html)

    def test_valid_ad_returns_a_result_with_flags_and_a_reply(self):
        response = self.client.post("/", {"ad": samples.SCAM_FEE})
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Risk: HIGH", html)
        self.assertIn("Asks you to pay money", html)
        self.assertIn("Message you can send", html)

    def test_legit_ad_shows_positives_and_a_low_level(self):
        html = self.client.post("/", {"ad": samples.LEGIT_DETAILED}).content.decode()
        self.assertIn("Risk: LOW", html)
        self.assertIn("Reassuring signs", html)

    def test_empty_input_shows_a_clear_error(self):
        for body in ("", "   \n  "):
            response = self.client.post("/", {"ad": body})
            self.assertEqual(response.status_code, 400)
            self.assertIn("Please paste a job ad", response.content.decode())

    def test_oversized_input_shows_a_clear_error(self):
        response = self.client.post("/", {"ad": "a" * (MAX_CHARS + 1)})
        self.assertEqual(response.status_code, 400)
        self.assertIn("too long", response.content.decode())

    def test_huge_request_body_is_rejected_without_crashing(self):
        response = self.client.post("/", {"ad": "a" * (200 * 1024)})
        self.assertEqual(response.status_code, 400)

    def test_post_without_a_csrf_token_is_refused(self):
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post("/", {"ad": samples.SCAM_FEE}).status_code, 403)

    def test_ad_text_is_html_escaped(self):
        html = self.client.post("/", {"ad": "<script>alert(1)</script> hiring now"}).content.decode()
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)

    def test_security_headers_and_csp_nonce(self):
        response = self.client.get("/")
        csp = response["Content-Security-Policy"]
        self.assertIn("default-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        nonce = re.search(r"'nonce-([^']+)'", csp).group(1)
        self.assertIn(f'nonce="{nonce}"', response.content.decode())
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_other_methods_are_not_allowed(self):
        self.assertEqual(self.client.put("/").status_code, 405)

    def test_health_check(self):
        response = self.client.get("/healthz")
        self.assertEqual((response.status_code, response.content), (200, b"ok"))

    def test_llm_is_only_used_when_a_key_is_set(self):
        with mock.patch("checker.views.analyze", return_value=_fake_result()) as analyze:
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("ANTHROPIC_API_KEY", None)
                self.client.post("/", {"ad": samples.SCAM_FEE})
            self.assertFalse(analyze.call_args.kwargs["use_llm"])
            with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                self.client.post("/", {"ad": samples.SCAM_FEE})
            self.assertTrue(analyze.call_args.kwargs["use_llm"])


def _fake_result():
    return {"level": "low", "score": 5, "flags": [], "positives": [], "model_prob": None,
            "summary": "ok", "reply_template": "hi"}


class SettingsTests(unittest.TestCase):
    def test_secret_key_is_required_when_debug_is_off(self):
        import importlib

        from django.core.exceptions import ImproperlyConfigured

        from webapp import settings

        env = {"DJANGO_DEBUG": "0", "DJANGO_SECRET_KEY": ""}
        with mock.patch.dict(os.environ, env), self.assertRaises(ImproperlyConfigured):
            importlib.reload(settings)
        importlib.reload(settings)  # restore the debug-mode module for the other tests


if __name__ == "__main__":
    unittest.main()
