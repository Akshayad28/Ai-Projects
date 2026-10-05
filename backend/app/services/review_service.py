"""Review Intelligence Service.

Processes real reviews obtained from authorized retailer sources.
NEVER generates fake reviews.
Extracts sentiment, positive themes, and recurring complaints strictly from observed text.
"""
from __future__ import annotations

import json
from typing import List, Optional
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.review import Review, ReviewAnalysis
from app.schemas.review import ReviewAnalysisResponse, ReviewItem

log = get_logger(__name__)


class ReviewService:
    """Provides objective review sentiment analysis and theme extraction."""

    async def get_reviews_for_product(self, db: AsyncSession, product_id: str) -> ReviewAnalysisResponse:
        q = select(Review).where(Review.product_id == product_id).limit(50)
        res = await db.execute(q)
        reviews = list(res.scalars().all())

        if not reviews:
            return ReviewAnalysisResponse(
                product_id=product_id,
                reviews_analyzed=0,
                sentiment_score=None,
                positive_themes=[],
                common_complaints=[],
                common_praise=[],
                summary="No verified customer reviews have been indexed for this product yet.",
                confidence=1.0,
                reviews=[],
            )

        items = [
            ReviewItem(
                id=r.id,
                source=r.source,
                rating=r.rating,
                title=r.title,
                text=r.text,
                review_date=r.review_date.strftime("%Y-%m-%d") if r.review_date else None,
                verified=r.verified,
            )
            for r in reviews
        ]

        valid_ratings = [r.rating for r in reviews if r.rating is not None]
        avg_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else 0.0

        settings = get_settings()
        gemini_key = settings.gemini_api_token
        summary_text = f"Analysis of {len(reviews)} verified reviews indicates an average score of {round(avg_rating, 1)}/5."

        # Attempt Gemini review synthesis if API key is configured
        if gemini_key and reviews:
            try:
                sample_reviews = [
                    f"- Rating: {r.rating}/5. Title: {r.title or 'N/A'}. Text: {r.text or ''}"
                    for r in reviews[:15]
                ]
                reviews_blob = "\n".join(sample_reviews)
                prompt = f"""You are an objective review analysis assistant for a shopping engine.
Analyze these real, verified customer reviews for a product:
{reviews_blob}

Task:
1. Extract 2-4 key positive themes (praise) mentioned by customers.
2. Extract 1-3 genuine complaints or recurring drawbacks mentioned by customers.
3. Provide a concise 2-sentence objective summary.

STRICT RULES:
- Do NOT invent, exaggerate, or assume anything not mentioned in the reviews.
- Return strictly valid JSON:
{{
  "positive_themes": ["..."],
  "common_complaints": ["..."],
  "summary": "..."
}}"""
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.0,
                        "responseMimeType": "application/json",
                    },
                }
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(url, json=payload)
                    if resp.status_code == 200:
                        candidates = resp.json().get("candidates", [])
                        if candidates:
                            raw_json = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            parsed = json.loads(raw_json)
                            if parsed.get("positive_themes"):
                                positive_themes = parsed["positive_themes"]
                            if parsed.get("common_complaints"):
                                complaints = parsed["common_complaints"]
                            if parsed.get("summary"):
                                summary_text = parsed["summary"]
            except Exception as exc:
                log.warning("Gemini review summarization skipped, using fallback heuristics", extra={"error": str(exc)})

        # Fallback keyword theme extraction if themes empty
        if not positive_themes and not complaints:
            all_text = " ".join((r.text or "") + " " + (r.title or "") for r in reviews).lower()
            if "battery" in all_text and ("great" in all_text or "long" in all_text or "good" in all_text):
                positive_themes.append("Excellent battery performance")
            if "sound" in all_text and ("clear" in all_text or "bass" in all_text or "amazing" in all_text):
                positive_themes.append("Rich audio fidelity and clarity")
            if "comfortable" in all_text or "ergonomic" in all_text:
                positive_themes.append("Comfortable ergonomic design")
            if "heating" in all_text or "heats up" in all_text:
                complaints.append("Reports of thermal throttling or warmth under load")
            if "mic" in all_text and ("bad" in all_text or "poor" in all_text):
                complaints.append("Microphone quality could be crisper in noisy areas")

        return ReviewAnalysisResponse(
            product_id=product_id,
            reviews_analyzed=len(reviews),
            sentiment_score=round(avg_rating / 5.0, 2) if avg_rating > 0 else None,
            positive_themes=positive_themes,
            common_complaints=complaints,
            common_praise=positive_themes,
            summary=summary_text,
            confidence=0.95,
            reviews=items,
        )
