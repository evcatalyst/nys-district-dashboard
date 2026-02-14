"""Tests for build_specs.py — BOCES clustering and spec generation."""

import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

# Ensure scripts/ is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_specs import SpecBuilder


@pytest.fixture
def builder(tmp_path):
    """Create a SpecBuilder with temp directories and sample data."""
    # Set up temp directories
    out_data = tmp_path / "out" / "data"
    out_spec = tmp_path / "out" / "spec"
    config_dir = tmp_path / "config"
    seed_dir = tmp_path / "data" / "seed"
    out_data.mkdir(parents=True)
    out_spec.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    seed_dir.mkdir(parents=True)

    # Patch module-level paths
    import build_specs
    build_specs.OUT_DATA_DIR = out_data
    build_specs.OUT_SPEC_DIR = out_spec
    build_specs.SEED_DATA_DIR = seed_dir
    build_specs.CONFIG_DIR = config_dir

    # Create sample config
    config = [
        {"name": "DistA", "instid": "100000000001", "boces": "Region Alpha"},
        {"name": "DistB", "instid": "100000000002", "boces": "Region Alpha"},
        {"name": "DistC", "instid": "200000000001", "boces": "Region Beta"},
        {"name": "DistD", "instid": "200000000002", "boces": "Region Beta"},
    ]
    (config_dir / "districts.json").write_text(json.dumps(config))

    # Create sample assessment CSV
    rows = []
    for name in ["DistA", "DistB", "DistC", "DistD"]:
        for year in [2022, 2023, 2024]:
            for subj in ["ELA", "MATH"]:
                digest = int(hashlib.md5(f"{name}{year}{subj}".encode()).hexdigest(), 16)
                pct = 60 + digest % 30
                rows.append({
                    "district": name, "year": year, "subject": subj,
                    "grade_band": "All", "proficient_pct": pct,
                    "tested_n": 1000, "source_url": "https://example.com"
                })
    pd.DataFrame(rows).to_csv(out_data / "assessments.csv", index=False)

    # Create sample levy CSV
    levy_rows = []
    for name in ["DistA", "DistB", "DistC", "DistD"]:
        for fy in ["2022-2023", "2023-2024", "2024-2025"]:
            digest = int(hashlib.md5(f"{name}{fy}".encode()).hexdigest(), 16)
            pct = 1.0 + digest % 20 / 10.0
            levy_rows.append({
                "district": name, "fiscal_year": fy,
                "levy_pct_change": pct, "levy_limit": "",
                "proposed_levy": "", "source_url": "https://example.com"
            })
    pd.DataFrame(levy_rows).to_csv(out_data / "levy.csv", index=False)

    # Create sample expenditure CSV
    exp_rows = []
    for name in ["DistA", "DistB", "DistC", "DistD"]:
        for sy in ["2021-22", "2022-23", "2023-24"]:
            for cat in ["Educational", "Administrative", "Capital", "Operational"]:
                digest = int(hashlib.md5(f"{name}{sy}{cat}".encode()).hexdigest(), 16)
                pp = 5000 + digest % 20000
                exp_rows.append({
                    "district": name, "school_year": sy, "category": cat,
                    "amount_total": pp * 3000, "per_pupil": pp,
                    "dcaadm": 3000.0, "source_url": "https://example.com"
                })
    pd.DataFrame(exp_rows).to_csv(out_data / "expenditures.csv", index=False)

    b = SpecBuilder()
    return b


class TestSpecBuilder:
    """Tests for SpecBuilder functionality."""

    def test_load_data_from_csv(self, builder):
        builder.load_data()
        assert not builder.assessments_df.empty
        assert not builder.levy_df.empty

    def test_boces_map_populated(self, builder):
        builder.load_data()
        assert "DistA" in builder.boces_map
        assert builder.boces_map["DistA"] == "Region Alpha"
        assert builder.boces_map["DistC"] == "Region Beta"

    def test_build_proficiency_chart(self, builder):
        builder.load_data()
        chart = builder.build_proficiency_chart("DistA")
        assert chart["type"] == "line"
        assert "Proficiency" in chart["title"]
        assert len(chart["data"]) > 0
        assert len(chart["series"]) > 0

    def test_build_proficiency_chart_empty_district(self, builder):
        builder.load_data()
        chart = builder.build_proficiency_chart("NonExistent")
        assert chart["data"] == []

    def test_build_levy_chart(self, builder):
        builder.load_data()
        chart = builder.build_levy_chart("DistA")
        assert chart["type"] == "bar"
        assert "Levy" in chart["title"]
        assert len(chart["data"]) > 0

    def test_build_levy_chart_empty_district(self, builder):
        builder.load_data()
        chart = builder.build_levy_chart("NonExistent")
        assert chart["data"] == []

    def test_build_expenditure_chart(self, builder):
        builder.load_data()
        chart = builder.build_expenditure_chart("DistA")
        assert chart["type"] == "line"
        assert "Per Pupil Expenditures" in chart["title"]
        assert len(chart["data"]) > 0
        series_names = [s["name"] for s in chart["series"]]
        assert len(series_names) == 4
        assert set(series_names) == {"Educational", "Administrative", "Capital", "Operational"}

    def test_build_expenditure_chart_empty_district(self, builder):
        builder.load_data()
        chart = builder.build_expenditure_chart("NonExistent")
        assert chart["data"] == []

    def test_build_district_spec(self, builder):
        builder.load_data()
        spec = builder.build_district_spec("DistA")
        assert spec["district"] == "DistA"
        assert len(spec["charts"]) == 3
        assert "disclaimer" in spec["metadata"]

    def test_compute_boces_benchmarks(self, builder):
        builder.load_data()
        benchmarks = builder.compute_boces_benchmarks()
        assert "Region Alpha" in benchmarks
        assert "Region Beta" in benchmarks
        assert "assessment" in benchmarks["Region Alpha"]
        assert "levy" in benchmarks["Region Alpha"]

    def test_benchmark_data_is_average(self, builder):
        builder.load_data()
        benchmarks = builder.compute_boces_benchmarks()
        # Check that benchmark values are between min/max of constituent districts
        alpha_bench = benchmarks["Region Alpha"]["assessment"]
        for entry in alpha_bench:
            pct = entry["proficient_pct"]
            assert 0 <= pct <= 100, f"Benchmark out of range: {pct}"

    def test_build_boces_cluster_spec(self, builder):
        builder.load_data()
        benchmarks = builder.compute_boces_benchmarks()
        spec = builder.build_boces_cluster_spec(
            "Region Alpha", ["DistA", "DistB"], benchmarks
        )
        assert spec["boces"] == "Region Alpha"
        assert len(spec["charts"]) >= 1
        assert "DistA" in spec["districts"]
        assert "DistB" in spec["districts"]

    def test_cluster_spec_has_benchmark_series(self, builder):
        builder.load_data()
        benchmarks = builder.compute_boces_benchmarks()
        spec = builder.build_boces_cluster_spec(
            "Region Alpha", ["DistA", "DistB"], benchmarks
        )
        # Check proficiency chart has a benchmark series
        prof_chart = spec["charts"][0]
        series_names = [s["name"] for s in prof_chart["series"]]
        assert any("Avg" in n for n in series_names), \
            f"Expected benchmark series, got: {series_names}"

    def test_cluster_spec_benchmark_is_dashed(self, builder):
        builder.load_data()
        benchmarks = builder.compute_boces_benchmarks()
        spec = builder.build_boces_cluster_spec(
            "Region Alpha", ["DistA", "DistB"], benchmarks
        )
        prof_chart = spec["charts"][0]
        bench_series = [s for s in prof_chart["series"] if "Avg" in s["name"]]
        for s in bench_series:
            assert s.get("dashStyle") == "dashed", \
                f"Benchmark series should be dashed: {s['name']}"

    def test_build_all_specs_creates_files(self, builder):
        builder.load_data()
        builder.build_all_specs()

        import build_specs
        spec_dir = build_specs.OUT_SPEC_DIR

        # District specs
        assert (spec_dir / "dista.json").exists()
        assert (spec_dir / "distb.json").exists()

        # BOCES cluster specs
        boces_files = list(spec_dir.glob("boces_*.json"))
        assert len(boces_files) >= 2, f"Expected >= 2 BOCES specs, got {len(boces_files)}"

        # Index
        assert (spec_dir / "index.json").exists()

    def test_index_contains_boces(self, builder):
        builder.load_data()
        builder.build_all_specs()

        import build_specs
        index_file = build_specs.OUT_SPEC_DIR / "index.json"
        with open(index_file) as f:
            index = json.load(f)

        assert "boces" in index
        assert len(index["boces"]) >= 2
        assert all("name" in b for b in index["boces"])
        assert all("spec_file" in b for b in index["boces"])

    def test_index_districts_have_boces(self, builder):
        builder.load_data()
        builder.build_all_specs()

        import build_specs
        index_file = build_specs.OUT_SPEC_DIR / "index.json"
        with open(index_file) as f:
            index = json.load(f)

        for d in index["districts"]:
            assert "boces" in d, f"District {d['name']} missing boces in index"


class TestSeedDataFallback:
    """Test that seed data is used when no fetched data exists."""

    def test_uses_seed_when_out_empty(self, tmp_path):
        import build_specs

        out_data = tmp_path / "out" / "data"
        out_spec = tmp_path / "out" / "spec"
        config_dir = tmp_path / "config"
        seed_dir = tmp_path / "data" / "seed"
        out_data.mkdir(parents=True)
        out_spec.mkdir(parents=True)
        config_dir.mkdir(parents=True)
        seed_dir.mkdir(parents=True)

        # Use real seed data
        real_seed = Path("data/seed")
        if real_seed.exists():
            for f in real_seed.iterdir():
                shutil.copy2(f, seed_dir / f.name)

        # Create minimal config
        config = [{"name": "Niskayuna", "instid": "441101060000", "boces": "Capital Region BOCES"}]
        (config_dir / "districts.json").write_text(json.dumps(config))

        build_specs.OUT_DATA_DIR = out_data
        build_specs.OUT_SPEC_DIR = out_spec
        build_specs.SEED_DATA_DIR = seed_dir
        build_specs.CONFIG_DIR = config_dir

        b = SpecBuilder()
        b.load_data()
        assert not b.assessments_df.empty, "Should fall back to seed data"
