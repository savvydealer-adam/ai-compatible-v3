"""Test fixtures with mock HTML and robots.txt samples."""

import httpx
import pytest


@pytest.fixture
def page_cache():
    return {}


@pytest.fixture
def client():
    """Create a real httpx client for integration tests."""
    return httpx.AsyncClient(timeout=10.0, follow_redirects=True)


@pytest.fixture
def mock_html_dealer():
    """Sample dealer homepage with JSON-LD."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Dealer - New and Used Cars</title>
        <meta name="description" content="Test Dealer offers new and used cars in Springfield">
        <link rel="canonical" href="https://www.testdealer.com">
        <meta property="og:title" content="Test Dealer">
        <meta property="og:description" content="New and Used Cars">
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "AutoDealer",
            "name": "Test Dealer",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "123 Main St",
                "addressLocality": "Springfield",
                "addressRegion": "IL",
                "postalCode": "62701"
            },
            "telephone": "(555) 123-4567",
            "url": "https://www.testdealer.com"
        }
        </script>
    </head>
    <body>
        <header><nav><a href="/new-inventory/">New Vehicles</a></nav></header>
        <footer>Powered by <a href="https://savvydealer.com">Savvy Dealer</a></footer>
    </body>
    </html>
    """


@pytest.fixture
def mock_html_inventory():
    """Sample inventory page with ItemList schema."""
    return """
    <html>
    <head><title>New Inventory - Test Dealer</title></head>
    <body>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "itemListElement": [
                {"@type": "Car", "name": "2024 Toyota Camry"},
                {"@type": "Car", "name": "2024 Honda Civic"},
                {"@type": "Car", "name": "2024 Ford F-150"}
            ]
        }
        </script>
        <div class="inventory-list">
            <a href="/vehicle-info/2024-Toyota-Camry-1HGBH41JXMN109186/">2024 Toyota Camry</a>
            <a href="/vehicle-info/2024-Honda-Civic-2HGFC2F50NH123456/">2024 Honda Civic</a>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def mock_html_vdp():
    """Sample vehicle detail page with Car schema."""
    return """
    <html>
    <head><title>2024 Toyota Camry - Test Dealer</title></head>
    <body>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Car",
            "name": "2024 Toyota Camry LE",
            "brand": {"@type": "Brand", "name": "Toyota"},
            "model": "Camry",
            "vehicleIdentificationNumber": "1HGBH41JXMN109186",
            "vehicleModelDate": "2024",
            "mileageFromOdometer": {"@type": "QuantitativeValue", "value": "15", "unitCode": "SMI"},
            "offers": {
                "@type": "Offer",
                "price": "28995",
                "priceCurrency": "USD"
            },
            "image": "https://example.com/car.jpg"
        }
        </script>
        <h1>2024 Toyota Camry LE</h1>
        <p>Price: $28,995</p>
        <p>VIN: 1HGBH41JXMN109186</p>
        <p>Mileage: 15 miles</p>
    </body>
    </html>
    """


@pytest.fixture
def mock_robots_allow_all():
    return """User-agent: *
Allow: /

Sitemap: https://www.testdealer.com/sitemap.xml
"""


@pytest.fixture
def mock_robots_block_ai():
    return """User-agent: *
Allow: /

User-agent: GPTBot
Disallow: /

User-agent: Claude-Web
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Google-Extended
Disallow: /

Sitemap: https://www.testdealer.com/sitemap.xml
"""


@pytest.fixture
def mock_robots_block_all():
    return """User-agent: *
Disallow: /
"""


@pytest.fixture
def mock_sitemap_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://www.testdealer.com/</loc>
        <lastmod>2024-01-15</lastmod>
    </url>
    <url>
        <loc>https://www.testdealer.com/new-inventory/</loc>
        <lastmod>2024-01-15</lastmod>
    </url>
    <url>
        <loc>https://www.testdealer.com/vehicle-info/2024-Toyota-Camry-1HGBH41JXMN109186/</loc>
        <lastmod>2024-01-14</lastmod>
    </url>
</urlset>
"""
