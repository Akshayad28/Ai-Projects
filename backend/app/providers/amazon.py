"""Amazon Product Advertising API 5.0 (PA-API / Creators API) Provider.

Implements the official Amazon Creators / Associates PA-API 5.0 contract with
AWS SigV4 HMAC-SHA256 request signing, marketplace routing, SearchItems,
GetItems, and GetVariations operations.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
import json
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.resilience import provider_bucket, with_retries
from app.providers.base import ProductProvider, raise_for_status
from app.schemas.domain import (
    ProviderSearchParams,
    RawOffer,
    RawProduct,
    now_utc,
)

log = get_logger(__name__)

# Region and Host mappings for Amazon PA-API 5.0
MARKETPLACE_CONFIG: Dict[str, Tuple[str, str, str]] = {
    "IN": ("webservices.amazon.in", "eu-west-1", "www.amazon.in"),
    "US": ("webservices.amazon.com", "us-east-1", "www.amazon.com"),
    "GB": ("webservices.amazon.co.uk", "eu-west-1", "www.amazon.co.uk"),
    "DE": ("webservices.amazon.de", "eu-west-1", "www.amazon.de"),
    "CA": ("webservices.amazon.ca", "us-east-1", "www.amazon.ca"),
    "AU": ("webservices.amazon.com.au", "us-west-2", "www.amazon.com.au"),
    "JP": ("webservices.amazon.co.jp", "us-west-2", "www.amazon.co.jp"),
}


def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
    k_date = _sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = _sign(k_date, region_name)
    k_service = _sign(k_region, service_name)
    k_signing = _sign(k_service, "aws4_request")
    return k_signing


class AmazonProvider(ProductProvider):
    name: ClassVar[str] = "amazon"
    label: ClassVar[str] = "Amazon"
    countries: ClassVar[Set[str]] = {"IN", "US", "GB", "DE", "CA", "AU", "JP"}
    rate_limit_per_second: ClassVar[float] = 1.0  # Amazon default PA-API limit is 1 TPS
    required_env: ClassVar[List[str]] = [
        "AMAZON_ACCESS_KEY",
        "AMAZON_SECRET_KEY",
        "AMAZON_ASSOCIATE_TAG",
    ]

    def is_configured(self) -> bool:
        settings = get_settings()
        return bool(
            (settings.amazon_paapi_access_key or settings.provider_api_key)
            and (settings.amazon_paapi_secret_key)
            and (settings.amazon_paapi_partner_tag or settings.affiliate_api_key)
        )

    def _get_credentials(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        settings = get_settings()
        access_key = settings.amazon_paapi_access_key or settings.provider_api_key
        secret_key = settings.amazon_paapi_secret_key
        partner_tag = settings.amazon_paapi_partner_tag or settings.affiliate_api_key
        return access_key, secret_key, partner_tag

    def _create_signed_headers(
        self,
        host: str,
        region: str,
        target: str,
        payload_str: str,
        access_key: str,
        secret_key: str,
    ) -> Dict[str, str]:
        """Calculates standard AWS SigV4 authentication headers for PA-API 5.0."""
        service = "ProductAdvertisingAPI"
        now = datetime.datetime.now(datetime.timezone.utc)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")

        canonical_uri = "/paapi5/searchitems" if "SearchItems" in target else (
            "/paapi5/getitems" if "GetItems" in target else "/paapi5/getvariations"
        )
        canonical_querystring = ""
        canonical_headers = (
            f"content-encoding:amz-1.0\n"
            f"content-type:application/json; charset=utf-8\n"
            f"host:{host}\n"
            f"x-amz-date:{amz_date}\n"
            f"x-amz-target:{target}\n"
        )
        signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"
        payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        canonical_request = (
            f"POST\n"
            f"{canonical_uri}\n"
            f"{canonical_querystring}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{payload_hash}"
        )

        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        string_to_sign = (
            f"AWS4-HMAC-SHA256\n"
            f"{amz_date}\n"
            f"{credential_scope}\n"
            f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
        )

        signing_key = _get_signature_key(secret_key, date_stamp, region, service)
        signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization_header = (
            f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )

        return {
            "Content-Type": "application/json; charset=utf-8",
            "Content-Encoding": "amz-1.0",
            "X-Amz-Date": amz_date,
            "X-Amz-Target": target,
            "Authorization": authorization_header,
            "Host": host,
        }

    async def search_products(self, params: ProviderSearchParams) -> List[RawProduct]:
        if not self.is_configured():
            return []

        access_key, secret_key, partner_tag = self._get_credentials()
        if not access_key or not secret_key or not partner_tag:
            return []

        country = params.country.upper() if params.country else "IN"
        host, region, marketplace_domain = MARKETPLACE_CONFIG.get(country, MARKETPLACE_CONFIG["IN"])

        await provider_bucket(self.name, self.rate_limit_per_second).acquire()

        query = params.intent.provider_query or params.query
        target = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"
        endpoint = f"https://{host}/paapi5/searchitems"

        payload = {
            "Keywords": query,
            "SearchIndex": "All",
            "ItemCount": min(params.limit, 10),
            "PartnerTag": partner_tag,
            "PartnerType": "Associates",
            "Marketplace": f"www.amazon.{'co.uk' if country == 'GB' else ('com.au' if country == 'AU' else country.lower())}",
            "Resources": [
                "Images.Primary.Large",
                "ItemInfo.Title",
                "ItemInfo.ByLineInfo",
                "ItemInfo.Features",
                "ItemInfo.Classifications",
                "Offers.Listings.Price",
                "Offers.Listings.Availability.Message",
                "Offers.Listings.MerchantInfo",
            ],
        }

        payload_str = json.dumps(payload)
        headers = self._create_signed_headers(
            host=host,
            region=region,
            target=target,
            payload_str=payload_str,
            access_key=access_key,
            secret_key=secret_key,
        )

        async def _call() -> dict:
            async with httpx.AsyncClient(timeout=get_settings().provider_timeout_seconds) as client:
                res = await client.post(endpoint, headers=headers, content=payload_str)
                raise_for_status(res, self.name)
                return res.json()

        try:
            data = await with_retries(_call, attempts=2)
        except Exception as exc:
            log.warning("Amazon PA-API search failed", extra={"query": query, "error": str(exc)})
            return []

        items = data.get("SearchResult", {}).get("Items", [])
        products: List[RawProduct] = []

        for item in items:
            asin = item.get("ASIN")
            item_info = item.get("ItemInfo", {})
            title_obj = item_info.get("Title", {})
            title = title_obj.get("DisplayValue")
            if not asin or not title:
                continue

            brand = item_info.get("ByLineInfo", {}).get("Brand", {}).get("DisplayValue")
            url = item.get("DetailPageURL")
            image_url = item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL")

            # Extract features / specs
            features_list = item_info.get("Features", {}).get("DisplayValues", [])
            specs = {"features": features_list} if features_list else {}

            # Offers
            offers: List[RawOffer] = []
            offers_container = item.get("Offers", {}).get("Listings", [])
            for listing in offers_container:
                price_obj = listing.get("Price", {})
                amount = price_obj.get("Amount")
                currency = price_obj.get("Currency") or params.currency

                merchant = listing.get("MerchantInfo", {}).get("Name", "Amazon")
                availability_msg = listing.get("Availability", {}).get("Message", "").lower()
                availability = "in_stock" if "in stock" in availability_msg or not availability_msg else "limited"

                offers.append(
                    RawOffer(
                        provider=self.name,
                        retailer_name="Amazon",
                        retailer_domain=marketplace_domain,
                        seller_name=merchant,
                        country=country,
                        price_amount=float(amount) if amount else None,
                        currency=currency,
                        availability=availability,
                        url=url,
                        affiliate_url=url,
                        checked_at=now_utc(),
                    )
                )

            # Fallback offer if none listed
            if not offers:
                offers.append(
                    RawOffer(
                        provider=self.name,
                        retailer_name="Amazon",
                        retailer_domain=marketplace_domain,
                        seller_name="Amazon",
                        country=country,
                        url=url,
                        affiliate_url=url,
                        checked_at=now_utc(),
                    )
                )

            raw = RawProduct(
                provider=self.name,
                external_id=asin,
                asin=asin,
                title=title,
                brand=brand,
                url=url,
                image_urls=[image_url] if image_url else [],
                specs=specs,
                country=country,
                offers=offers,
                is_demo=False,
            )
            products.append(raw)

        return products

    async def get_product(self, external_id: str, country: str) -> Optional[RawProduct]:
        if not self.is_configured():
            return None

        access_key, secret_key, partner_tag = self._get_credentials()
        if not access_key or not secret_key or not partner_tag:
            return None

        c = country.upper() if country else "IN"
        host, region, marketplace_domain = MARKETPLACE_CONFIG.get(c, MARKETPLACE_CONFIG["IN"])

        target = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.GetItems"
        endpoint = f"https://{host}/paapi5/getitems"

        payload = {
            "ItemIds": [external_id],
            "PartnerTag": partner_tag,
            "PartnerType": "Associates",
            "Marketplace": f"www.amazon.{'co.uk' if c == 'GB' else ('com.au' if c == 'AU' else c.lower())}",
            "Resources": [
                "Images.Primary.Large",
                "ItemInfo.Title",
                "ItemInfo.ByLineInfo",
                "ItemInfo.Features",
                "Offers.Listings.Price",
                "Offers.Listings.Availability.Message",
                "Offers.Listings.MerchantInfo",
            ],
        }

        payload_str = json.dumps(payload)
        headers = self._create_signed_headers(
            host=host,
            region=region,
            target=target,
            payload_str=payload_str,
            access_key=access_key,
            secret_key=secret_key,
        )

        try:
            async with httpx.AsyncClient(timeout=get_settings().provider_timeout_seconds) as client:
                res = await client.post(endpoint, headers=headers, content=payload_str)
                raise_for_status(res, self.name)
                data = res.json()
        except Exception as exc:
            log.warning("Amazon GetItems failed", extra={"asin": external_id, "error": str(exc)})
            return None

        items = data.get("ItemsResult", {}).get("Items", [])
        if not items:
            return None

        item = items[0]
        asin = item.get("ASIN")
        item_info = item.get("ItemInfo", {})
        title = item_info.get("Title", {}).get("DisplayValue")
        brand = item_info.get("ByLineInfo", {}).get("Brand", {}).get("DisplayValue")
        url = item.get("DetailPageURL")
        image_url = item.get("Images", {}).get("Primary", {}).get("Large", {}).get("URL")

        offers: List[RawOffer] = []
        for listing in item.get("Offers", {}).get("Listings", []):
            price_obj = listing.get("Price", {})
            amount = price_obj.get("Amount")
            currency = price_obj.get("Currency") or "INR"
            merchant = listing.get("MerchantInfo", {}).get("Name", "Amazon")

            offers.append(
                RawOffer(
                    provider=self.name,
                    retailer_name="Amazon",
                    retailer_domain=marketplace_domain,
                    seller_name=merchant,
                    country=c,
                    price_amount=float(amount) if amount else None,
                    currency=currency,
                    url=url,
                    affiliate_url=url,
                    checked_at=now_utc(),
                )
            )

        return RawProduct(
            provider=self.name,
            external_id=asin,
            asin=asin,
            title=title or external_id,
            brand=brand,
            url=url,
            image_urls=[image_url] if image_url else [],
            country=c,
            offers=offers,
            is_demo=False,
        )
