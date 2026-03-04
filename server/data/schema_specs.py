"""JSON-LD schema property specifications per type."""

# Required and optional properties for each schema type
SCHEMA_REQUIRED_PROPERTIES: dict[str, dict[str, list[str]]] = {
    # Dealer types
    "LocalBusiness": {
        "required": ["name", "address"],
        "optional": [
            "telephone",
            "url",
            "openingHours",
            "geo",
            "image",
            "description",
            "priceRange",
            "review",
            "aggregateRating",
        ],
    },
    "AutoDealer": {
        "required": ["name", "address"],
        "optional": [
            "telephone",
            "url",
            "openingHours",
            "geo",
            "image",
            "description",
            "priceRange",
            "review",
            "aggregateRating",
        ],
    },
    "Organization": {
        "required": ["name"],
        "optional": [
            "url",
            "logo",
            "description",
            "address",
            "telephone",
            "sameAs",
            "contactPoint",
        ],
    },
    "AutomotiveBusiness": {
        "required": ["name", "address"],
        "optional": [
            "telephone",
            "url",
            "openingHours",
            "geo",
            "image",
            "description",
        ],
    },
    "Store": {
        "required": ["name", "address"],
        "optional": [
            "telephone",
            "url",
            "openingHours",
            "geo",
            "image",
            "description",
        ],
    },
    # Vehicle types
    "Vehicle": {
        "required": ["name"],
        "optional": [
            "description",
            "image",
            "offers",
            "brand",
            "model",
            "vehicleIdentificationNumber",
            "mileageFromOdometer",
            "color",
            "vehicleEngine",
            "fuelType",
            "vehicleModelDate",
            "bodyType",
            "vehicleTransmission",
            "driveWheelConfiguration",
            "numberOfDoors",
            "vehicleInteriorColor",
            "vehicleSeatingCapacity",
            "numberOfPreviousOwners",
        ],
    },
    "Car": {
        "required": ["name"],
        "optional": [
            "description",
            "image",
            "offers",
            "brand",
            "model",
            "vehicleIdentificationNumber",
            "mileageFromOdometer",
            "color",
            "vehicleEngine",
            "fuelType",
            "vehicleModelDate",
            "bodyType",
            "vehicleTransmission",
            "driveWheelConfiguration",
            "numberOfDoors",
            "vehicleInteriorColor",
            "vehicleSeatingCapacity",
            "numberOfPreviousOwners",
        ],
    },
    "Motorcycle": {
        "required": ["name"],
        "optional": [
            "description",
            "image",
            "offers",
            "brand",
            "model",
            "vehicleIdentificationNumber",
            "mileageFromOdometer",
            "color",
            "vehicleEngine",
            "fuelType",
            "vehicleModelDate",
        ],
    },
    "BusOrCoach": {
        "required": ["name"],
        "optional": [
            "description",
            "image",
            "offers",
            "brand",
            "model",
            "vehicleIdentificationNumber",
            "mileageFromOdometer",
        ],
    },
    "MotorizedBicycle": {
        "required": ["name"],
        "optional": [
            "description",
            "image",
            "offers",
            "brand",
            "model",
            "vehicleIdentificationNumber",
        ],
    },
    # Product types
    "Product": {
        "required": ["name"],
        "optional": [
            "description",
            "image",
            "offers",
            "brand",
            "model",
            "sku",
            "gtin",
            "color",
        ],
    },
    "IndividualProduct": {
        "required": ["name"],
        "optional": [
            "description",
            "image",
            "offers",
            "brand",
            "model",
            "sku",
        ],
    },
    # Inventory types
    "ItemList": {
        "required": ["itemListElement"],
        "optional": ["name", "numberOfItems", "itemListOrder"],
    },
    "OfferCatalog": {
        "required": ["itemListElement"],
        "optional": ["name", "numberOfItems"],
    },
    # Offer types
    "Offer": {
        "required": ["price"],
        "optional": [
            "priceCurrency",
            "availability",
            "url",
            "priceValidUntil",
            "itemCondition",
        ],
    },
    "AggregateOffer": {
        "required": ["lowPrice"],
        "optional": [
            "highPrice",
            "priceCurrency",
            "offerCount",
        ],
    },
    # Web types
    "WebSite": {
        "required": ["name"],
        "optional": ["url", "potentialAction", "description"],
    },
    "WebPage": {
        "required": ["name"],
        "optional": ["url", "description", "breadcrumb"],
    },
    "BreadcrumbList": {
        "required": ["itemListElement"],
        "optional": [],
    },
    # FAQ type (new in v3)
    "FAQPage": {
        "required": ["mainEntity"],
        "optional": ["name", "description"],
    },
}

# Schema type categorization
DEALER_SCHEMA_TYPES = [
    "LocalBusiness",
    "AutoDealer",
    "Organization",
    "AutomotiveBusiness",
    "Store",
]

VEHICLE_SCHEMA_TYPES = [
    "Vehicle",
    "Car",
    "Motorcycle",
    "BusOrCoach",
    "MotorizedBicycle",
    "Product",
    "IndividualProduct",
]

INVENTORY_SCHEMA_TYPES = ["ItemList", "OfferCatalog"]

# Type aliases for normalization (case-insensitive)
SCHEMA_TYPE_ALIASES: dict[str, str] = {
    "car": "Car",
    "vehicle": "Vehicle",
    "motorcycle": "Motorcycle",
    "busorcoach": "BusOrCoach",
    "motorizedbicycle": "MotorizedBicycle",
    "product": "Product",
    "localbusiness": "LocalBusiness",
    "autodealer": "AutoDealer",
    "organization": "Organization",
    "itemlist": "ItemList",
    "offercatalog": "OfferCatalog",
    "offer": "Offer",
    "aggregateoffer": "AggregateOffer",
    "website": "WebSite",
    "webpage": "WebPage",
    "breadcrumblist": "BreadcrumbList",
    "automotivebusiness": "AutomotiveBusiness",
    "store": "Store",
    "automobile": "Car",
    "suv": "Car",
    "van": "Vehicle",
    "minivan": "Vehicle",
    "truck": "Vehicle",
    "automobileproduct": "Car",
    "individualproduct": "IndividualProduct",
    "faqpage": "FAQPage",
    "vehiclelisting": "VehicleListing",
}
