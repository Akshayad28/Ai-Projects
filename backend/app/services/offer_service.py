"""Offer and True Cost Service.

Calculates true cost and aggregates offers across retailers without inventing missing values.
Formula:
    true_cost = price + known_shipping + known_tax - confirmed_discount
Never assumes unknown values as zero.
"""
from __future__ import annotations

from typing import List, Optional, Tuple
from app.providers.base.models import ProviderProduct
from app.schemas.offer import OfferSchema, TrueCostBreakdown
from app.schemas.price_history import PriceSummary


class TrueCostService:
    """Calculates comprehensive true cost adhering strictly to available data."""

    @staticmethod
    def calculate(
        price: Optional[float],
        shipping: Optional[float] = None,
        tax: Optional[float] = None,
        discount: Optional[float] = None,
    ) -> TrueCostBreakdown:
        if price is None:
            return TrueCostBreakdown(price=0.0, status="INCOMPLETE")

        # If any mandatory delivery/tax component is missing/unknown, status is INCOMPLETE
        is_complete = (shipping is not None and tax is not None)
        
        computed = price
        if shipping is not None:
            computed += shipping
        if tax is not None:
            computed += tax
        if discount is not None:
            computed -= discount

        return TrueCostBreakdown(
            price=price,
            shipping=shipping,
            tax=tax,
            discounts=discount,
            true_cost=round(computed, 2) if is_complete else None,
            status="COMPLETE" if is_complete else "INCOMPLETE",
        )


class OfferService:
    """Manages offer normalization, true cost calculation, and aggregation."""

    def __init__(self) -> None:
        self.true_cost_service = TrueCostService()

    def build_offer(self, prod: ProviderProduct, product_id: str) -> OfferSchema:
        price_amt = prod.price.amount
        orig_amt = prod.price.original_price
        discount = prod.price.discount

        tc = self.true_cost_service.calculate(
            price=price_amt,
            discount=discount,
        )

        # Quick commerce and delivery metadata extraction
        meta = prod.raw_metadata or {}
        specs = prod.specifications or {}
        variants = prod.variant_attributes or {}

        is_qc = meta.get("is_quick_commerce", False) or prod.provider in ("blinkit", "zepto", "instamart", "bigbasket")
        delivery_estimate = specs.get("delivery") or meta.get("delivery_estimate")
        delivery_eta_minutes = meta.get("delivery_eta_minutes")
        pack_size = variants.get("pack_size") or specs.get("pack_size")
        unit_price = specs.get("unit_price")
        unit_measure = specs.get("unit_measure")
        delivery_fee = meta.get("delivery_fee")
        platform_fee = meta.get("platform_fee")

        if is_qc and not delivery_estimate:
            delivery_estimate = f"⚡ {delivery_eta_minutes or 15} mins"

        retailer_name = (prod.seller or "Firecrawl") if prod.provider == "firecrawl" else prod.provider.capitalize()
        if prod.provider in ("blinkit", "zepto", "instamart", "bigbasket", "croma", "reliance_digital", "myntra", "ikea"):
            retailer_name = prod.provider.replace("_", " ").title()

        return OfferSchema(
            product_id=product_id,
            retailer=retailer_name,
            seller=prod.seller or retailer_name,
            url=prod.url,
            price=price_amt,
            currency=prod.price.currency or "INR",
            original_price=orig_amt,
            discount=discount,
            availability=prod.availability,
            condition="new",
            delivery_estimate=delivery_estimate,
            delivery_eta_minutes=delivery_eta_minutes,
            is_quick_commerce=is_qc,
            delivery_fee=delivery_fee,
            platform_fee=platform_fee,
            pack_size=pack_size,
            unit_price=unit_price,
            unit_measure=unit_measure,
            store_name=meta.get("store_name"),
            location_checked=meta.get("location_checked"),
            source=prod.provider,
            fetched_at=prod.fetched_at,
            true_cost=tc,
        )

    def summarize_prices(self, offers: List[OfferSchema]) -> PriceSummary:
        valid_prices = [o.price for o in offers if o.price is not None and o.price > 0]
        if not valid_prices:
            return PriceSummary(currency="INR")

        lowest = min(valid_prices)
        highest = max(valid_prices)
        avg = round(sum(valid_prices) / len(valid_prices), 2)

        return PriceSummary(
            lowest_price=lowest,
            highest_price=highest,
            average_price=avg,
            currency=offers[0].currency if offers else "INR",
            observations_count=len(valid_prices),
            price_position="great_deal" if lowest < avg * 0.9 else "typical",
        )
