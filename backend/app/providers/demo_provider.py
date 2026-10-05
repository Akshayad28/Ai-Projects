"""Demo provider for development testing only.

ACTIVATION RULES:
1. ONLY active when DEMO_MODE=true in environment or configuration.
2. In production (ENVIRONMENT=production), DEMO_MODE is refused and errors out.
3. Every product produced by this provider is explicitly marked `is_demo=True`.
4. Multi-category coverage: Laptops, Mobile Phones, Air Fryers, Running Shoes,
   Office Chairs, Monitors, Washing Machines, Skincare, Power Tools, Suitcases, etc.
   Never restricted to just headphones.
"""
from __future__ import annotations

from typing import Any, ClassVar, List, Optional, Set
import re

from app.core.config import get_settings
from app.core.logging import get_logger
from app.providers.base import ProductProvider
from app.schemas.domain import (
    ProviderSearchParams,
    RawOffer,
    RawProduct,
    RawReview,
    now_utc,
)

log = get_logger(__name__)


# Multi-category demo catalog across diverse product lines
_DEMO_CATALOG = [
    # ── Laptops ──
    {
        "external_id": "demo-macbook-air-m3-16gb",
        "title": "Apple MacBook Air 15\" (M3 chip, 16GB RAM, 512GB SSD, Midnight)",
        "brand": "Apple",
        "category_id": "laptops",
        "category_hint": "laptops",
        "description": "15.3-inch Liquid Retina display, Apple M3 8-core CPU, 10-core GPU, 16GB Unified Memory, 512GB SSD, up to 18 hours battery life, MagSafe 3 charging.",
        "specs": {"cpu": "Apple M3 chip", "ram_gb": "16", "storage_gb": "512", "display_in": "15.3", "weight_kg": "1.51", "battery_hours": "18"},
        "rating": 4.8,
        "review_count": 2450,
        "image_urls": ["https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 134900.0, "currency": "INR", "original_price": 144900.0, "shipping": "Free", "warranty": "1 Year Apple Warranty", "url": "https://www.apple.com"},
            {"retailer": "Croma", "price": 136990.0, "currency": "INR", "original_price": 144900.0, "shipping": "Free Next-Day", "warranty": "1 Year Apple Warranty", "url": "https://www.croma.com"},
            {"retailer": "Reliance Digital", "price": 135900.0, "currency": "INR", "original_price": 144900.0, "shipping": "Free Delivery", "warranty": "1 Year Apple Warranty", "url": "https://www.reliancedigital.in"}
        ]
    },
    {
        "external_id": "demo-lenovo-loq-i7-rtx4060",
        "title": "Lenovo LOQ 15.6\" Gaming Laptop (Intel Core i7-14700HX, 16GB DDR5 RAM, 1TB SSD, RTX 4060 8GB, 144Hz FHD)",
        "brand": "Lenovo",
        "category_id": "laptops",
        "category_hint": "laptops",
        "description": "High performance gaming & programming laptop with 14th Gen Intel Core i7-14700HX, NVIDIA GeForce RTX 4060 8GB GDDR6, 16GB DDR5-5600 RAM, 1TB PCIe NVMe SSD.",
        "specs": {"cpu": "Intel Core i7-14700HX", "ram_gb": "16", "storage_gb": "1024", "display_in": "15.6", "gpu": "NVIDIA GeForce RTX 4060", "weight_kg": "2.38"},
        "rating": 4.5,
        "review_count": 870,
        "image_urls": ["https://images.unsplash.com/photo-1603302576837-37561b2e2302?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 94990.0, "currency": "INR", "original_price": 118990.0, "shipping": "Free Delivery", "warranty": "1 Year Onsite Warranty", "url": "https://www.amazon.in"},
            {"retailer": "Flipkart", "price": 93490.0, "currency": "INR", "original_price": 118990.0, "shipping": "Free Delivery", "warranty": "1 Year Onsite Warranty", "url": "https://www.flipkart.com"}
        ]
    },
    {
        "external_id": "demo-asus-zenbook-14-oled",
        "title": "ASUS Zenbook 14 OLED (Intel Core Ultra 7 155H, 16GB LPDDR5X RAM, 1TB SSD, Intel Arc Graphics, 1.2kg)",
        "brand": "ASUS",
        "category_id": "laptops",
        "category_hint": "laptops",
        "description": "Ultraportable premium laptop for software engineering and travel. 14.0-inch 3K 120Hz OLED display, Intel AI Boost NPU, 75Wh battery.",
        "specs": {"cpu": "Intel Core Ultra 7 155H", "ram_gb": "16", "storage_gb": "1024", "display_in": "14.0", "weight_kg": "1.20", "battery_hours": "15"},
        "rating": 4.6,
        "review_count": 612,
        "image_urls": ["https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 99990.0, "currency": "INR", "original_price": 119990.0, "shipping": "Free Prime", "warranty": "1 Year International Warranty", "url": "https://www.amazon.in"},
            {"retailer": "Croma", "price": 101990.0, "currency": "INR", "original_price": 119990.0, "shipping": "Free Delivery", "warranty": "1 Year International Warranty", "url": "https://www.croma.com"}
        ]
    },

    # ── Running Shoes ──
    {
        "external_id": "demo-nike-pegasus-41",
        "title": "Nike Air Zoom Pegasus 41 Road Running Shoes",
        "brand": "Nike",
        "category_id": "running-shoes",
        "category_hint": "running-shoes",
        "description": "Responsive road running shoes featuring dual Air Zoom units and all-new ReactX foam midsole for 13% more energy return. Engineered mesh upper for breathability.",
        "specs": {"cushioning": "Responsive", "weight_g": "297", "material": "Mesh", "gender": "Men", "water_resistant": "false"},
        "rating": 4.6,
        "review_count": 3120,
        "image_urls": ["https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Nike Store", "price": 8995.0, "currency": "INR", "original_price": 10995.0, "shipping": "Free for Members", "warranty": "6 Months Manufacturing Warranty", "url": "https://www.nike.com"},
            {"retailer": "Amazon", "price": 8490.0, "currency": "INR", "original_price": 10995.0, "shipping": "Free Delivery", "warranty": "6 Months Warranty", "url": "https://www.amazon.in"}
        ]
    },
    {
        "external_id": "demo-asics-gel-nimbus-26",
        "title": "ASICS Gel-Nimbus 26 Max Cushioning Running Shoes",
        "brand": "ASICS",
        "category_id": "running-shoes",
        "category_hint": "running-shoes",
        "description": "Premium max-cushion road running shoes with PureGEL technology and FF BLAST PLUS ECO cushioning for ultra-soft landings on long distance runs.",
        "specs": {"cushioning": "Max Cushioning", "weight_g": "304", "material": "Knit", "gender": "Unisex"},
        "rating": 4.8,
        "review_count": 1840,
        "image_urls": ["https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "ASICS Official", "price": 12999.0, "currency": "INR", "original_price": 14999.0, "shipping": "Free Delivery", "warranty": "3 Months Warranty", "url": "https://www.asics.com"},
            {"retailer": "Flipkart", "price": 11990.0, "currency": "INR", "original_price": 14999.0, "shipping": "Free Delivery", "warranty": "3 Months Warranty", "url": "https://www.flipkart.com"}
        ]
    },

    # ── Office Chairs ──
    {
        "external_id": "demo-sihoo-doro-c300",
        "title": "SIHOO Doro C300 Ergonomic Office Chair with Dynamic Lumbar Support & 3D Armrests",
        "brand": "SIHOO",
        "category_id": "office-chairs",
        "category_hint": "office-chairs",
        "description": "Ergonomic mesh high-back computer desk chair with dynamic self-adaptive lumbar tracking, 3D coordinated armrests, multi-angle recline lock, and breathable cloud mesh.",
        "specs": {"lumbar_support": "true", "armrest": "3D", "material": "Mesh", "max_load_kg": "136", "warranty_years": "3"},
        "rating": 4.5,
        "review_count": 920,
        "image_urls": ["https://images.unsplash.com/photo-1580481077195-c3a82da91883?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 22999.0, "currency": "INR", "original_price": 29999.0, "shipping": "Free Assembly Available", "warranty": "3 Years Manufacturer Warranty", "url": "https://www.amazon.in"},
            {"retailer": "Croma", "price": 23490.0, "currency": "INR", "original_price": 29999.0, "shipping": "Free Home Delivery", "warranty": "3 Years Manufacturer Warranty", "url": "https://www.croma.com"}
        ]
    },
    {
        "external_id": "demo-featherlite-helix-high-back",
        "title": "Featherlite Helix High Back Ergonomic Mesh Chair",
        "brand": "Featherlite",
        "category_id": "office-chairs",
        "category_hint": "office-chairs",
        "description": "Commercial grade ergonomic task chair tested to BIFMA standards with adjustable lumbar support, 2D armrests, and synchro-tilt mechanism.",
        "specs": {"lumbar_support": "true", "armrest": "2D", "material": "Mesh", "max_load_kg": "120", "warranty_years": "3"},
        "rating": 4.4,
        "review_count": 780,
        "image_urls": ["https://images.unsplash.com/photo-1505797149-43b0069ec26b?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Featherlite Direct", "price": 18500.0, "currency": "INR", "original_price": 21000.0, "shipping": "Free Delivery & Installation", "warranty": "3 Years Warranty", "url": "https://www.featherlitefurniture.com"},
            {"retailer": "Amazon", "price": 18200.0, "currency": "INR", "original_price": 21000.0, "shipping": "Free Delivery", "warranty": "3 Years Warranty", "url": "https://www.amazon.in"}
        ]
    },

    # ── Air Fryers ──
    {
        "external_id": "demo-philips-airfryer-xxl-hd9285",
        "title": "Philips Connected Airfryer XXL 7.2L (Connected with NutriU App, Rapid CombiAir Technology, 16-in-1)",
        "brand": "Philips",
        "category_id": "air-fryers",
        "category_hint": "air-fryers",
        "description": "7.2 Liter / 1.4kg capacity designed for families of 4 to 6 people. Rapid CombiAir technology automatically adjusts cook time and temperature. Wi-Fi connected with remote monitoring.",
        "specs": {"capacity_l": "7.2", "wattage_w": "2000", "presets": "16", "warranty_years": "2"},
        "rating": 4.7,
        "review_count": 4820,
        "image_urls": ["https://images.unsplash.com/photo-1556911220-e15b29be8c8f?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 14999.0, "currency": "INR", "original_price": 19995.0, "shipping": "Free Prime", "warranty": "2 Years Worldwide Guarantee", "url": "https://www.amazon.in"},
            {"retailer": "Croma", "price": 15490.0, "currency": "INR", "original_price": 19995.0, "shipping": "Free Delivery", "warranty": "2 Years Worldwide Guarantee", "url": "https://www.croma.com"},
            {"retailer": "Reliance Digital", "price": 15200.0, "currency": "INR", "original_price": 19995.0, "shipping": "Free Delivery", "warranty": "2 Years Worldwide Guarantee", "url": "https://www.reliancedigital.in"}
        ]
    },
    {
        "external_id": "demo-ninja-air-fryer-dualzone-af300",
        "title": "Ninja Foodi DualZone 7.6L 2-Basket Digital Air Fryer",
        "brand": "Ninja",
        "category_id": "air-fryers",
        "category_hint": "air-fryers",
        "description": "2 independent cooking baskets with DualZone technology: cook 2 foods in 2 ways and finish at the same time with the Smart Finish function. Perfect for busy family dinners.",
        "specs": {"capacity_l": "7.6", "wattage_w": "2400", "dual_basket": "true", "warranty_years": "1"},
        "rating": 4.8,
        "review_count": 6140,
        "image_urls": ["https://images.unsplash.com/photo-1588854337236-6889d631faa8?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 18999.0, "currency": "INR", "original_price": 24999.0, "shipping": "Free Delivery", "warranty": "1 Year Manufacturer Warranty", "url": "https://www.amazon.in"}
        ]
    },

    # ── Mobile Phones ──
    {
        "external_id": "demo-samsung-galaxy-s24-fe",
        "title": "Samsung Galaxy S24 FE 5G (8GB RAM, 256GB Storage, Exynos 2400e, Galaxy AI, Blue)",
        "brand": "Samsung",
        "category_id": "mobile-phones",
        "category_hint": "mobile-phones",
        "description": "6.7-inch Dynamic AMOLED 2X 120Hz display, 50MP triple pro-grade camera with 3x optical zoom, 4700mAh battery with 25W fast charging, 7 years of OS & security updates.",
        "specs": {"ram_gb": "8", "storage_gb": "256", "camera_mp": "50", "battery_mah": "4700", "network_5g": "true", "display_in": "6.7"},
        "rating": 4.5,
        "review_count": 1420,
        "image_urls": ["https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 54999.0, "currency": "INR", "original_price": 65999.0, "shipping": "Free Next-Day", "warranty": "1 Year Comprehensive Warranty", "url": "https://www.amazon.in"},
            {"retailer": "Samsung Direct", "price": 55999.0, "currency": "INR", "original_price": 65999.0, "shipping": "Free Delivery", "warranty": "1 Year Comprehensive Warranty", "url": "https://www.samsung.com"},
            {"retailer": "Flipkart", "price": 54499.0, "currency": "INR", "original_price": 65999.0, "shipping": "Free Delivery", "warranty": "1 Year Comprehensive Warranty", "url": "https://www.flipkart.com"}
        ]
    },
    {
        "external_id": "demo-oneplus-12r",
        "title": "OnePlus 12R 5G (16GB RAM, 256GB Storage, Snapdragon 8 Gen 2, 5500mAh, 100W SUPERVOOC, Iron Gray)",
        "brand": "OnePlus",
        "category_id": "mobile-phones",
        "category_hint": "mobile-phones",
        "description": "Flagship-tier performance with Snapdragon 8 Gen 2, 4th Gen 120Hz ProXDR display, 5500mAh highest battery capacity on a OnePlus phone, and Sony IMX890 50MP OIS camera.",
        "specs": {"ram_gb": "16", "storage_gb": "256", "camera_mp": "50", "battery_mah": "5500", "network_5g": "true", "display_in": "6.78"},
        "rating": 4.6,
        "review_count": 5210,
        "image_urls": ["https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 42999.0, "currency": "INR", "original_price": 45999.0, "shipping": "Free Prime", "warranty": "1 Year Warranty", "url": "https://www.amazon.in"},
            {"retailer": "Croma", "price": 42999.0, "currency": "INR", "original_price": 45999.0, "shipping": "Free Express", "warranty": "1 Year Warranty", "url": "https://www.croma.com"}
        ]
    },

    # ── Skincare ──
    {
        "external_id": "demo-minimalist-salicylic-acid-2",
        "title": "Minimalist 2% Salicylic Acid Face Serum for Oily Skin, Blackheads & Acne Control (30ml)",
        "brand": "Minimalist",
        "category_id": "skincare",
        "category_hint": "skincare",
        "description": "Daily gentle exfoliating serum with 2% Salicylic Acid (BHA), formulated in soothing Aloe Vera base. Penetrates pore linings to reduce excess sebum, oiliness, and acne breakouts.",
        "specs": {"skin_type": "Oily", "key_ingredient": "Salicylic Acid", "volume_ml": "30", "fragrance_free": "true"},
        "rating": 4.4,
        "review_count": 8940,
        "image_urls": ["https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Minimalist Store", "price": 549.0, "currency": "INR", "original_price": 599.0, "shipping": "Free over ₹499", "url": "https://beminimalist.co"},
            {"retailer": "Amazon", "price": 520.0, "currency": "INR", "original_price": 599.0, "shipping": "Free Prime", "url": "https://www.amazon.in"},
            {"retailer": "Nykaa", "price": 539.0, "currency": "INR", "original_price": 599.0, "shipping": "Free Delivery", "url": "https://www.nykaa.com"}
        ]
    },
    {
        "external_id": "demo-cerave-foaming-cleanser",
        "title": "CeraVe Foaming Facial Cleanser for Normal to Oily Skin with Hyaluronic Acid & Niacinamide (236ml)",
        "brand": "CeraVe",
        "category_id": "skincare",
        "category_hint": "skincare",
        "description": "Dermatologist-developed foaming gel cleanser cleanses and removes excess oil without disrupting the protective skin barrier. Non-comedogenic and fragrance-free.",
        "specs": {"skin_type": "Oily", "key_ingredient": "Niacinamide", "volume_ml": "236", "fragrance_free": "true"},
        "rating": 4.7,
        "review_count": 12850,
        "image_urls": ["https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 1050.0, "currency": "INR", "original_price": 1250.0, "shipping": "Free Delivery", "url": "https://www.amazon.in"},
            {"retailer": "Nykaa", "price": 1125.0, "currency": "INR", "original_price": 1250.0, "shipping": "Free Delivery", "url": "https://www.nykaa.com"}
        ]
    },

    # ── Power Tools ──
    {
        "external_id": "demo-bosch-gsb-500w-kit",
        "title": "Bosch GSB 500W 10 RE Professional Impact Drill Machine Kit with 100 Accessories for Home DIY",
        "brand": "Bosch",
        "category_id": "power-tools",
        "category_hint": "power-tools",
        "description": "500-Watt reversible impact hammer drill with 10mm key chuck and complete 100-piece accessory kit (drill bits, screws, plugs, hammer, pliers) in sturdy carrying case for home DIY projects.",
        "specs": {"tool_type": "Hammer Drill", "wattage_w": "500", "chuck_mm": "10", "kit_pieces": "100", "warranty_years": "1"},
        "rating": 4.5,
        "review_count": 7820,
        "image_urls": ["https://images.unsplash.com/photo-1504148455328-c376907d081c?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 3899.0, "currency": "INR", "original_price": 5450.0, "shipping": "Free Delivery", "warranty": "1 Year Bosch India Warranty", "url": "https://www.amazon.in"},
            {"retailer": "Flipkart", "price": 3799.0, "currency": "INR", "original_price": 5450.0, "shipping": "Free Delivery", "warranty": "1 Year Bosch India Warranty", "url": "https://www.flipkart.com"}
        ]
    },

    # ── Luggage & Suitcases ──
    {
        "external_id": "demo-samsonite-evoa-spinner-75",
        "title": "Samsonite EVOA Polycarbonate 75cm Large Check-in Spinner Suitcase with TSA Lock",
        "brand": "Samsonite",
        "category_id": "luggage",
        "category_hint": "luggage",
        "description": "Minimalist high-tech check-in luggage constructed from premium 100% Makrolon polycarbonate. Features Aero-Trac suspension wheel system, anti-theft zipper, and integrated TSA magnetic lock.",
        "specs": {"capacity_l": "108", "shell": "Polycarbonate", "luggage_size": "Large", "tsa_lock": "true", "weight_kg": "5.3", "warranty_years": "10"},
        "rating": 4.8,
        "review_count": 1420,
        "image_urls": ["https://images.unsplash.com/photo-1565026057447-bc90a3dceb87?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Samsonite Official", "price": 28500.0, "currency": "INR", "original_price": 32000.0, "shipping": "Free Insured Shipping", "warranty": "10 Years Global Warranty", "url": "https://www.samsonite.com"},
            {"retailer": "Amazon", "price": 27490.0, "currency": "INR", "original_price": 32000.0, "shipping": "Free Delivery", "warranty": "10 Years Global Warranty", "url": "https://www.amazon.in"}
        ]
    },

    # ── Washing Machines ──
    {
        "external_id": "demo-lg-8kg-front-load-inverter",
        "title": "LG 8 Kg 5 Star Inverter Direct Drive Fully-Automatic Front Load Washing Machine with Steam & Wi-Fi",
        "brand": "LG",
        "category_id": "washing-machines",
        "category_hint": "washing-machines",
        "description": "8kg front-load washer suitable for families of 4 to 5 members. AI DD (Artificial Intelligence Direct Drive) detects fabric weight and softness. 1400 RPM spin speed with 5-star energy rating.",
        "specs": {"capacity_kg": "8", "energy_rating": "5", "rpm": "1400", "load_type": "Front Load", "inverter": "true", "warranty_years": "2"},
        "rating": 4.6,
        "review_count": 3840,
        "image_urls": ["https://images.unsplash.com/photo-1626806787461-102c1bfaaea1?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 37990.0, "currency": "INR", "original_price": 47990.0, "shipping": "Free Delivery & Installation", "warranty": "2 Years on Product, 10 Years on Motor", "url": "https://www.amazon.in"},
            {"retailer": "Croma", "price": 38490.0, "currency": "INR", "original_price": 47990.0, "shipping": "Free Delivery & Installation", "warranty": "2 Years on Product, 10 Years on Motor", "url": "https://www.croma.com"},
            {"retailer": "Reliance Digital", "price": 37990.0, "currency": "INR", "original_price": 47990.0, "shipping": "Free Delivery & Installation", "warranty": "2 Years on Product, 10 Years on Motor", "url": "https://www.reliancedigital.in"}
        ]
    },

    # ── Gaming Monitors ──
    {
        "external_id": "demo-lg-ultragear-27gr83q",
        "title": "LG UltraGear 27\" QHD (2560x1440) IPS Gaming Monitor (240Hz, 1ms GtG, DisplayHDR 400, G-Sync Compatible)",
        "brand": "LG",
        "category_id": "monitors",
        "category_hint": "monitors",
        "description": "High-speed 240Hz esports gaming monitor with 27-inch Quad HD IPS panel, 1ms response time, AMD FreeSync Premium, and ergonomic height/pivot/tilt stand.",
        "specs": {"display_in": "27", "refresh_hz": "240", "resolution": "QHD", "panel": "IPS", "response_ms": "1"},
        "rating": 4.7,
        "review_count": 1950,
        "image_urls": ["https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?auto=format&fit=crop&w=800&q=80"],
        "offers": [
            {"retailer": "Amazon", "price": 34999.0, "currency": "INR", "original_price": 45000.0, "shipping": "Free Prime", "warranty": "3 Years Onsite Warranty", "url": "https://www.amazon.in"},
            {"retailer": "Croma", "price": 35490.0, "currency": "INR", "original_price": 45000.0, "shipping": "Free Delivery", "warranty": "3 Years Onsite Warranty", "url": "https://www.croma.com"}
        ]
    }
]


class DemoProvider(ProductProvider):
    name: ClassVar[str] = "demo_provider"
    label: ClassVar[str] = "Demo Catalog (Disabled)"
    is_demo: ClassVar[bool] = True

    def is_configured(self) -> bool:
        # Completely disabled in runtime. Live scrapers are the sole product source.
        return False

    async def search_products(self, params: Any) -> List[RawProduct]:
        return []

