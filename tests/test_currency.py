"""
Tests for Currency Conversion Service – Dream Line Travels
==========================================================
Covers:
 - USD → INR conversion
 - INR → USD conversion
 - AED → INR conversion
 - INR → AED conversion
 - USD → AED conversion
 - AED → USD conversion
 - Same-currency no-op
 - Unsupported currency error
 - Zero / negative amount guard
 - ExchangeRate-API live fetch (mocked)
 - Frankfurter fallback (mocked)
 - Static fallback when all APIs fail
 - Cache reuse
 - Indicative label when not live
 - format_conversion_reply English
 - format_conversion_reply Arabic
"""

import os
import sys
import json
import time
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.currency_service import (
    convert,
    format_conversion_reply,
    get_rates,
    invalidate_cache,
    SUPPORTED,
    SYMBOLS,
    _STATIC_FALLBACK,
)


# ── Helper: build a mock urllib response ─────────────────────────────────────
def _mock_urlopen(json_body: dict, status: int = 200):
    """Return a context-manager mock that yields a fake HTTP response."""
    body = json.dumps(json_body).encode()
    mock_resp = MagicMock()
    mock_resp.status = status
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


_ERA_SUCCESS = {
    "result": "success",
    "conversion_rates": {
        "USD": 1.0,
        "INR": 83.80,
        "AED": 3.6725,
        "EUR": 0.921,
        "GBP": 0.787,
    }
}

_FRANKFURTER_SUCCESS = {
    "rates": {
        "INR": 83.70,
        "AED": 3.670,
        "EUR": 0.920,
        "GBP": 0.786,
    }
}


class TestCurrencyConvertPairs(unittest.TestCase):
    """Test all required currency pairs using mocked ExchangeRate-API."""

    def setUp(self):
        invalidate_cache()

    def _patch_era(self):
        return patch(
            "urllib.request.urlopen",
            return_value=_mock_urlopen(_ERA_SUCCESS)
        )

    def test_usd_to_inr(self):
        with self._patch_era():
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": "test-key"}):
                result = convert(500, "USD", "INR")
        self.assertNotIn("error", result)
        self.assertAlmostEqual(result["to_amount"], 500 * 83.80, delta=1)
        self.assertEqual(result["from_currency"], "USD")
        self.assertEqual(result["to_currency"], "INR")
        self.assertTrue(result["is_live"])
        self.assertIn("ExchangeRate-API", result["source"])
        invalidate_cache()

    def test_inr_to_usd(self):
        with self._patch_era():
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": "test-key"}):
                result = convert(10000, "INR", "USD")
        self.assertNotIn("error", result)
        expected = 10000 / 83.80
        self.assertAlmostEqual(result["to_amount"], expected, delta=0.1)
        self.assertEqual(result["to_currency"], "USD")
        invalidate_cache()

    def test_aed_to_inr(self):
        with self._patch_era():
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": "test-key"}):
                result = convert(1000, "AED", "INR")
        self.assertNotIn("error", result)
        expected = (1000 / 3.6725) * 83.80
        self.assertAlmostEqual(result["to_amount"], expected, delta=5)
        self.assertEqual(result["from_currency"], "AED")
        self.assertEqual(result["to_currency"], "INR")
        invalidate_cache()

    def test_inr_to_aed(self):
        with self._patch_era():
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": "test-key"}):
                result = convert(50000, "INR", "AED")
        self.assertNotIn("error", result)
        expected = (50000 / 83.80) * 3.6725
        self.assertAlmostEqual(result["to_amount"], expected, delta=1)
        invalidate_cache()

    def test_usd_to_aed(self):
        with self._patch_era():
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": "test-key"}):
                result = convert(100, "USD", "AED")
        self.assertNotIn("error", result)
        self.assertAlmostEqual(result["to_amount"], 100 * 3.6725, delta=0.1)
        invalidate_cache()

    def test_aed_to_usd(self):
        with self._patch_era():
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": "test-key"}):
                result = convert(367.25, "AED", "USD")
        self.assertNotIn("error", result)
        expected = 367.25 / 3.6725
        self.assertAlmostEqual(result["to_amount"], expected, delta=0.5)
        invalidate_cache()


class TestSameCurrency(unittest.TestCase):
    def setUp(self):
        invalidate_cache()

    def test_usd_to_usd(self):
        result = convert(200, "USD", "USD")
        self.assertNotIn("error", result)
        self.assertEqual(result["to_amount"], 200.0)
        self.assertEqual(result["rate"], 1.0)

    def test_inr_to_inr(self):
        result = convert(5000, "INR", "INR")
        self.assertEqual(result["to_amount"], 5000.0)


class TestInputValidation(unittest.TestCase):
    def setUp(self):
        invalidate_cache()

    def test_unsupported_from_currency(self):
        result = convert(100, "JPY", "USD")
        self.assertIn("error", result)
        self.assertIn("JPY", result["error"])

    def test_unsupported_to_currency(self):
        result = convert(100, "USD", "BTC")
        self.assertIn("error", result)

    def test_zero_amount(self):
        result = convert(0, "USD", "INR")
        self.assertIn("error", result)

    def test_negative_amount(self):
        result = convert(-100, "USD", "INR")
        self.assertIn("error", result)


class TestFallbackBehaviour(unittest.TestCase):
    """Test the full fallback chain."""

    def setUp(self):
        invalidate_cache()

    def tearDown(self):
        invalidate_cache()

    def test_frankfurter_fallback_when_no_era_key(self):
        """Without ERA key, should use Frankfurter."""
        frankfurt_resp = _mock_urlopen(_FRANKFURTER_SUCCESS)
        with patch("urllib.request.urlopen", return_value=frankfurt_resp):
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": ""}):
                result = convert(100, "USD", "INR")
        self.assertNotIn("error", result)
        self.assertAlmostEqual(result["to_amount"], 100 * 83.70, delta=1)
        self.assertIn("Frankfurter", result["source"])
        self.assertTrue(result["is_live"])

    def test_static_fallback_when_all_apis_fail(self):
        """When all network calls raise, use static fallback with indicative label."""
        with patch("urllib.request.urlopen", side_effect=OSError("network down")):
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": ""}):
                result = convert(100, "USD", "INR")
        self.assertNotIn("error", result)
        self.assertFalse(result["is_live"])
        self.assertIn("Indicative", result["source"])
        self.assertIn("INDICATIVE", result["disclaimer"].upper())

    def test_era_placeholder_key_skipped(self):
        """A placeholder key (starts with 'your_') must NOT be sent to the API."""
        called_urls = []

        def fake_urlopen(req, timeout=None):
            # Capture what URL is being called
            url = req.full_url if hasattr(req, "full_url") else str(req)
            called_urls.append(url)
            return _mock_urlopen(_FRANKFURTER_SUCCESS)

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": "your_key_here"}):
                get_rates()

        # ExchangeRate-API URL must NOT have been called
        for url in called_urls:
            self.assertNotIn("exchangerate-api.com", url), \
                f"Placeholder key was sent to ExchangeRate-API! URL: {url}"


class TestCaching(unittest.TestCase):
    def setUp(self):
        invalidate_cache()

    def tearDown(self):
        invalidate_cache()

    def test_cache_reuses_rates_within_ttl(self):
        """get_rates() must call the API only once within the cache TTL."""
        with patch(
            "urllib.request.urlopen",
            return_value=_mock_urlopen(_ERA_SUCCESS)
        ) as mock_open:
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": "test-key"}):
                get_rates()
                get_rates()   # second call must reuse cache
                get_rates()   # third call too

        self.assertEqual(mock_open.call_count, 1)

    def test_invalidate_cache_forces_refetch(self):
        with patch(
            "urllib.request.urlopen",
            return_value=_mock_urlopen(_ERA_SUCCESS)
        ) as mock_open:
            with patch.dict(os.environ, {"EXCHANGERATE_API_KEY": "test-key"}):
                get_rates()
                invalidate_cache()
                get_rates()

        self.assertEqual(mock_open.call_count, 2)


class TestFormatConversionReply(unittest.TestCase):
    """Test the chat formatting function."""

    def _sample_result(self, live: bool = True) -> dict:
        return {
            "from_currency": "USD",
            "to_currency": "INR",
            "from_amount": 100.0,
            "to_amount": 8380.0,
            "rate": 83.80,
            "source": "ExchangeRate-API (live)" if live else "Indicative (static fallback)",
            "fetched_at": "2026-01-01 10:00 UTC",
            "is_live": live,
            "disclaimer": "Test disclaimer.",
        }

    def test_english_format_contains_symbols(self):
        reply = format_conversion_reply(self._sample_result(), lang="en")
        self.assertIn("$", reply)
        self.assertIn("₹", reply)
        self.assertIn("8,380.00", reply)
        self.assertIn("100.00", reply)
        self.assertIn("ExchangeRate-API", reply)

    def test_english_live_tag(self):
        reply = format_conversion_reply(self._sample_result(live=True), lang="en")
        self.assertIn("🟢 Live", reply)

    def test_english_indicative_tag(self):
        reply = format_conversion_reply(self._sample_result(live=False), lang="en")
        self.assertIn("🟡 Indicative", reply)

    def test_arabic_format_contains_arabic_text(self):
        reply = format_conversion_reply(self._sample_result(), lang="ar")
        self.assertIn("تحويل العملات", reply)
        self.assertIn("سعر الصرف", reply)

    def test_arabic_contains_symbols(self):
        result = {
            "from_currency": "AED",
            "to_currency": "INR",
            "from_amount": 1000.0,
            "to_amount": 22800.0,
            "rate": 22.8,
            "source": "ExchangeRate-API (live)",
            "fetched_at": "2026-01-01 10:00 UTC",
            "is_live": True,
            "disclaimer": "Test disclaimer.",
        }
        reply = format_conversion_reply(result, lang="ar")
        self.assertIn("د.إ", reply)
        self.assertIn("₹", reply)

    def test_error_dict_in_english(self):
        reply = format_conversion_reply({"error": "Bad currency"}, lang="en")
        self.assertIn("Error", reply)
        self.assertIn("Bad currency", reply)

    def test_error_dict_in_arabic(self):
        reply = format_conversion_reply({"error": "Bad currency"}, lang="ar")
        self.assertIn("خطأ", reply)


class TestSupportedCurrencies(unittest.TestCase):
    def test_all_required_currencies_present(self):
        for code in ("USD", "INR", "AED"):
            self.assertIn(code, SUPPORTED)

    def test_symbols_present(self):
        self.assertEqual(SYMBOLS["USD"], "$")
        self.assertEqual(SYMBOLS["INR"], "₹")
        self.assertEqual(SYMBOLS["AED"], "د.إ")


if __name__ == "__main__":
    unittest.main(verbosity=2)

