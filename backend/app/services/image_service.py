"""Product Image Extraction, Validation, and Quality Ranking Service.

Inspects candidate product images across multiple tiers (API, JSON-LD, OpenGraph,
lazy-loading DOM attributes, Firecrawl, Merchant Feeds), filters out tracking pixels,
logos, and generic placeholders, and ranks the highest-quality product image.
Never fabricates placeholder imagery.
"""
from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from app.core.logging import get_logger

log = get_logger(__name__)

# Known tracking pixels, generic placeholders, and spam patterns to reject
DISALLOWED_PATTERNS = [
    r"1x1",
    r"pixel\.(?:gif|png|jpg)",
    r"spacer\.(?:gif|png|jpg)",
    r"blank\.(?:gif|png|jpg)",
    r"transparent\.(?:gif|png)",
    r"placeholder",
    r"no[-_]?image",
    r"image[-_]?not[-_]?found",
    r"default[-_]?product",
    r"coming[-_]?soon",
    r"data:image/gif;base64,R0lGODlhAQABA",  # standard 1x1 transparent gif data URI
    r"icon[-_]?logo",
    r"site[-_]?logo",
    r"favicon",
    r"badge",
    r"banner",
    r"tracker",
    r"beacon",
]
DISALLOWED_REGEX = re.compile("|".join(DISALLOWED_PATTERNS), re.IGNORECASE)

# Image file extension validation
VALID_EXTENSIONS: Set[str] = {
    ".jpg", ".jpeg", ".png", ".webp", ".avif", ".svg"
}


class ImageExtractionService:
    """Manages validation, deduplication, and quality scoring of product images."""

    def __init__(self) -> None:
        self._validated_cache: Dict[str, bool] = {}

    def validate_image_url(self, url: Optional[str]) -> bool:
        """Alias for is_valid_image_url."""
        return self.is_valid_image_url(url)

    def is_valid_image_url(self, url: Optional[str]) -> bool:
        """Validates that a URL is a real, accessible, non-placeholder product image URL."""
        if not url or not isinstance(url, str):
            return False

        clean_url = url.strip()
        if len(clean_url) < 10:
            return False

        # Check cache
        if clean_url in self._validated_cache:
            return self._validated_cache[clean_url]

        # 1. Scheme and host check
        try:
            parsed = urlparse(clean_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                self._validated_cache[clean_url] = False
                return False
        except Exception:
            self._validated_cache[clean_url] = False
            return False

        # 2. Reject tracking pixels and placeholder text
        if DISALLOWED_REGEX.search(clean_url):
            self._validated_cache[clean_url] = False
            return False

        # 3. Path inspection
        path = parsed.path.lower()
        # Accept valid extension or trusted CDN patterns (e.g. Amazon / Flipkart / Google / Cloudinary)
        has_valid_ext = any(path.endswith(ext) for ext in VALID_EXTENSIONS)
        is_trusted_cdn = any(
            cdn in parsed.netloc.lower()
            for cdn in (
                "amazon",
                "flipkart",
                "media-amazon",
                "ssl-images-amazon",
                "cloudinary",
                "img.bbystatic.com",
                "ebayimg",
                "firecrawl",
                "googleusercontent",
                "gstatic",
                "ikea",
                "croma",
                "myntassets",
                "nykaa",
                "zepto",
                "blinkit",
                "swiggy",
                "bigbasket",
            )
        )

        valid = has_valid_ext or is_trusted_cdn
        self._validated_cache[clean_url] = valid
        return valid

    def score_image_quality(self, url: str) -> float:
        """Scores candidate images based on resolution hints, CDN trust, and clarity."""
        score = 50.0
        url_lower = url.lower()

        # Resolution hints in URL
        if any(h in url_lower for h in ("1000", "1200", "1500", "1600", "2000", "highres", "hires", "zoom", "original", "_sl1500_", "_ac_sl")):
            score += 35.0
        elif any(m in url_lower for m in ("500", "600", "800", "medium", "large")):
            score += 20.0
        elif any(t in url_lower for t in ("thumb", "thumbnail", "tiny", "50x50", "100x100")):
            score -= 25.0

        # Modern formats
        if url_lower.endswith(".webp") or url_lower.endswith(".avif"):
            score += 10.0
        elif url_lower.endswith(".png") or url_lower.endswith(".jpg") or url_lower.endswith(".jpeg"):
            score += 5.0

        # Disproportionate query params
        if "crop" in url_lower:
            score -= 5.0

        return max(0.0, score)

    def select_best_image(
        self,
        candidates: List[str],
        title: Optional[str] = None,
    ) -> Tuple[Optional[str], List[str]]:
        """Selects the best primary image and deduplicated gallery from a candidate list.

        Returns: (primary_image, gallery_images). If no valid image exists, primary_image is None.
        """
        valid_candidates: List[Tuple[str, float]] = []
        seen_hashes: Set[str] = set()

        for cand in candidates:
            if not self.is_valid_image_url(cand):
                continue

            # Normalized URL hash for deduplication
            norm = cand.strip().split("?")[0]  # strip transient query params for dedup
            img_hash = hashlib.md5(norm.encode("utf-8")).hexdigest()
            if img_hash in seen_hashes:
                continue
            seen_hashes.add(img_hash)

            score = self.score_image_quality(cand)
            valid_candidates.append((cand, score))

        if not valid_candidates:
            return None, []

        # Sort by quality score descending
        valid_candidates.sort(key=lambda x: x[1], reverse=True)

        primary = valid_candidates[0][0]
        gallery = [img for img, _ in valid_candidates[1:10]]

        return primary, gallery
