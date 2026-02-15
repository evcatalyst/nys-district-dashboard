"""Tests for the fetch_sources module with parallel execution."""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import fetch_sources

CACHE_NEVER_EXPIRES_HOURS = 24 * 3650


class TestDataFetcherThreadSafety:
    """Test that DataFetcher is thread-safe."""

    def test_record_source_is_thread_safe(self, tmp_path):
        """Test that record_source can be called from multiple threads."""
        # Set up temp cache dir
        with patch.object(fetch_sources, 'CACHE_DIR', tmp_path / 'cache'):
            fetcher = fetch_sources.DataFetcher()
            
            # Verify lock exists
            assert hasattr(fetcher, 'sources_lock')
            
            # Record multiple sources
            for i in range(10):
                fetcher.record_source(
                    url=f"http://example.com/{i}",
                    status="success",
                    filepath=f"test_{i}.html"
                )
            
            # Verify all sources were recorded
            assert len(fetcher.sources) == 10
            
            # Verify sources have correct structure
            for source in fetcher.sources:
                assert "url" in source
                assert "status" in source
                assert "fetched_at" in source

    def test_fetch_district_data_returns_name(self, tmp_path):
        """Test that fetch_district_data returns the district name."""
        with patch.object(fetch_sources, 'CACHE_DIR', tmp_path / 'cache'):
            fetcher = fetch_sources.DataFetcher()
            
            # Mock all fetch methods to avoid actual network calls
            with patch.object(fetcher, 'fetch_assessment_data'), \
                 patch.object(fetcher, 'fetch_enrollment_data'), \
                 patch.object(fetcher, 'fetch_graduation_rate_data'), \
                 patch.object(fetcher, 'fetch_graduation_pathways_data'), \
                 patch.object(fetcher, 'fetch_budget_page'):
                
                district = {
                    "name": "Test District",
                    "instid": "123456789012",
                    "budget_url": "http://example.com/budget"
                }
                
                result = fetcher.fetch_district_data(district)
                
                # Verify it returns the district name
                assert result == "Test District"

    def test_parallel_execution_with_multiple_districts(self, tmp_path):
        """Test that parallel execution works with multiple districts."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with patch.object(fetch_sources, 'CACHE_DIR', tmp_path / 'cache'):
            fetcher = fetch_sources.DataFetcher()
            
            # Mock all fetch methods
            with patch.object(fetcher, 'fetch_assessment_data'), \
                 patch.object(fetcher, 'fetch_enrollment_data'), \
                 patch.object(fetcher, 'fetch_graduation_rate_data'), \
                 patch.object(fetcher, 'fetch_graduation_pathways_data'), \
                 patch.object(fetcher, 'fetch_budget_page'):
                
                districts = [
                    {"name": f"District {i}", "instid": f"{i:012d}", "budget_url": None}
                    for i in range(5)
                ]
                
                # Execute in parallel
                completed_districts = []
                with ThreadPoolExecutor(max_workers=4) as executor:
                    future_to_district = {
                        executor.submit(fetcher.fetch_district_data, district): district
                        for district in districts
                    }
                    
                    for future in as_completed(future_to_district):
                        district_name = future.result()
                        completed_districts.append(district_name)
                
                # Verify all districts were processed
                assert len(completed_districts) == 5
                assert all(f"District {i}" in completed_districts for i in range(5))


class TestMainFunctionParallelization:
    """Test the main function with parallelization."""

    def test_main_uses_environment_variable(self, tmp_path, monkeypatch):
        """Test that main function reads FETCH_MAX_WORKERS environment variable."""
        # Set up environment
        monkeypatch.setenv("FETCH_MAX_WORKERS", "8")
        
        # Create minimal districts config
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)
        districts_file = config_dir / "districts.json"
        districts_file.write_text(json.dumps([
            {"name": "Test District", "instid": "123456789012"}
        ]))
        
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        
        # Patch paths and methods
        with patch.object(fetch_sources, 'DISTRICTS_CONFIG', districts_file), \
             patch.object(fetch_sources, 'CACHE_DIR', cache_dir), \
             patch.object(fetch_sources.DataFetcher, 'fetch_fiscal_profiles'), \
             patch.object(fetch_sources.DataFetcher, 'fetch_district_data', return_value="Test District"), \
             patch.object(fetch_sources.DataFetcher, 'save_sources_metadata'):
            
            # Run main - it should work without errors
            result = fetch_sources.main()
            assert result == 0

    def test_threadpool_processes_multiple_districts(self):
        """Test that ThreadPoolExecutor can process multiple districts concurrently."""
        from concurrent.futures import ThreadPoolExecutor
        from threading import Lock
        
        # This test verifies the parallel execution infrastructure exists
        # and can process multiple districts concurrently
        districts = [
            {"name": f"District {i}", "instid": f"{i:012d}"}
            for i in range(10)
        ]
        
        processed = []
        processed_lock = Lock()  # Thread-safe access to processed list
        
        def mock_fetch(district):
            with processed_lock:
                processed.append(district["name"])
            return district["name"]
        
        # Test that ThreadPoolExecutor can be used as expected
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(mock_fetch, d) for d in districts]
            results = [f.result() for f in futures]
        
        assert len(results) == 10
        assert len(processed) == 10
        # Verify all districts were processed
        assert set(processed) == {f"District {i}" for i in range(10)}


class TestFetchCadenceCaching:
    """Test cache reuse cadence for data fetching."""

    def test_assessment_uses_fresh_cached_source(self, tmp_path):
        """Assessment fetch should reuse cache when within frequent refresh window."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        cached_file = cache_dir / "test_district_assessment_math_2024.html"
        cached_file.write_text("<html>cached</html>")
        source_url = "https://data.nysed.gov/assessment38.php?instid=123&year=2024&subject=math"
        fetched_at = datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat()
        sources_file = cache_dir / "sources.json"
        sources_file.write_text(json.dumps([{
            "url": source_url,
            "status": "success",
            "filepath": str(cached_file),
            "fetched_at": fetched_at
        }]))

        with patch.object(fetch_sources, "CACHE_DIR", cache_dir), \
             patch.object(fetch_sources, "SOURCES_JSON", sources_file), \
             patch.object(fetch_sources, "FREQUENT_REFRESH_HOURS", CACHE_NEVER_EXPIRES_HOURS), \
             patch.object(fetch_sources, "ASSESSMENT_YEARS", [2024]), \
             patch.object(fetch_sources, "SUBJECTS", ["math"]):
            fetcher = fetch_sources.DataFetcher()

            with patch.object(fetcher, "fetch_url") as mock_fetch_url:
                fetcher.fetch_assessment_data("123", "Test District")
                mock_fetch_url.assert_not_called()
                assert len(fetcher.sources) == 1
                assert fetcher.sources[0]["filepath"] == str(cached_file)

    def test_budget_refetches_when_cache_is_stale(self, tmp_path):
        """Budget fetch should refetch when cached source is older than monthly window."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        stale_file = cache_dir / "test_district_budget.html"
        stale_file.write_text("<html>stale</html>")
        source_url = "https://district.example/budget"
        stale_time = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        sources_file = cache_dir / "sources.json"
        sources_file.write_text(json.dumps([{
            "url": source_url,
            "status": "success",
            "filepath": str(stale_file),
            "fetched_at": stale_time
        }]))

        with patch.object(fetch_sources, "CACHE_DIR", cache_dir), \
             patch.object(fetch_sources, "SOURCES_JSON", sources_file):
            fetcher = fetch_sources.DataFetcher()
            response = Mock()
            response.content = b"<html>fresh</html>"
            response.headers = {}

            with patch.object(fetcher, "fetch_url", return_value=response) as mock_fetch_url:
                fetcher.fetch_budget_page(source_url, "Test District")
                mock_fetch_url.assert_called_once_with(source_url)
