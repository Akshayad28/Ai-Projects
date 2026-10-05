"""Dynamic recommendation and ranking engine.

Computes a match score (0-100%) and a fully traceable breakdown of reasons,
drawbacks, and trade-offs using category-specific weights and rules loaded
from the database.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.db.models import CategoryRule, CategoryWeight
from app.schemas.domain import RawOffer, RawProduct, SearchIntent


def evaluate_condition(attr_val: Any, op: str, target: Any) -> bool:
    if attr_val is None:
        return False
    try:
        if op == ">=":
            return float(attr_val) >= float(target)
        if op == "<=":
            return float(attr_val) <= float(target)
        if op == ">":
            return float(attr_val) > float(target)
        if op == "<":
            return float(attr_val) < float(target)
        if op == "==":
            return str(attr_val).lower() == str(target).lower()
        if op == "in":
            return str(attr_val).lower() in [str(x).lower() for x in target]
        if op == "contains_any":
            val_str = str(attr_val).lower()
            return any(str(x).lower() in val_str for x in target)
    except (ValueError, TypeError):
        return False
    return False


class RecommendationEngine:
    def rank_products(
        self,
        products: List[RawProduct],
        intent: SearchIntent,
        weights: Dict[str, float],
        rules: List[CategoryRule],
    ) -> List[Tuple[RawProduct, float, Dict[str, Any]]]:
        """Scores, explains, and ranks products based on intent and category rules."""
        scored: List[Tuple[RawProduct, float, Dict[str, Any]]] = []

        w_req = weights.get("requirement_match", 0.25)
        w_price = weights.get("price_fit", 0.20)
        w_rating = weights.get("rating_quality", 0.20)
        w_relevance = weights.get("relevance", 0.15)
        w_avail = weights.get("availability", 0.10)
        w_seller = weights.get("seller_quality", 0.10)

        for prod in products:
            reasons: List[str] = []
            drawbacks: List[str] = []
            why_not_higher: List[str] = []

            # 1. Price evaluation
            best_offer = min(prod.offers, key=lambda o: o.price_amount or float("inf")) if prod.offers else None
            price_val = best_offer.price_amount if best_offer else None
            price_score = 0.7  # neutral default

            if price_val is not None:
                if intent.budget.max:
                    if price_val <= intent.budget.max:
                        savings = intent.budget.max - price_val
                        pct_saved = int((savings / intent.budget.max) * 100)
                        if pct_saved > 5:
                            reasons.append(f"Well under your budget ({pct_saved}% lower than maximum)")
                            price_score = 1.0
                        else:
                            reasons.append("Comfortably within your stated budget")
                            price_score = 0.95
                    else:
                        over_pct = int(((price_val - intent.budget.max) / intent.budget.max) * 100)
                        drawbacks.append(f"Exceeds target budget by {over_pct}%")
                        why_not_higher.append("Price is higher than your specified budget constraint")
                        price_score = max(0.1, 1.0 - (over_pct / 100.0))
            else:
                why_not_higher.append("Price could not be verified in real-time across retailers")

            # 2. Requirement matching via category rules
            matched_rules = 0
            applicable_rules = 0

            for rule in rules:
                p_load = rule.payload
                rule_match = p_load.get("match", [])
                # Check if user query or use_cases trigger this rule
                query_corpus = f"{intent.raw_query.lower()} {' '.join(intent.use_cases).lower()}"
                is_active = any(trigger.lower() in query_corpus for trigger in rule_match)
                if is_active:
                    applicable_rules += 1
                    conditions = p_load.get("conditions", [])
                    cond_met = True
                    for c in conditions:
                        attr_key = c.get("attribute")
                        attr_val = prod.specs.get(attr_key)
                        if not evaluate_condition(attr_val, c.get("op", "=="), c.get("value")):
                            cond_met = False
                            break

                    if cond_met:
                        matched_rules += 1
                        reasons.append(f"{p_load.get('label', 'Matches requirement')}")
                    else:
                        drawbacks.append(f"May not fully satisfy: {p_load.get('label')}")
                        why_not_higher.append(f"Did not meet ideal requirement for {p_load.get('label')}")

            req_score = (matched_rules / applicable_rules) if applicable_rules > 0 else 0.85

            # 3. Rating & review quality
            rating_score = 0.6
            if prod.rating:
                rating_score = min(prod.rating / 5.0, 1.0)
                if prod.rating >= 4.5:
                    rev_txt = f"from {prod.review_count:,} reviews" if prod.review_count else "from customer ratings"
                    reasons.append(f"High customer satisfaction rating ({prod.rating}★ {rev_txt})")
                elif prod.rating < 4.0:
                    drawbacks.append(f"Customer rating is {prod.rating}★")
                    why_not_higher.append("Rating is lower than top competitors")

            # 4. Brand preference
            if intent.preferred_brands:
                prod_brand = (prod.brand or "").lower()
                if any(b.lower() in prod_brand for b in intent.preferred_brands):
                    reasons.append(f"Matches your brand preference for {prod.brand}")
                    req_score = min(1.0, req_score + 0.1)

            # 5. Availability & offer coverage
            avail_score = 0.5
            if best_offer and best_offer.availability == "in_stock":
                avail_score = 1.0
                if len(prod.offers) > 1:
                    reasons.append(f"Multiple seller offers compared across {len(prod.offers)} retailers")
            elif best_offer and best_offer.availability == "out_of_stock":
                avail_score = 0.1
                drawbacks.append("Currently reported out of stock at major sellers")
                why_not_higher.append("Limited stock availability")

            # Composite weighted calculation
            composite = (
                (req_score * w_req) +
                (price_score * w_price) +
                (rating_score * w_rating) +
                (avail_score * w_avail) +
                (0.85 * w_relevance) +
                (0.85 * w_seller)
            )

            final_score = int(round(composite * 100))
            final_score = max(35, min(99, final_score))

            breakdown = {
                "match_score": final_score,
                "reasons": reasons[:4],
                "drawbacks": drawbacks[:3],
                "why_not_higher": why_not_higher[:2],
                "price_score": round(price_score, 2),
                "requirement_score": round(req_score, 2),
                "rating_score": round(rating_score, 2),
            }

            scored.append((prod, composite, breakdown))

        # Sort descending by composite score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
