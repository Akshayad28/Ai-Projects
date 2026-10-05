"""Search Intent Parser.

Translates arbitrary natural language queries into structured intent
(category, budget, use cases, requirements, brand preferences).
When LLM keys are configured, calls the LLM for structured extraction.
Falls back to robust rule-based parsing otherwise.
NEVER invents product facts.
"""
from __future__ import annotations

import json
import re
from typing import List, Optional

import httpx

from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.domain import Budget, Condition, SearchIntent
from app.utils.hashing import hash_query

log = get_logger(__name__)

# Currency regex and multipliers
_CURRENCY_PATTERNS = [
    (r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d+)?)\s*(lakh|lac|k|thousand|cr|crore)?", "INR"),
    (r"\$\s*([\d,]+(?:\.\d+)?)\s*(k)?", "USD"),
    (r"£\s*([\d,]+(?:\.\d+)?)\s*(k)?", "GBP"),
    (r"€\s*([\d,]+(?:\.\d+)?)\s*(k)?", "EUR"),
    (r"(?:aed|dirham)\s*([\d,]+(?:\.\d+)?)", "AED"),
    (r"under\s+([\d,]+)\s*(?:rs|rupees|inr)", "INR"),
    (r"under\s+([\d,]+)\s*(?:dollars|usd|\$)", "USD"),
]

# Common brand recognizers
_KNOWN_BRANDS = [
    "apple", "samsung", "sony", "bose", "sennheiser", "jbl", "asus", "dell", "hp",
    "lenovo", "acer", "lg", "oneplus", "google", "xiaomi", "philips", "ninja", "instant",
    "nike", "adidas", "asics", "puma", "new balance", "hoka", "saucony", "sihoo", "herman miller",
    "steelcase", "featherlite", "bosch", "dewalt", "stanley", "black+decker", "samsonite",
    "american tourister", "delsey", "minimalist", "cerave", "the ordinary", "cetaphil"
]


def _extract_budget(query: str, default_currency: str = "INR") -> Budget:
    q_lower = query.lower()
    for pat, curr in _CURRENCY_PATTERNS:
        m = re.search(pat, q_lower)
        if m:
            raw_num = m.group(1).replace(",", "")
            multiplier = 1.0
            if len(m.groups()) > 1 and m.group(2):
                unit = m.group(2).lower()
                if unit in {"lakh", "lac"}:
                    multiplier = 100_000.0
                elif unit in {"k", "thousand"}:
                    multiplier = 1_000.0
                elif unit in {"cr", "crore"}:
                    multiplier = 10_000_000.0

            try:
                val = float(raw_num) * multiplier
                # If query says "under X" or "below X" or "budget of X"
                if any(w in q_lower for w in ["under", "below", "max", "less than", "budget"]):
                    return Budget(max=val, currency=curr)
                elif any(w in q_lower for w in ["above", "over", "more than", "min"]):
                    return Budget(min=val, currency=curr)
                else:
                    return Budget(max=val, currency=curr)
            except ValueError:
                pass

    return Budget(currency=default_currency)


def parse_intent_with_rules(query: str, country: str = "IN", currency: str = "INR") -> SearchIntent:
    """Fast, deterministic rule-based intent parsing."""
    q_lower = query.lower()

    budget = _extract_budget(query, default_currency=currency)

    # Detect known brands
    found_brands = [b.title() for b in _KNOWN_BRANDS if re.search(rf"\b{re.escape(b)}\b", q_lower)]

    # Detect use cases
    use_cases: List[str] = []
    use_case_map = {
        "programming": ["programming", "coding", "developer", "software development"],
        "gaming": ["gaming", "esports", "games", "playstation", "xbox"],
        "travel": ["travel", "traveling", "flight", "commute", "portable"],
        "running": ["running", "jogging", "marathon", "long runs"],
        "office": ["office", "wfh", "work from home", "desk work", "long hours"],
        "family": ["family of four", "family of 4", "family", "large family"],
        "photography": ["photography", "photos", "vlogging", "camera"],
        "diy": ["home diy", "diy", "woodworking", "drilling"],
        "acne/oily skin": ["oily skin", "acne", "pimples", "blackheads"],
    }
    for uc, triggers in use_case_map.items():
        if any(t in q_lower for t in triggers):
            use_cases.append(uc)

    # Clean query for raw provider dispatch (strip 'best', 'under ₹1 lakh', etc.)
    clean_provider_q = query
    clean_provider_q = re.sub(r"\b(best|cheap|top|good|recommend|for|under|below|budget)\b", " ", clean_provider_q, flags=re.I)
    clean_provider_q = re.sub(r"[₹\$£€]\s*[\d,]+(?:\s*(?:lakh|lac|k|cr))?", " ", clean_provider_q, flags=re.I)
    clean_provider_q = " ".join(clean_provider_q.split())
    if not clean_provider_q:
        clean_provider_q = query

    return SearchIntent(
        raw_query=query,
        provider_query=clean_provider_q,
        budget=budget,
        use_cases=use_cases,
        preferred_brands=found_brands,
        country=country,
        parser="rules"
    )


async def parse_intent(query: str, country: str = "IN", currency: str = "INR") -> SearchIntent:
    """Parses intent via LLM (Gemini/OpenAI) if available, falling back to rule-based parser.
    Universal parser: supports any product category, brand, model, attribute, or natural language query.
    CATEGORY IS NEVER MANDATORY FOR SEARCH.
    """
    settings = get_settings()

    cache = get_cache()
    cache_key = f"search_intent:{hash_query(query, country, currency)}"
    try:
        cached_intent = await cache.get(cache_key)
        if cached_intent and isinstance(cached_intent, dict):
            return SearchIntent.model_validate(cached_intent)
    except Exception:
        pass

    async def _cache_and_return(intent: SearchIntent) -> SearchIntent:
        try:
            await cache.set(cache_key, intent.model_dump(), ttl=3600)
        except Exception:
            pass
        return intent

    # Rule-based fallback immediately if no LLM configured
    base_intent = parse_intent_with_rules(query, country, currency)

    gemini_key = settings.gemini_api_token
    if not settings.openai_api_key and not gemini_key:
        return await _cache_and_return(base_intent)

    # Google Gemini LLM enrichment
    if gemini_key and (settings.llm_provider in ("auto", "gemini") or not settings.openai_api_key):
        try:
            prompt = f"""You are a universal shopping intent parser. Analyze this user shopping query:
"{query}"
Return a valid JSON object matching this schema:
{{
  "product_type": "specific product type (e.g. office chair, dining table, running shoes, air fryer, cordless drill, etc.) or null",
  "category": "broad product category (e.g. furniture, electronics, footwear, appliances, tools, skincare, clothing, luggage, etc.) or null",
  "brand": "brand name if mentioned or null",
  "model": "model name or number if mentioned (e.g. S26 Ultra, M4, WH-1000XM5) or null",
  "budget_min": number or null,
  "budget_max": number or null,
  "currency": "{currency}",
  "size": "size specification if mentioned or null",
  "color": "color preference if mentioned or null",
  "quantity": integer or null,
  "use_cases": ["intended use case, e.g. long working hours, gaming, family of four"],
  "requirements": ["specific requirements or specs, e.g. 16GB RAM, 512GB SSD, 1440p 165Hz, wooden, 6 people, cordless"],
  "preferred_brands": ["preferred brands"],
  "clean_provider_query": "concise keyword search string optimized for retail search engines without conversational noise words",
  "keywords": ["key search terms"]
}}
DO NOT invent any product models or prices not in the query. Return strictly JSON."""

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.0,
                    "responseMimeType": "application/json",
                },
            }

            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = json.loads(raw_text)
                        if parsed.get("category"):
                            base_intent.category = parsed["category"]
                        if parsed.get("budget_max"):
                            base_intent.budget.max = float(parsed["budget_max"])
                        if parsed.get("budget_min"):
                            base_intent.budget.min = float(parsed["budget_min"])
                        if parsed.get("use_cases"):
                            base_intent.use_cases = parsed["use_cases"]
                        if parsed.get("requirements"):
                            base_intent.requirements = parsed["requirements"]
                        if parsed.get("preferred_brands"):
                            base_intent.preferred_brands = parsed["preferred_brands"]
                        elif parsed.get("brand"):
                            base_intent.preferred_brands = [parsed["brand"]]
                        if parsed.get("size"):
                            base_intent.size = str(parsed["size"])
                        if parsed.get("color"):
                            base_intent.color = str(parsed["color"])
                        if parsed.get("quantity"):
                            try:
                                base_intent.quantity = int(parsed["quantity"])
                            except (ValueError, TypeError):
                                pass
                        if parsed.get("keywords"):
                            base_intent.keywords = parsed["keywords"]
                        if parsed.get("clean_provider_query"):
                            base_intent.provider_query = parsed["clean_provider_query"]
                        base_intent.parser = "gemini"
                        return await _cache_and_return(base_intent)
        except Exception as exc:
            log.warning("Gemini intent parsing skipped, trying fallbacks", extra={"error": str(exc)})

    # Optional OpenAI / LLM enrichment
    if settings.openai_api_key:
        try:
            prompt = f"""You are a universal shopping intent parser. Analyze this user shopping query:
"{query}"
Return a valid JSON object matching this schema:
{{
  "product_type": "specific product type or null",
  "category": "broad product category or null",
  "brand": "brand name if mentioned or null",
  "model": "model name or number if mentioned or null",
  "budget_min": number or null,
  "budget_max": number or null,
  "currency": "{currency}",
  "size": "size specification if mentioned or null",
  "color": "color preference if mentioned or null",
  "use_cases": ["intended use case"],
  "requirements": ["specific requirements or specs"],
  "preferred_brands": ["preferred brands"],
  "clean_provider_query": "concise keyword search string for retail search engines",
  "keywords": ["key search terms"]
}}
DO NOT invent any product models or prices not in the query. Return strictly JSON."""

            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.openai_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.0,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    parsed = json.loads(data["choices"][0]["message"]["content"])
                    if parsed.get("category"):
                        base_intent.category = parsed.get("category")
                    if parsed.get("budget_max"):
                        base_intent.budget.max = float(parsed["budget_max"])
                    if parsed.get("budget_min"):
                        base_intent.budget.min = float(parsed["budget_min"])
                    if parsed.get("use_cases"):
                        base_intent.use_cases = parsed["use_cases"]
                    if parsed.get("requirements"):
                        base_intent.requirements = parsed["requirements"]
                    if parsed.get("preferred_brands"):
                        base_intent.preferred_brands = parsed["preferred_brands"]
                    elif parsed.get("brand"):
                        base_intent.preferred_brands = [parsed["brand"]]
                    if parsed.get("size"):
                        base_intent.size = str(parsed["size"])
                    if parsed.get("color"):
                        base_intent.color = str(parsed["color"])
                    if parsed.get("keywords"):
                        base_intent.keywords = parsed["keywords"]
                    if parsed.get("clean_provider_query"):
                        base_intent.provider_query = parsed["clean_provider_query"]
                    base_intent.parser = "openai"
                    return await _cache_and_return(base_intent)
        except Exception as exc:
            log.warning("OpenAI intent parsing skipped", extra={"error": str(exc)})

    return await _cache_and_return(base_intent)
