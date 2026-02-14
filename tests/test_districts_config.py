"""Tests for the districts configuration file."""

import json
from pathlib import Path

import pytest

CONFIG_FILE = Path("config/districts.json")


@pytest.fixture
def districts():
    """Load districts config."""
    with open(CONFIG_FILE) as f:
        return json.load(f)


class TestDistrictsConfig:
    """Tests for config/districts.json structure and content."""

    def test_config_file_exists(self):
        assert CONFIG_FILE.exists(), "districts.json must exist"

    def test_config_is_valid_json(self):
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        assert isinstance(data, list)

    def test_config_has_districts(self, districts):
        assert len(districts) > 0, "Must have at least one district"

    def test_minimum_district_count(self, districts):
        """Should have a substantial number of districts across the state."""
        assert len(districts) >= 50, f"Expected >= 50 districts, got {len(districts)}"

    def test_each_district_has_required_fields(self, districts):
        for d in districts:
            assert "name" in d, f"District missing 'name': {d}"
            assert "instid" in d, f"District {d.get('name')} missing 'instid'"
            assert "boces" in d, f"District {d.get('name')} missing 'boces'"

    def test_instid_format(self, districts):
        """NYSED institution IDs should be 12-digit strings."""
        for d in districts:
            instid = d["instid"]
            assert isinstance(instid, str), f"{d['name']}: instid must be string"
            assert len(instid) == 12, f"{d['name']}: instid must be 12 digits, got {len(instid)}"
            assert instid.isdigit(), f"{d['name']}: instid must be all digits"

    def test_district_names_unique(self, districts):
        names = [d["name"] for d in districts]
        assert len(names) == len(set(names)), "District names must be unique"

    def test_instids_unique(self, districts):
        instids = [d["instid"] for d in districts]
        assert len(instids) == len(set(instids)), "Institution IDs must be unique"

    def test_original_districts_present(self, districts):
        """The original 3 districts must still be present."""
        names = {d["name"] for d in districts}
        assert "Niskayuna" in names
        assert "Bethlehem" in names
        assert "Shenendehowa" in names

    def test_original_districts_have_budget_url(self, districts):
        for d in districts:
            if d["name"] in ("Niskayuna", "Bethlehem", "Shenendehowa"):
                assert "budget_url" in d, f"{d['name']} should have budget_url"
                assert d["budget_url"].startswith("https://"), f"{d['name']} budget_url must be HTTPS"

    def test_multiple_boces_regions(self, districts):
        """Should have districts from many BOCES regions."""
        boces_set = {d["boces"] for d in districts}
        assert len(boces_set) >= 10, f"Expected >= 10 BOCES regions, got {len(boces_set)}"

    def test_each_boces_has_multiple_districts(self, districts):
        """Each BOCES should have at least 2 districts for meaningful clustering."""
        from collections import Counter
        boces_counts = Counter(d["boces"] for d in districts)
        for boces, count in boces_counts.items():
            assert count >= 2, f"BOCES '{boces}' has only {count} district(s); need >= 2"

    def test_boces_names_are_nonempty(self, districts):
        for d in districts:
            assert d["boces"].strip(), f"District {d['name']} has empty boces"

    def test_niskayuna_boces(self, districts):
        nisk = next(d for d in districts if d["name"] == "Niskayuna")
        assert nisk["boces"] == "Capital Region BOCES"

    def test_bethlehem_boces(self, districts):
        beth = next(d for d in districts if d["name"] == "Bethlehem")
        assert beth["boces"] == "Questar III BOCES"
