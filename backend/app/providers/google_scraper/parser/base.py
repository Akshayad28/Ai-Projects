"""Base class for Google Layout Parsers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Tuple
from bs4 import BeautifulSoup

from app.providers.google_scraper.models import ExtractionHealth, GoogleLayout, GoogleScrapedItem


class GoogleLayoutParser(ABC):
    """Abstract Base Class for layout-specific Google Shopping parsers."""

    layout_type: GoogleLayout = GoogleLayout.UNKNOWN

    @abstractmethod
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Determines if this parser can process the provided parsed DOM."""
        raise NotImplementedError

    @abstractmethod
    def parse(
        self,
        soup: BeautifulSoup,
        country: str = "IN",
        currency: str = "INR",
        max_results: int = 20,
    ) -> Tuple[List[GoogleScrapedItem], ExtractionHealth]:
        """Parses product items from the DOM and records extraction health."""
        raise NotImplementedError
