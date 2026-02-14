"""Tests for the seed data files."""

import csv
from pathlib import Path

import pytest

SEED_DIR = Path("data/seed")


class TestSeedAssessments:
    """Tests for data/seed/assessments.csv."""

    @pytest.fixture
    def rows(self):
        with open(SEED_DIR / "assessments.csv") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def test_file_exists(self):
        assert (SEED_DIR / "assessments.csv").exists()

    def test_has_expected_columns(self, rows):
        expected = {"district", "year", "subject", "grade_band", "proficient_pct", "tested_n", "source_url"}
        assert expected == set(rows[0].keys())

    def test_has_multiple_districts(self, rows):
        districts = {r["district"] for r in rows}
        assert len(districts) >= 50, f"Expected >= 50 districts, got {len(districts)}"

    def test_has_ela_and_math(self, rows):
        subjects = {r["subject"] for r in rows}
        assert "ELA" in subjects
        assert "MATH" in subjects

    def test_proficiency_in_range(self, rows):
        for r in rows:
            pct = float(r["proficient_pct"])
            assert 0 <= pct <= 100, f"Proficiency out of range: {pct} for {r['district']}"

    def test_years_present(self, rows):
        years = {int(r["year"]) for r in rows}
        assert 2019 in years
        assert 2024 in years

    def test_original_districts_present(self, rows):
        districts = {r["district"] for r in rows}
        assert "Niskayuna" in districts
        assert "Bethlehem" in districts
        assert "Shenendehowa" in districts

    def test_source_urls_present(self, rows):
        for r in rows:
            assert r["source_url"].startswith("https://"), f"Bad URL for {r['district']}"


class TestSeedLevy:
    """Tests for data/seed/levy.csv."""

    @pytest.fixture
    def rows(self):
        with open(SEED_DIR / "levy.csv") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def test_file_exists(self):
        assert (SEED_DIR / "levy.csv").exists()

    def test_has_expected_columns(self, rows):
        expected = {"district", "fiscal_year", "levy_pct_change", "levy_limit", "proposed_levy", "source_url"}
        assert expected == set(rows[0].keys())

    def test_has_multiple_districts(self, rows):
        districts = {r["district"] for r in rows}
        assert len(districts) >= 50

    def test_levy_pct_is_numeric(self, rows):
        for r in rows:
            if r["levy_pct_change"]:
                pct = float(r["levy_pct_change"])
                assert -10 <= pct <= 20, f"Levy pct out of range: {pct} for {r['district']}"

    def test_fiscal_years_format(self, rows):
        import re
        for r in rows:
            assert re.match(r'\d{4}-\d{4}', r["fiscal_year"]), \
                f"Bad fiscal year: {r['fiscal_year']}"


class TestSeedSources:
    """Tests for data/seed/sources.json."""

    def test_file_exists(self):
        assert (SEED_DIR / "sources.json").exists()

    def test_is_valid_json(self):
        import json
        with open(SEED_DIR / "sources.json") as f:
            data = json.load(f)
        assert isinstance(data, list)

    def test_has_entries(self):
        import json
        with open(SEED_DIR / "sources.json") as f:
            data = json.load(f)
        assert len(data) > 0

    def test_entries_have_required_fields(self):
        import json
        with open(SEED_DIR / "sources.json") as f:
            data = json.load(f)
        for entry in data:
            assert "url" in entry
            assert "status" in entry
            assert "fetched_at" in entry


class TestSeedGraduation:
    """Tests for data/seed/graduation.csv."""

    @pytest.fixture
    def rows(self):
        with open(SEED_DIR / "graduation.csv") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def test_file_exists(self):
        assert (SEED_DIR / "graduation.csv").exists()

    def test_has_expected_columns(self, rows):
        expected = {"district", "year", "metric", "value_pct", "cohort_n", "source_url"}
        assert expected == set(rows[0].keys())

    def test_has_multiple_districts(self, rows):
        districts = {r["district"] for r in rows}
        assert len(districts) >= 50, f"Expected >= 50 districts, got {len(districts)}"

    def test_has_expected_metrics(self, rows):
        metrics = {r["metric"] for r in rows}
        assert "grad_4yr_aug" in metrics
        assert "grad_5yr" in metrics
        assert "grad_6yr" in metrics

    def test_value_in_range(self, rows):
        for r in rows:
            pct = float(r["value_pct"])
            assert 0 <= pct <= 100, f"Value out of range: {pct} for {r['district']}"

    def test_years_present(self, rows):
        years = {int(r["year"]) for r in rows}
        assert 2019 in years
        assert 2024 in years

    def test_original_districts_present(self, rows):
        districts = {r["district"] for r in rows}
        assert "Niskayuna" in districts
        assert "Bethlehem" in districts
        assert "Shenendehowa" in districts


class TestSeedPathways:
    """Tests for data/seed/pathways.csv."""

    @pytest.fixture
    def rows(self):
        with open(SEED_DIR / "pathways.csv") as f:
            reader = csv.DictReader(f)
            return list(reader)

    def test_file_exists(self):
        assert (SEED_DIR / "pathways.csv").exists()

    def test_has_expected_columns(self, rows):
        expected = {"district", "year", "pathway", "value_pct", "cohort_n", "source_url"}
        assert expected == set(rows[0].keys())

    def test_has_multiple_districts(self, rows):
        districts = {r["district"] for r in rows}
        assert len(districts) >= 50, f"Expected >= 50 districts, got {len(districts)}"

    def test_has_expected_pathways(self, rows):
        pathways = {r["pathway"] for r in rows}
        assert "Regents" in pathways
        assert "Advanced Regents" in pathways
        assert "Local" in pathways
        assert "CDOS" in pathways

    def test_value_in_range(self, rows):
        for r in rows:
            pct = float(r["value_pct"])
            assert 0 <= pct <= 100, f"Value out of range: {pct} for {r['district']}"
