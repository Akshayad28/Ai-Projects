"""Product Identity Matching Engine.

Implements cross-retailer product deduplication, variant disambiguation,
and canonical clustering rules:
1. Exact Universal Identifiers (GTIN, UPC, EAN, ISBN)
2. Normalized Brand + Model Code (MPN, Manufacturer Part Number)
3. Normalized Brand + Core Model Name + Variant Key (e.g., "Sony WH-1000XM5", "Apple M3 16GB 512GB")
4. Strict Rejection of Uncertain Matches:
   - Differentiates variants by RAM, Storage, Screen Size, or Generation
   - Prevents merging Base vs. Pro / Ultra models
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from app.schemas.domain import RawOffer, RawProduct


# Noise words commonly injected into online shopping titles that obscure identity
TITLE_NOISE_WORDS: Set[str] = {
    "buy", "online", "best", "deal", "deals", "discount", "discounted", "sale",
    "offer", "offers", "free", "shipping", "fast", "delivery", "genuine",
    "original", "authentic", "india", "usa", "uk", "official", "warranty",
    "year", "latest", "new", "hot", "trending", "lowest", "price", "cheapest",
    "limited", "stock", "pack", "piece", "combo", "special", "edition"
}

# Regex to detect key variant attributes from product text
RAM_PATTERN = re.compile(r"\b(\d{1,3})\s*(?:gb|gigabytes?)\s*(?:ram|memory)?\b", re.IGNORECASE)
STORAGE_PATTERN = re.compile(r"\b(\d{1,4})\s*(?:gb|tb)\s*(?:ssd|hdd|storage|emmc|rom|nvme)?\b", re.IGNORECASE)
SCREEN_PATTERN = re.compile(r"\b(\d{1,2}(?:\.\d{1,2})?)\s*(?:inch|inches|\"|-inch)\b", re.IGNORECASE)
MODEL_NO_PATTERN = re.compile(r"\b([a-z]{1,4}[-_]?\d{3,5}[a-z0-9-_]*)\b", re.IGNORECASE)

# Quick commerce & Grocery / Pack size patterns
VOLUME_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(l|litre|litres|liter|liters|ml|millilitres?|milliliters?)\b", re.IGNORECASE)
WEIGHT_PATTERN = re.compile(r"\b(\d+(?:\.\d+)?)\s*(kg|kgs|kilograms?|gm|gms|g|grams?)\b", re.IGNORECASE)
PACK_COUNT_PATTERN = re.compile(r"\b(?:pack\s*of|pack\s*-\s*|set\s*of|combo\s*of)\s*(\d{1,3})\b|\b(\d{1,3})\s*(?:pack|packs|pk|pcs|pieces)\b", re.IGNORECASE)
SHOE_SIZE_PATTERN = re.compile(r"\b(?:uk|us|eu|size)\s*[:\s]*(\d{1,2}(?:\.\d)?)\b", re.IGNORECASE)
CLOTHING_SIZE_PATTERN = re.compile(r"\b(?:size\s*[:\s]*)?(xs|s|m|l|xl|xxl|2xl|3xl)\b", re.IGNORECASE)


def normalize_volume_to_ml(val_str: str, unit_str: str) -> float:
    """Converts volume string to milliliters for clean numerical comparison."""
    val = float(val_str)
    unit = unit_str.lower()
    if unit in ("l", "litre", "litres", "liter", "liters"):
        return val * 1000.0
    return val


def normalize_weight_to_grams(val_str: str, unit_str: str) -> float:
    """Converts weight string to grams for clean numerical comparison."""
    val = float(val_str)
    unit = unit_str.lower()
    if unit in ("kg", "kgs", "kilograms?"):
        return val * 1000.0
    return val


def extract_variant_signatures(text: str) -> Dict[str, str]:
    """Extracts distinctive variant properties to prevent merging distinct variants."""
    text_lower = text.lower()
    signatures: Dict[str, str] = {}

    # 1. RAM
    ram_match = RAM_PATTERN.search(text_lower)
    if ram_match:
        signatures["ram"] = f"{ram_match.group(1)}gb"

    # 2. Storage
    storage_matches = STORAGE_PATTERN.findall(text_lower)
    if storage_matches:
        signatures["storage"] = storage_matches[-1].lower()

    # 3. Screen size
    screen_match = SCREEN_PATTERN.search(text_lower)
    if screen_match:
        signatures["screen"] = screen_match.group(1)

    # 4. Product tier / edition
    for tier in ["pro max", "pro", "ultra", "plus", "mini", "lite", "max", "air", "fe"]:
        if re.search(rf"\b{tier}\b", text_lower):
            signatures["tier"] = tier
            break

    # 5. Quick-commerce Volume (e.g. 750ml, 1L, 2L)
    vol_match = VOLUME_PATTERN.search(text_lower)
    if vol_match:
        ml = normalize_volume_to_ml(vol_match.group(1), vol_match.group(2))
        signatures["volume_ml"] = f"{int(ml)}ml"

    # 6. Weight (e.g. 500g, 1kg)
    # Check that it's not a storage gb match
    wt_matches = WEIGHT_PATTERN.findall(text_lower)
    for num_str, unit_str in wt_matches:
        if unit_str.lower() in ("g", "gm", "gms") and re.search(rf"\b{num_str}\s*gb\b", text_lower):
            continue
        g = normalize_weight_to_grams(num_str, unit_str)
        signatures["weight_g"] = f"{int(g)}g"
        break

    # 7. Pack count (e.g. Pack of 6 vs 1)
    pack_match = PACK_COUNT_PATTERN.search(text_lower)
    if pack_match:
        count = pack_match.group(1) or pack_match.group(2)
        signatures["pack_count"] = count

    # 8. Shoe / Footwear Size
    shoe_match = SHOE_SIZE_PATTERN.search(text_lower)
    if shoe_match:
        signatures["shoe_size"] = shoe_match.group(1)

    # 9. Apparel Size
    clothing_match = CLOTHING_SIZE_PATTERN.search(text_lower)
    if clothing_match and not ram_match:  # avoid confusion if e.g. "m" stands for something else
        signatures["apparel_size"] = clothing_match.group(1).lower()

    return signatures


def are_variants_compatible(p1: Any, p2: Any) -> bool:
    """Verifies that two products (or variant signature dicts) do not represent incompatible physical variants."""
    if isinstance(p1, dict) and isinstance(p2, dict):
        sig1 = p1
        sig2 = p2
    else:
        t1 = f"{getattr(p1, 'title', '')} {getattr(p1, 'description', '') or ''}"
        t2 = f"{getattr(p2, 'title', '')} {getattr(p2, 'description', '') or ''}"
        sig1 = extract_variant_signatures(t1)
        sig2 = extract_variant_signatures(t2)

    # 1. RAM (e.g. 8GB vs 16GB)
    if "ram" in sig1 and "ram" in sig2 and sig1["ram"] != sig2["ram"]:
        return False

    # 2. Storage (e.g. 256GB vs 512GB)
    if "storage" in sig1 and "storage" in sig2 and sig1["storage"] != sig2["storage"]:
        return False

    # 3. Product Tier (e.g. iPad Air vs iPad Pro)
    if "tier" in sig1 and "tier" in sig2 and sig1["tier"] != sig2["tier"]:
        return False

    # 4. Quick-Commerce Volume (e.g. 750ml vs 1L vs 2L)
    if "volume_ml" in sig1 and "volume_ml" in sig2 and sig1["volume_ml"] != sig2["volume_ml"]:
        return False

    # 5. Weight (e.g. 500g vs 1kg)
    if "weight_g" in sig1 and "weight_g" in sig2 and sig1["weight_g"] != sig2["weight_g"]:
        return False

    # 6. Pack count (e.g. pack of 1 vs pack of 6)
    p1_count = sig1.get("pack_count", "1")
    p2_count = sig2.get("pack_count", "1")
    if ("pack_count" in sig1 or "pack_count" in sig2) and p1_count != p2_count:
        return False

    # 7. Shoe Size (e.g. UK 8 vs UK 9)
    if "shoe_size" in sig1 and "shoe_size" in sig2 and sig1["shoe_size"] != sig2["shoe_size"]:
        return False

    # 8. Apparel Size (e.g. M vs XL)
    if "apparel_size" in sig1 and "apparel_size" in sig2 and sig1["apparel_size"] != sig2["apparel_size"]:
        return False

    return True


def compute_canonical_identity_key(
    product: Optional[RawProduct] = None,
    *,
    brand: Optional[str] = None,
    title: Optional[str] = None,
    gtin: Optional[str] = None,
    ean: Optional[str] = None,
    upc: Optional[str] = None,
    mpn: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Generates a stable, deterministic clustering key for a physical product."""
    p_gtin = gtin or (product.gtin if product else None)
    p_ean = ean or (product.ean if product else None)
    p_upc = upc or (product.upc if product else None)
    p_brand = brand or (product.brand if product else None)
    p_title = title or (product.title if product else "")
    p_mpn = mpn or (product.mpn if product else None)
    p_model = model or (product.model if product else None)

    # 1. Highest confidence: Global Trade Item Numbers (GTIN / EAN / UPC / ISBN)
    if p_gtin:
        return f"gtin:{p_gtin.strip()}"
    if p_ean:
        return f"ean:{p_ean.strip()}"
    if p_upc:
        return f"upc:{p_upc.strip()}"

    brand_str = (p_brand or "generic").strip().lower()

    # 2. Manufacturer Part Number (MPN) or Model Number
    if p_mpn and len(p_mpn.strip()) >= 3:
        clean_mpn = re.sub(r"[^\w-]", "", p_mpn.strip().lower())
        return f"mpn:{brand_str}:{clean_mpn}"

    if p_model and len(p_model.strip()) >= 3:
        clean_model = re.sub(r"[^\w-]", "", p_model.strip().lower())
        return f"model:{brand_str}:{clean_model}"

    # 3. Model number extracted via regex
    model_match = MODEL_NO_PATTERN.search(p_title)
    if model_match and len(model_match.group(1)) >= 4:
        clean_extracted_model = model_match.group(1).lower().replace("_", "-")
        return f"ext_model:{brand_str}:{clean_extracted_model}"

    # 4. Normalized Title Clustering + Variant Signatures (including pack size/volume)
    clean_title = p_title.lower()
    clean_title = re.sub(r"[^\w\s\.-]", " ", clean_title)
    tokens = [
        t for t in clean_title.split()
        if len(t) > 1 and t not in TITLE_NOISE_WORDS and t != brand_str
    ]
    core_title = "-".join(tokens[:5])

    variants = extract_variant_signatures(p_title)
    var_token = "-".join(f"{k}:{v}" for k, v in sorted(variants.items())) if variants else "base"

    return f"title:{brand_str}:{core_title}:{var_token}"


def compute_identity_key(brand: Optional[str], title: str, model: Optional[str] = None, specs: Optional[dict] = None) -> str:
    """Generates a stable identity key from brand and title components."""
    clean_brand = (brand or "generic").strip().lower()
    model_match = MODEL_NO_PATTERN.search(title)
    if model_match and len(model_match.group(1)) >= 4:
        clean_extracted_model = model_match.group(1).lower().replace("_", "-")
        return f"{clean_brand}:{clean_extracted_model}"

    clean_title = title.lower()
    clean_title = re.sub(r"[^\w\s\.-]", " ", clean_title)
    tokens = [
        t for t in clean_title.split()
        if len(t) > 1 and t not in TITLE_NOISE_WORDS and t != clean_brand
    ]
    core_title = "-".join(tokens[:4])
    return f"{clean_brand}:{core_title}"


def cluster_and_merge_offers(raw_products: List[RawProduct]) -> List[RawProduct]:
    """Clusters provider items into canonical products and aggregates distinct retailer offers.

    Enforces strict variant safety: rejects clustering if variant attributes conflict.
    """
    clusters: Dict[str, RawProduct] = {}

    for p in raw_products:
        key = compute_canonical_identity_key(p)

        if key not in clusters:
            clusters[key] = p
        else:
            existing = clusters[key]

            # Variant safety check: If conflict detected, treat as separate canonical product
            if not are_variants_compatible(existing, p):
                fallback_key = f"{key}:diff:{p.external_id}"
                clusters[fallback_key] = p
                continue

            # Merge offers
            existing_retailers = {o.retailer_name.lower() for o in existing.offers}
            for off in p.offers:
                r_name = off.retailer_name.lower()
                if r_name not in existing_retailers:
                    existing.offers.append(off)
                    existing_retailers.add(r_name)
                else:
                    # Update price if current observation has a lower verified price
                    for curr_off in existing.offers:
                        if curr_off.retailer_name.lower() == r_name:
                            if off.price_amount and (curr_off.price_amount is None or off.price_amount < curr_off.price_amount):
                                curr_off.price_amount = off.price_amount
                                curr_off.original_price = off.original_price or curr_off.original_price
                                curr_off.url = off.url or curr_off.url
                                curr_off.affiliate_url = off.affiliate_url or curr_off.affiliate_url
                                curr_off.checked_at = off.checked_at

            # Merge images
            for img in p.image_urls:
                if img not in existing.image_urls:
                    existing.image_urls.append(img)

            # Preserve best rating & review count
            if p.rating and (not existing.rating or p.rating > existing.rating):
                existing.rating = p.rating
                existing.review_count = p.review_count or existing.review_count

            # Supplement missing specs
            for sk, sv in p.specs.items():
                if sk not in existing.specs:
                    existing.specs[sk] = sv

    return list(clusters.values())
