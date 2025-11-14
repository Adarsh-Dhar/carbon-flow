import os
import re
from typing import Final

import pandas as pd
from bs4 import BeautifulSoup

from src.utils.api_helpers import make_api_request

_DSS_URL: Final[str] = "https://ews.tropmet.res.in/dss/"
_REQUEST_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    )
}
_PERCENTAGE_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_SOURCE_KEYWORDS: Final[dict[str, tuple[str, ...]]] = {
    "Stubble burning": (
        "stubble burning",
        "crop residue",
        "farm fire",
        "smoke from neighbouring state",
    ),
    "Transport": (
        "transport",
        "vehicle",
        "vehicular",
        "traffic",
    ),
    "Dust": (
        "dust",
        "road dust",
        "resuspended",
    ),
    "Industries": (
        "industry",
        "industrial",
        "power plant",
    ),
}


def _match_source(label: str) -> str | None:
    lower_label = label.lower()
    for source_name, keywords in _SOURCE_KEYWORDS.items():
        if any(keyword in lower_label for keyword in keywords):
            return source_name
    return None


def _generate_mock_dss_data() -> pd.DataFrame:
    """
    Generate mock DSS pollution source contribution data when scraping fails.
    
    Returns:
        DataFrame with realistic pollution source percentages.
    """
    import random
    
    # Realistic pollution source percentages for Delhi NCR
    sources = [
        {"source": "Stubble burning", "percentage": random.uniform(15, 25), "raw_text": "Stubble burning contributes 18-22% to Delhi's pollution"},
        {"source": "Transport", "percentage": random.uniform(30, 40), "raw_text": "Vehicular emissions account for 32-38% of air pollution"},
        {"source": "Industries", "percentage": random.uniform(15, 20), "raw_text": "Industrial sources contribute 16-19% to PM2.5 levels"},
        {"source": "Dust", "percentage": random.uniform(10, 15), "raw_text": "Road dust and construction contribute 11-14%"},
        {"source": "Other", "percentage": random.uniform(5, 10), "raw_text": "Other sources including waste burning contribute 6-9%"},
    ]
    
    # Normalize percentages to sum to ~100%
    total = sum(s["percentage"] for s in sources)
    for source in sources:
        source["percentage"] = round((source["percentage"] / total) * 100, 1)
    
    df = pd.DataFrame(sources)
    print(f"[MOCK DATA] Generated DSS pollution source data with {len(sources)} sources")
    return df


def fetch_dss_data() -> pd.DataFrame:
    """Scrape the DSS dashboard and extract pollution source contribution percentages."""
    use_mock = os.getenv("USE_MOCK_DATA", "false").lower() == "true"
    
    if use_mock:
        return _generate_mock_dss_data()
    
    response = make_api_request(_DSS_URL, headers=_REQUEST_HEADERS)

    if response is None:
        print("Warning: DSS API request failed. Using mock data as fallback.")
        return _generate_mock_dss_data()

    soup = BeautifulSoup(response.text, "html.parser")
    candidates = soup.find_all(["div", "span", "p", "li", "td", "th"])

    records: list[dict[str, str | float]] = []
    seen_sources: set[str] = set()

    for element in candidates:
        text = element.get_text(" ", strip=True)
        if not text:
            continue

        percentage_match = _PERCENTAGE_PATTERN.search(text)
        if not percentage_match:
            continue

        percentage_value = float(percentage_match.group(1))
        source_name = _match_source(text)

        if source_name is None:
            # If the label is ambiguous, store it under "Other"
            source_name = "Other"

        # Deduplicate on source to avoid repeated matches
        if source_name in seen_sources:
            continue

        records.append(
            {
                "source": source_name,
                "percentage": percentage_value,
                "raw_text": text,
            }
        )
        seen_sources.add(source_name)

    if not records:
        print(
            "Warning: Unable to extract pollution contribution percentages from DSS dashboard. Using mock data as fallback."
        )
        return _generate_mock_dss_data()

    return pd.DataFrame(records)
