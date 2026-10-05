"""Unit tests for Price and True Cost Service."""
from __future__ import annotations

from app.schemas.offer import OfferSchema
from app.services.offer_service import OfferService, TrueCostService


def test_true_cost_incomplete_when_shipping_tax_unknown():
    """Critical: If shipping/tax are unknown, do NOT assume zero. Status must be INCOMPLETE."""
    res = TrueCostService.calculate(price=34999.0, shipping=None, tax=None)
    assert res.price == 34999.0
    assert res.shipping is None
    assert res.tax is None
    assert res.true_cost is None
    assert res.status == "INCOMPLETE"


def test_true_cost_complete_when_all_values_known():
    res = TrueCostService.calculate(
        price=34999.0,
        shipping=150.0,
        tax=0.0,
        discount=1000.0,
    )
    assert res.price == 34999.0
    assert res.shipping == 150.0
    assert res.discounts == 1000.0
    assert res.true_cost == 34149.0
    assert res.status == "COMPLETE"


def test_price_summarization():
    service = OfferService()
    offers = [
        OfferSchema(
            product_id="test",
            retailer="Amazon",
            price=34999.0,
            currency="INR",
            source="amazon",
            fetched_at="2026-10-04T00:00:00Z",
        ),
        OfferSchema(
            product_id="test",
            retailer="Flipkart",
            price=33499.0,
            currency="INR",
            source="flipkart",
            fetched_at="2026-10-04T00:00:00Z",
        ),
    ]

    summary = service.summarize_prices(offers)
    assert summary.lowest_price == 33499.0
    assert summary.highest_price == 34999.0
    assert summary.average_price == 34249.0
    assert summary.observations_count == 2
