"""
Currency Conversion Service – Dream Line Travels
=================================================
Primary source  : ExchangeRate-API  (https://www.exchangerate-api.com/)
                  Endpoint: https://v6.exchangerate-api.com/v6/{KEY}/latest/USD
                  Requires EXCHANGERATE_API_KEY in environment / .env
Fallback source : Frankfurter API  (ECB rates, no key required)
Hard fallback   : Indicative static rates (clearly labelled, never presented as live)

Supported pairs : USD ↔ INR, USD ↔ AED, INR ↔ AED (and all combinations)

Usage:
    from app.services.currency_service import convert, format_conversion_reply

    result = convert(500, "USD", "INR")
    print(format_conversion_reply(result))
"""

import datetime
import json
import os
import time
import urllib.error
import urllib.request
from typing import Dict, Optional, Tuple

# ── Supported currencies ────────────────────────────────────────────────────
SUPPORTED: Dict[str, str] = {
    "USD": "US Dollar ($)",
    "INR": "Indian Rupee (₹)",
    "AED": "UAE Dirham (د.إ)",
    "EUR": "Euro (€)",
    "GBP": "British Pound (£)",
}

SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "INR": "₹",
    "AED": "د.إ",
    "EUR": "€",
    "GBP": "£",
}

# ── Static fallback rates (USD base) ───────────────────────────────────────
# These are used ONLY when all live APIs are unreachable.
# They are clearly labelled as indicative in every reply.
_STATIC_FALLBACK: Dict[str, float] = {
    "USD": 1.0,
    "INR": 84.5,
    "AED": 3.6725,
    "EUR": 0.92,
    "GBP": 0.79,
}

# ── In-memory rate cache ────────────────────────────────────────────────────
_CACHE: Dict = {}
_CACHE_TTL_SECONDS = 3600          # Refresh at most once per hour


# ── Private: fetch from ExchangeRate-API (PRIMARY) ─────────────────────────
def _fetch_exchangerate_api(api_key: str) -> Optional[Tuple[Dict[str, float], str]]:
    """
    Call ExchangeRate-API v6 latest endpoint (USD base).
    Returns (rates_dict, source_label) or None on any failure.
    """
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD"
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "DreamLineAI/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("result") != "success":
            return None

        rates = data.get("conversion_rates")
        if not isinstance(rates, dict) or "USD" not in rates:
            return None

        return rates, "ExchangeRate-API (live)"

    except urllib.error.HTTPError as exc:
        # 403 = invalid key, 429 = rate limit
        return None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    except (json.JSONDecodeError, KeyError, ValueError):
        return None


# ── Private: fetch from Frankfurter API (SECONDARY fallback, no key) ───────
def _fetch_frankfurter() -> Optional[Tuple[Dict[str, float], str]]:
    """
    Call the free Frankfurter API (European Central Bank rates).
    Returns (rates_dict, source_label) or None on failure.
    """
    url = "https://api.frankfurter.app/latest?from=USD"
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        rates = data.get("rates", {})
        if not rates:
            return None

        # Frankfurter does not include the base currency itself
        rates["USD"] = 1.0
        return rates, "Frankfurter/ECB (live)"

    except Exception:
        return None


# ── Public: get current rates ───────────────────────────────────────────────
def get_rates() -> Tuple[Dict[str, float], str, float]:
    """
    Return (rates_dict, source_name, fetched_at_unix_timestamp).

    Priority:
      1. In-memory cache (if fresh)
      2. ExchangeRate-API  (if EXCHANGERATE_API_KEY is set and valid)
      3. Frankfurter/ECB   (free, no key)
      4. Static indicative rates (last resort, clearly labelled)
    """
    global _CACHE
    now = time.time()

    # Return cache if still fresh
    if _CACHE and (now - _CACHE.get("fetched_at", 0)) < _CACHE_TTL_SECONDS:
        return _CACHE["rates"], _CACHE["source"], _CACHE["fetched_at"]

    rates: Optional[Dict[str, float]] = None
    source: str = "Indicative (static fallback — not live)"

    # 1. ExchangeRate-API (primary)
    era_key = os.getenv("EXCHANGERATE_API_KEY", "").strip()
    if era_key and not era_key.startswith("your_"):
        result = _fetch_exchangerate_api(era_key)
        if result:
            rates, source = result

    # 2. Frankfurter (secondary)
    if not rates:
        result = _fetch_frankfurter()
        if result:
            rates, source = result

    # 3. Static fallback
    if not rates:
        rates = dict(_STATIC_FALLBACK)
        source = "Indicative (static fallback — not live)"

    fetched_at = now
    _CACHE = {"rates": rates, "source": source, "fetched_at": fetched_at}
    return rates, source, fetched_at


def invalidate_cache() -> None:
    """Force a fresh fetch on the next call to get_rates()."""
    global _CACHE
    _CACHE = {}


# ── Public: convert amount ─────────────────────────────────────────────────
def convert(amount: float, from_currency: str, to_currency: str) -> Dict:
    """
    Convert `amount` from `from_currency` to `to_currency`.

    Returns a dict with:
      from_currency, to_currency, from_amount, to_amount,
      rate, source, fetched_at, is_live, disclaimer
    or {"error": "..."} if inputs are invalid.

    Never returns invented rates — if live fetch fails the
    result is labelled as indicative.
    """
    from_c = from_currency.upper().strip()
    to_c   = to_currency.upper().strip()

    if from_c not in SUPPORTED:
        return {"error": f"Unsupported source currency '{from_c}'. Supported: {', '.join(SUPPORTED)}"}
    if to_c not in SUPPORTED:
        return {"error": f"Unsupported target currency '{to_c}'. Supported: {', '.join(SUPPORTED)}"}
    if not isinstance(amount, (int, float)) or amount <= 0:
        return {"error": "Amount must be a positive number."}
    if from_c == to_c:
        return {
            "from_currency": from_c,
            "to_currency":   to_c,
            "from_amount":   round(float(amount), 4),
            "to_amount":     round(float(amount), 4),
            "rate":          1.0,
            "source":        "Same currency",
            "fetched_at":    datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "is_live":       True,
            "disclaimer":    "Same currency — no conversion needed.",
        }

    rates, source, fetched_at = get_rates()
    is_live = "live" in source.lower() and "not live" not in source.lower()

    # Cross-rate via USD base: amount → USD → target
    from_rate = rates.get(from_c, _STATIC_FALLBACK.get(from_c, 1.0))
    to_rate   = rates.get(to_c,   _STATIC_FALLBACK.get(to_c,   1.0))

    amount_usd    = float(amount) / from_rate
    amount_target = amount_usd * to_rate
    cross_rate    = to_rate / from_rate

    fetched_str = datetime.datetime.fromtimestamp(fetched_at).strftime("%Y-%m-%d %H:%M UTC")

    disclaimer = (
        "Live rate from ExchangeRate-API. "
        "Actual bank or card rates may differ. "
        "Always confirm with your financial institution before transacting."
    ) if is_live else (
        "⚠️ Live rate unavailable. This is an INDICATIVE rate only. "
        "Do not use for financial transactions. "
        "Check a bank or financial service for the actual rate."
    )

    return {
        "from_currency": from_c,
        "to_currency":   to_c,
        "from_amount":   round(float(amount), 4),
        "to_amount":     round(amount_target, 4),
        "rate":          round(cross_rate, 6),
        "source":        source,
        "fetched_at":    fetched_str,
        "is_live":       is_live,
        "disclaimer":    disclaimer,
    }


# ── Public: format result for chat display ─────────────────────────────────
def format_conversion_reply(result: Dict, lang: str = "en") -> str:
    """
    Format a convert() result dict as a human-friendly chat string.
    Supports English and Arabic.
    """
    if "error" in result:
        if lang == "ar":
            return f"❌ خطأ: {result['error']}"
        return f"❌ Error: {result['error']}"

    from_sym = SYMBOLS.get(result["from_currency"], "")
    to_sym   = SYMBOLS.get(result["to_currency"], "")

    from_str = f"{from_sym}{result['from_amount']:,.2f} {result['from_currency']}"
    to_str   = f"{to_sym}{result['to_amount']:,.2f} {result['to_currency']}"
    rate_str = f"1 {result['from_currency']} = {result['rate']:,.4f} {result['to_currency']}"
    live_tag = "🟢 Live" if result.get("is_live") else "🟡 Indicative"

    if lang == "ar":
        return (
            f"💱 تحويل العملات ({live_tag})\n"
            f"**{from_str}** = **{to_str}**\n"
            f"سعر الصرف: {rate_str}\n"
            f"المصدر: {result['source']} | آخر تحديث: {result['fetched_at']}\n"
            f"⚠️ {result['disclaimer']}"
        )

    return (
        f"💱 Currency Conversion ({live_tag})\n"
        f"**{from_str}** = **{to_str}**\n"
        f"Rate: {rate_str}\n"
        f"Source: {result['source']} | Updated: {result['fetched_at']}\n"
        f"⚠️ {result['disclaimer']}"
    )
