"""CSS selectors and extraction config per website provider for VDP/SRP data."""

from dataclasses import dataclass, field


@dataclass
class ProviderSelectors:
    """CSS selectors for extracting vehicle data from a provider's pages."""

    price: list[str] = field(default_factory=list)
    vin: list[str] = field(default_factory=list)
    vehicle_card: list[str] = field(default_factory=list)
    vehicle_title: list[str] = field(default_factory=list)


PROVIDER_SELECTORS: dict[str, ProviderSelectors] = {
    "DealerON": ProviderSelectors(
        price=[
            ".final-price .value",
            ".price-value",
            ".internetPrice .value",
            "[data-price]",
        ],
        vin=[".vin-value", ".vdp-vin", "[data-vin]"],
        vehicle_card=[".vehicle-card", ".srp-vehicle", ".inventory-listing"],
        vehicle_title=[".vehicle-title", "h1.vehicle-name"],
    ),
    "Dealer.com": ProviderSelectors(
        price=[
            ".price-value",
            ".finalPrice",
            ".internetPrice",
            ".pricing .value",
        ],
        vin=[".vin .value", ".vdpVin"],
        vehicle_card=[".vehicle-card", ".hproduct"],
        vehicle_title=[".vehicle-title h1", "h1.listing-title"],
    ),
    "DealerInspire": ProviderSelectors(
        price=[
            ".price",
            ".vehicle-price",
            ".di-price",
            ".final-price",
        ],
        vin=[".vin", ".vehicle-vin"],
        vehicle_card=[".vehicle-card", ".srp-listing"],
        vehicle_title=[".vehicle-name", "h1"],
    ),
    "DealerFire": ProviderSelectors(
        price=[".price", ".vehicle-price", ".df-price"],
        vin=[".vin", ".df-vin"],
        vehicle_card=[".vehicle-item", ".listing-item"],
        vehicle_title=[".vehicle-title", "h1"],
    ),
    "Savvy Dealer": ProviderSelectors(
        price=[
            ".vehicle-price",
            ".price-display",
            "[data-vehicle-price]",
        ],
        vin=[".vehicle-vin", "[data-vin]"],
        vehicle_card=[".vehicle-card", ".inventory-item"],
        vehicle_title=[".vehicle-title", "h1"],
    ),
}

# Fallback for unknown providers — uses no CSS selectors, relies on regex extraction
GENERIC_SELECTORS = ProviderSelectors(
    price=[".price", "[class*='price']", "[data-price]"],
    vin=[".vin", "[class*='vin']", "[data-vin]"],
    vehicle_card=["[class*='vehicle']", "[class*='listing']", "[class*='inventory']"],
    vehicle_title=["h1", ".vehicle-title", "[class*='title']"],
)


def get_selectors(provider_name: str | None) -> ProviderSelectors:
    """Get CSS selectors for a provider, with generic fallback."""
    if provider_name and provider_name in PROVIDER_SELECTORS:
        return PROVIDER_SELECTORS[provider_name]
    return GENERIC_SELECTORS
