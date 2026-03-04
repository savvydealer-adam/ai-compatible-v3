"""JSON-LD extraction and validation."""

import json
import logging
import re

from server.data.schema_specs import (
    DEALER_SCHEMA_TYPES,
    INVENTORY_SCHEMA_TYPES,
    SCHEMA_REQUIRED_PROPERTIES,
    SCHEMA_TYPE_ALIASES,
    VEHICLE_SCHEMA_TYPES,
)
from server.detectors.base import BaseDetector

logger = logging.getLogger(__name__)


class SchemaParser(BaseDetector):
    """Extract and validate JSON-LD structured data."""

    async def check(self, url_or_domain: str) -> dict:
        """Analyze JSON-LD schemas on a page."""
        result = {
            "json_ld_found": False,
            "json_ld_count": 0,
            "schemas_detected": [],
            "schema_details": [],
            "validation_errors": [],
            "has_dealer_schema": False,
            "has_vehicle_schema": False,
            "has_inventory_schema": False,
        }

        if "://" not in url_or_domain:
            url_or_domain = self.make_url(url_or_domain)

        content = await self.fetch_page(url_or_domain)
        if not content:
            return result

        return self.parse_content(content, result)

    def parse_content(self, html: str, result: dict | None = None) -> dict:
        """Parse JSON-LD from HTML content."""
        if result is None:
            result = {
                "json_ld_found": False,
                "json_ld_count": 0,
                "schemas_detected": [],
                "schema_details": [],
                "validation_errors": [],
                "has_dealer_schema": False,
                "has_vehicle_schema": False,
                "has_inventory_schema": False,
            }

        blocks = self._extract_json_ld_blocks(html)
        if not blocks:
            return result

        schemas: list[dict] = []
        for block_text in blocks:
            parsed = self._parse_json_ld_block(block_text, result["validation_errors"])
            schemas.extend(parsed)

        if schemas:
            result["json_ld_found"] = True
        result["json_ld_count"] = len(schemas)

        for schema in schemas:
            schema_type = self._get_schema_type(schema)
            if not schema_type:
                continue

            result["schemas_detected"].append(schema_type)
            detail = self._validate_schema(schema, schema_type)
            result["schema_details"].append(detail)

            if schema_type in DEALER_SCHEMA_TYPES:
                result["has_dealer_schema"] = True
            if schema_type in VEHICLE_SCHEMA_TYPES:
                result["has_vehicle_schema"] = True
            if schema_type in INVENTORY_SCHEMA_TYPES:
                result["has_inventory_schema"] = True

        return result

    def _extract_json_ld_blocks(self, html: str) -> list[str]:
        """Find all <script type="application/ld+json"> blocks."""
        soup = self.parse_html(html)
        scripts = soup.find_all("script", {"type": "application/ld+json"})
        return [s.string for s in scripts if s.string and s.string.strip()]

    def _parse_json_ld_block(self, text: str, errors: list) -> list[dict]:
        """Parse a single JSON-LD block into schema dicts."""
        schemas = []
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON-LD: {e}")
            return schemas

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    schemas.append(item)
        elif isinstance(data, dict):
            # Handle @graph container
            if "@graph" in data:
                graph = data["@graph"]
                if isinstance(graph, list):
                    schemas.extend(item for item in graph if isinstance(item, dict))
            else:
                schemas.append(data)

        return schemas

    def _get_schema_type(self, schema: dict) -> str | None:
        """Extract and normalize schema @type."""
        raw_type = schema.get("@type")
        if not raw_type:
            return None

        if isinstance(raw_type, list):
            for t in raw_type:
                normalized = self._normalize_schema_type(t, schema)
                if normalized:
                    return normalized
            return self._normalize_schema_type(str(raw_type[0]), schema) if raw_type else None

        return self._normalize_schema_type(str(raw_type), schema)

    def _normalize_schema_type(self, schema_type: str, schema: dict | None = None) -> str:
        """Normalize schema type with alias lookup."""
        # Strip schema.org prefix
        clean = re.sub(r"^https?://schema\.org/", "", schema_type).strip()
        lower = clean.lower()

        # Direct alias lookup
        if lower in SCHEMA_TYPE_ALIASES:
            return SCHEMA_TYPE_ALIASES[lower]

        # Check if it's in our known types (case-insensitive)
        if clean in SCHEMA_REQUIRED_PROPERTIES:
            return clean

        # Detect vehicle-like schemas by properties
        if schema and lower in ("other", "thing", "item"):
            vehicle_props = [
                "vehicleIdentificationNumber",
                "vehicleEngine",
                "fuelType",
                "vehicleModelDate",
                "mileageFromOdometer",
            ]
            if any(prop in schema for prop in vehicle_props):
                return "Vehicle"

        return clean

    def _validate_schema(self, schema: dict, schema_type: str) -> dict:
        """Validate schema completeness against specs."""
        spec = SCHEMA_REQUIRED_PROPERTIES.get(schema_type)
        if not spec:
            return {
                "type": schema_type,
                "properties_found": list(schema.keys()),
                "properties_missing": [],
                "completeness_score": 50.0,
                "raw_data": schema,
            }

        required = spec.get("required", [])
        optional = spec.get("optional", [])
        all_props = required + optional

        found = [p for p in all_props if self._has_property(schema, p)]
        missing = [p for p in required if p not in found]

        # Score: 60% weight required, 40% optional
        req_count = len(required)
        opt_count = len(optional)
        req_found = len([p for p in required if p in found])
        opt_found = len([p for p in optional if p in found])

        if req_count + opt_count == 0:
            score = 100.0
        else:
            req_pct = (req_found / req_count * 60) if req_count else 60
            opt_pct = (opt_found / opt_count * 40) if opt_count else 0
            score = req_pct + opt_pct

        return {
            "type": schema_type,
            "properties_found": found,
            "properties_missing": missing,
            "completeness_score": round(score, 1),
            "raw_data": schema,
        }

    @staticmethod
    def _has_property(schema: dict, prop: str) -> bool:
        """Check if property exists and has a non-empty value."""
        val = schema.get(prop)
        if val is None:
            return False
        if isinstance(val, str) and not val.strip():
            return False
        return not (isinstance(val, (list, dict)) and len(val) == 0)
