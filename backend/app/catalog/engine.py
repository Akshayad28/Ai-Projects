"""Catalog loader and dynamic attribute extractor.

Transforms raw product data and provider specs into normalized, typed
attributes based on category definition rules stored in the database.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Category, CategoryAttribute, CategoryRule, CategoryWeight

log = get_logger(__name__)

_CATEGORIES_JSON_PATH = Path(__file__).parent / "categories.json"


async def seed_categories_if_empty(session: AsyncSession) -> None:
    """Seeds the category database tables from categories.json if empty."""
    res = await session.execute(select(Category).limit(1))
    if res.scalars().first() is not None:
        return

    if not _CATEGORIES_JSON_PATH.exists():
        log.warning(f"Category configuration file not found at {_CATEGORIES_JSON_PATH}")
        return

    with open(_CATEGORIES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    attribute_lib: Dict[str, dict] = data.get("attribute_library", {})
    default_weights: Dict[str, float] = data.get("default_weights", {})
    categories_data: List[dict] = data.get("categories", [])

    for cat_dict in categories_data:
        cat_id = cat_dict["id"]
        cat_obj = Category(
            id=cat_id,
            name=cat_dict["name"],
            department=cat_dict.get("department", "general"),
            keywords=cat_dict.get("keywords", []),
            description=cat_dict.get("description"),
            sort_order=cat_dict.get("sort_order", 100),
        )
        session.add(cat_obj)

        # Merge category attributes
        attr_list = cat_dict.get("attributes", [])
        for order, attr_def in enumerate(attr_list, start=1):
            use_key = attr_def.get("use")
            if use_key and use_key in attribute_lib:
                merged = {**attribute_lib[use_key], **attr_def}
                key = use_key
            else:
                merged = attr_def
                key = attr_def.get("key")

            if not key:
                continue

            patterns = merged.get("patterns", [])
            # Normalize pattern list to strings or json
            serialized_patterns = [p if isinstance(p, str) else json.dumps(p) for p in patterns]

            cat_attr = CategoryAttribute(
                category_id=cat_id,
                key=key,
                label=merged.get("label", key.replace("_", " ").title()),
                value_type=merged.get("value_type", "text"),
                unit=merged.get("unit"),
                extract_patterns=serialized_patterns,
                source_keys=merged.get("source_keys", []),
                filterable=merged.get("filterable", False),
                show_on_card=merged.get("show_on_card", False),
                comparable=merged.get("comparable", True),
                higher_is_better=merged.get("higher_is_better"),
                display_order=order,
            )
            session.add(cat_attr)

        # Weights
        cat_weights = {**default_weights, **cat_dict.get("weights", {})}
        for factor, w in cat_weights.items():
            session.add(CategoryWeight(category_id=cat_id, factor=factor, weight=float(w)))

        # Rules
        for r in cat_dict.get("rules", []):
            session.add(CategoryRule(category_id=cat_id, rule_type=r.get("rule_type", "requirement"), payload=r))

    await session.commit()
    log.info(f"Seeded {len(categories_data)} categories into database")


def resolve_category_from_text(query: str, categories: List[Category]) -> Tuple[Optional[str], float]:
    """Resolves category ID and confidence from natural language query terms."""
    q_clean = query.lower()
    best_cat: Optional[str] = None
    best_score = 0.0

    for cat in categories:
        if not cat.keywords:
            continue
        for kw in cat.keywords:
            kw_lower = kw.lower()
            if kw_lower == q_clean or f" {kw_lower} " in f" {q_clean} ":
                score = len(kw_lower) / max(len(q_clean), 1) + 0.5
                if score > best_score:
                    best_score = score
                    best_cat = cat.id

    return best_cat, min(best_score, 1.0)


def extract_attributes(title: str, description: Optional[str], specs: Dict[str, Any], attributes: List[CategoryAttribute]) -> Dict[str, Any]:
    """Extracts typed attributes dynamically using the category's configured patterns & source keys."""
    text_corpus = f"{title} {description or ''}"
    extracted: Dict[str, Any] = {}

    for attr in attributes:
        # 1. First check explicit specs from provider
        found_val = None
        for sk in attr.source_keys:
            for spec_key, spec_val in specs.items():
                if sk.lower() == spec_key.lower():
                    found_val = spec_val
                    break
            if found_val is not None:
                break

        # 2. If not found in specs, run regex patterns against title & description
        if found_val is None and attr.extract_patterns:
            for pat in attr.extract_patterns:
                try:
                    pattern_str = pat
                    multiply = 1.0
                    if pat.startswith("{"):
                        p_data = json.loads(pat)
                        pattern_str = p_data.get("regex", "")
                        multiply = float(p_data.get("multiply", 1.0))

                    m = re.search(pattern_str, text_corpus, re.IGNORECASE)
                    if m:
                        val_str = m.group(1).strip()
                        if attr.value_type == "number":
                            try:
                                found_val = float(val_str) * multiply
                                if found_val.is_integer():
                                    found_val = int(found_val)
                            except ValueError:
                                pass
                        elif attr.value_type == "bool":
                            found_val = True
                        else:
                            found_val = val_str
                        break
                except Exception:
                    continue

        if found_val is not None:
            extracted[attr.key] = found_val

    return extracted
