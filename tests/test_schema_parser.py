"""Tests for JSON-LD schema parser."""

from server.detectors.schema_parser import SchemaParser


class TestSchemaParser:
    def setup_method(self):
        self.parser = SchemaParser.__new__(SchemaParser)
        self.parser.page_cache = {}

    def test_extract_json_ld_blocks(self, mock_html_dealer):
        blocks = self.parser._extract_json_ld_blocks(mock_html_dealer)
        assert len(blocks) == 1
        assert "AutoDealer" in blocks[0]

    def test_parse_dealer_schema(self, mock_html_dealer):
        result = self.parser.parse_content(mock_html_dealer)
        assert result["json_ld_found"] is True
        assert result["has_dealer_schema"] is True
        assert "AutoDealer" in result["schemas_detected"]

    def test_parse_inventory_schema(self, mock_html_inventory):
        result = self.parser.parse_content(mock_html_inventory)
        assert result["json_ld_found"] is True
        assert result["has_inventory_schema"] is True
        assert "ItemList" in result["schemas_detected"]

    def test_parse_vehicle_schema(self, mock_html_vdp):
        result = self.parser.parse_content(mock_html_vdp)
        assert result["json_ld_found"] is True
        assert result["has_vehicle_schema"] is True
        assert "Car" in result["schemas_detected"]

    def test_schema_completeness(self, mock_html_vdp):
        result = self.parser.parse_content(mock_html_vdp)
        details = result["schema_details"]
        car_detail = next(d for d in details if d["type"] == "Car")
        assert car_detail["completeness_score"] > 50
        assert "name" in car_detail["properties_found"]
        assert "vehicleIdentificationNumber" in car_detail["properties_found"]

    def test_invalid_json_ld(self):
        html = '<script type="application/ld+json">{invalid json}</script>'
        result = self.parser.parse_content(html)
        assert result["json_ld_found"] is False
        assert len(result["validation_errors"]) > 0

    def test_no_json_ld(self):
        html = "<html><body>No schema here</body></html>"
        result = self.parser.parse_content(html)
        assert result["json_ld_found"] is False

    def test_graph_container(self):
        html = """
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "WebSite", "name": "Test"},
                {"@type": "AutoDealer", "name": "Test Dealer",
                    "address": {"streetAddress": "123 Main"}}
            ]
        }
        </script>
        """
        result = self.parser.parse_content(html)
        assert result["json_ld_found"] is True
        assert result["has_dealer_schema"] is True
        assert len(result["schemas_detected"]) == 2

    def test_normalize_schema_type(self):
        assert self.parser._normalize_schema_type("car") == "Car"
        assert self.parser._normalize_schema_type("automobile") == "Car"
        assert self.parser._normalize_schema_type("LocalBusiness") == "LocalBusiness"
        assert self.parser._normalize_schema_type("suv") == "Car"
        assert self.parser._normalize_schema_type("truck") == "Vehicle"
