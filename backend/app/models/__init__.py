"""ShopBuddy Database Models Package."""
from __future__ import annotations

from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.product_identifier import ProductIdentifier
from app.models.retailer import Retailer
from app.models.seller import Seller
from app.models.offer import Offer
from app.models.price_history import PriceHistory
from app.models.availability_history import AvailabilityHistory
from app.models.review import Review, ReviewAnalysis
from app.models.product_source import ProductSource
from app.models.search import SearchRecord, SearchResultRecord

__all__ = [
    "Product",
    "ProductVariant",
    "ProductIdentifier",
    "Retailer",
    "Seller",
    "Offer",
    "PriceHistory",
    "AvailabilityHistory",
    "Review",
    "ReviewAnalysis",
    "ProductSource",
    "SearchRecord",
    "SearchResultRecord",
]
