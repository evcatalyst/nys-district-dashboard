"""Integration tests for the full build pipeline."""

import json
import shutil
from pathlib import Path

import pytest


class TestFullPipeline:
    """Test the full pipeline: normalize -> build_specs -> build_site."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, tmp_path):
        """Set up temp output dirs and run the pipeline once."""
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

        import build_specs
        import build_site

        # Set up dirs
        self.out_dir = tmp_path / "out"
        self.out_data = self.out_dir / "data"
        self.out_spec = self.out_dir / "spec"
        self.out_data.mkdir(parents=True)
        self.out_spec.mkdir(parents=True)

        # Copy real seed data as source
        real_seed = Path("data/seed")
        for f in real_seed.iterdir():
            shutil.copy2(f, self.out_data / f.name)

        # Patch paths
        build_specs.OUT_DATA_DIR = self.out_data
        build_specs.OUT_SPEC_DIR = self.out_spec
        build_specs.SEED_DATA_DIR = real_seed
        build_specs.CONFIG_DIR = Path("config")

        # Run build_specs
        builder = build_specs.SpecBuilder()
        builder.load_data()
        builder.build_all_specs()

        # Run build_site
        build_site.OUT_DIR = self.out_dir
        build_site.SITE_DIR = Path("site")
        site_builder = build_site.SiteBuilder()
        site_builder.copy_site_files()
        site_builder.generate_manifest()

        yield

    def test_index_html_copied(self):
        assert (self.out_dir / "index.html").exists()

    def test_app_js_copied(self):
        assert (self.out_dir / "app.js").exists()

    def test_styles_css_copied(self):
        assert (self.out_dir / "styles.css").exists()

    def test_spec_index_exists(self):
        assert (self.out_spec / "index.json").exists()

    def test_spec_index_has_districts(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        assert len(index["districts"]) >= 50

    def test_spec_index_has_boces(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        assert "boces" in index
        assert len(index["boces"]) >= 10

    def test_district_spec_files_exist(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        for d in index["districts"][:5]:  # spot check first 5
            spec_path = self.out_spec / d["spec_file"]
            assert spec_path.exists(), f"Missing spec: {d['spec_file']}"

    def test_boces_spec_files_exist(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        for b in index["boces"]:
            spec_path = self.out_spec / b["spec_file"]
            assert spec_path.exists(), f"Missing BOCES spec: {b['spec_file']}"

    def test_district_spec_has_charts(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        d = index["districts"][0]
        with open(self.out_spec / d["spec_file"]) as f:
            spec = json.load(f)
        assert "charts" in spec
        assert len(spec["charts"]) >= 1

    def test_boces_spec_has_charts(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        b = index["boces"][0]
        with open(self.out_spec / b["spec_file"]) as f:
            spec = json.load(f)
        assert "charts" in spec
        assert len(spec["charts"]) >= 1

    def test_manifest_exists(self):
        assert (self.out_dir / "manifest.json").exists()

    def test_manifest_has_entries(self):
        with open(self.out_dir / "manifest.json") as f:
            manifest = json.load(f)
        assert len(manifest) > 0
        assert "index.html" in manifest
        assert "app.js" in manifest

    def test_district_specs_have_boces_in_index(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        for d in index["districts"]:
            assert "boces" in d, f"District {d['name']} missing boces in index"

    def test_boces_cluster_has_districts_list(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        b = index["boces"][0]
        with open(self.out_spec / b["spec_file"]) as f:
            spec = json.load(f)
        assert "districts" in spec
        assert len(spec["districts"]) >= 2

    def test_district_spec_has_graduation_charts(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        d = index["districts"][0]
        with open(self.out_spec / d["spec_file"]) as f:
            spec = json.load(f)
        grad_charts = [c for c in spec["charts"] if "Graduation" in c["title"]]
        assert len(grad_charts) >= 1, f"Expected graduation charts, got titles: {[c['title'] for c in spec['charts']]}"

    def test_boces_cluster_proficiency_chart_has_benchmark(self):
        with open(self.out_spec / "index.json") as f:
            index = json.load(f)
        b = index["boces"][0]
        with open(self.out_spec / b["spec_file"]) as f:
            spec = json.load(f)
        # Find proficiency chart
        prof_chart = next((c for c in spec["charts"] if "Proficiency" in c["title"]), None)
        if prof_chart:
            series_names = [s["name"] for s in prof_chart["series"]]
            assert any("Avg" in n for n in series_names), \
                f"Expected benchmark in series: {series_names}"
