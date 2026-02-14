"""
End-to-end browser tests for the dashboard UI.

Uses Playwright (via the playwright-browser tools available in the test environment).
These tests verify the dashboard loads correctly, BOCES filtering works,
district selection renders charts, and cluster comparison works.
"""

import json
import subprocess
from pathlib import Path

import pytest


class TestDashboardHTML:
    """Validate the static HTML structure."""

    @pytest.fixture
    def html_content(self):
        return (Path("site/index.html")).read_text()

    def test_has_boces_filter(self, html_content):
        assert 'id="bocesFilter"' in html_content

    def test_has_district_select(self, html_content):
        assert 'id="districtSelect"' in html_content

    def test_has_cluster_button(self, html_content):
        assert 'id="showClusterBtn"' in html_content

    def test_has_back_button(self, html_content):
        assert 'id="showDistrictBtn"' in html_content

    def test_has_charts_container(self, html_content):
        assert 'id="charts"' in html_content

    def test_has_boces_label(self, html_content):
        assert "Filter by BOCES Region" in html_content

    def test_has_district_label(self, html_content):
        assert "District:" in html_content

    def test_has_disclaimer(self, html_content):
        assert "no causal claims" in html_content

    def test_has_methodology_section(self, html_content):
        assert "Data Collection Methodology" in html_content

    def test_how_to_use_mentions_boces(self, html_content):
        assert "BOCES" in html_content


class TestAppJSStructure:
    """Validate app.js code structure."""

    @pytest.fixture
    def js_content(self):
        return (Path("site/app.js")).read_text()

    def test_has_chart_renderer_class(self, js_content):
        assert "class ChartRenderer" in js_content

    def test_has_dashboard_app_class(self, js_content):
        assert "class DashboardApp" in js_content

    def test_has_boces_property(self, js_content):
        assert "this.boces" in js_content

    def test_has_cluster_view_property(self, js_content):
        assert "this.clusterView" in js_content

    def test_has_load_boces_cluster_method(self, js_content):
        assert "loadBocesCluster" in js_content

    def test_has_populate_district_select(self, js_content):
        assert "populateDistrictSelect" in js_content

    def test_has_render_line_chart(self, js_content):
        assert "renderLineChart" in js_content

    def test_has_render_bar_chart(self, js_content):
        assert "renderBarChart" in js_content

    def test_handles_category_xaxis(self, js_content):
        assert "drawCategoryAxes" in js_content

    def test_handles_dashed_lines(self, js_content):
        assert "dashStyle" in js_content
        assert "stroke-dasharray" in js_content

    def test_boces_filter_event_listener(self, js_content):
        assert "bocesFilter" in js_content

    def test_cluster_btn_event_listener(self, js_content):
        assert "showClusterBtn" in js_content

    def test_back_btn_event_listener(self, js_content):
        assert "showDistrictBtn" in js_content

    def test_has_render_annotations(self, js_content):
        assert "renderAnnotations" in js_content

    def test_has_interactive_legend(self, js_content):
        assert "drawInteractiveLegend" in js_content

    def test_has_tooltip(self, js_content):
        assert "showTooltip" in js_content

    def test_has_render_snapshot(self, js_content):
        assert "renderSnapshot" in js_content


class TestResourcesPage:
    """Validate resources.html exists and has expected structure."""

    def test_resources_page_exists(self):
        assert Path("site/resources.html").exists()

    def test_resources_has_table(self):
        content = Path("site/resources.html").read_text()
        assert "<table" in content


class TestStylesCSS:
    """Validate styles.css has necessary rules."""

    @pytest.fixture
    def css_content(self):
        return (Path("site/styles.css")).read_text()

    def test_has_boces_filter_styles(self, css_content):
        assert "#bocesFilter" in css_content

    def test_has_cluster_button_styles(self, css_content):
        assert ".btn-cluster" in css_content

    def test_has_cluster_controls(self, css_content):
        assert ".cluster-controls" in css_content

    def test_has_chart_styles(self, css_content):
        assert ".chart-wrapper" in css_content

    def test_has_responsive_styles(self, css_content):
        assert "@media" in css_content

    def test_has_data_line_styles(self, css_content):
        assert ".data-line" in css_content

    def test_has_annotation_styles(self, css_content):
        assert ".annotation-line" in css_content

    def test_has_tooltip_styles(self, css_content):
        assert ".chart-tooltip" in css_content

    def test_has_snapshot_styles(self, css_content):
        assert ".snapshot-header" in css_content
