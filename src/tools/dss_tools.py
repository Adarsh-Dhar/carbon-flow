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


def fetch_dss_data() -> pd.DataFrame:
    """Scrape the DSS dashboard and extract pollution source contribution percentages."""
    response = make_api_request(_DSS_URL, headers=_REQUEST_HEADERS)

    if response is None:
        return pd.DataFrame(columns=["source", "percentage", "raw_text"])

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
            "Warning: Unable to extract pollution contribution percentages from DSS dashboard."
        )
        return pd.DataFrame(columns=["source", "percentage", "raw_text"])

    return pd.DataFrame(records)
