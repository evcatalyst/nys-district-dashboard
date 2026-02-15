#!/usr/bin/env python3
"""
Fetch public NYS education data sources.

Downloads:
- NYSED assessment data
- NYSED enrollment data
- District budget/levy pages

Writes raw files to cache/ with metadata in cache/sources.json
"""

import json
import logging
import os
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
CACHE_DIR = Path("cache")
CONFIG_DIR = Path("config")
DISTRICTS_CONFIG = CONFIG_DIR / "districts.json"
SOURCES_JSON = CACHE_DIR / "sources.json"

SETTINGS_JSON = CONFIG_DIR / "settings.json"
SUBJECTS = ["math", "ela"]
FREQUENT_REFRESH_HOURS = int(os.getenv("FREQUENT_REFRESH_HOURS", "24"))
BACKGROUND_REFRESH_DAYS = int(os.getenv("BACKGROUND_REFRESH_DAYS", "30"))

# Default year ranges
DEFAULT_SETTINGS = {
    "assessments_start_year": 2014,
    "assessments_end_year": 2024,
    "graduation_start_year": 2014,
    "graduation_end_year": 2024,
    "expenditures_start_year": 2013,
    "expenditures_end_year": 2024,
}


def load_settings() -> Dict:
    """Load settings from config/settings.json, falling back to defaults."""
    if SETTINGS_JSON.exists():
        try:
            with open(SETTINGS_JSON) as f:
                settings = json.load(f)
            logger.info(f"Loaded settings from {SETTINGS_JSON}")
            return {**DEFAULT_SETTINGS, **settings}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Error reading {SETTINGS_JSON}: {e}; using defaults")
    return dict(DEFAULT_SETTINGS)


_settings = load_settings()
ASSESSMENT_YEARS = list(range(
    _settings["assessments_start_year"],
    _settings["assessments_end_year"] + 1,
))
GRADUATION_YEARS = list(range(
    _settings["graduation_start_year"],
    _settings["graduation_end_year"] + 1,
))


class DataFetcher:
    """Fetch and cache NYS education data sources."""

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.sources: List[Dict] = []
        self.sources_lock = Lock()  # Thread-safe access to sources list
        self.frequent_refresh_window = timedelta(hours=FREQUENT_REFRESH_HOURS)
        self.background_refresh_window = timedelta(days=BACKGROUND_REFRESH_DAYS)
        self.previous_sources_by_url = self._load_previous_sources_by_url()
        self.previous_sources_by_filename = self._load_previous_sources_by_filename()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NYS-District-Dashboard/1.0 (Educational Research)'
        })

    def _parse_timestamp(self, timestamp: Optional[str]) -> Optional[datetime]:
        """Parse ISO timestamp and return timezone-aware datetime."""
        if not timestamp:
            return None
        try:
            parsed = datetime.fromisoformat(timestamp)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None

    def _load_previous_sources(self) -> List[Dict]:
        """Load existing sources metadata if available."""
        if not SOURCES_JSON.exists():
            return []
        try:
            data = json.loads(SOURCES_JSON.read_text())
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            logger.warning(f"Could not read previous sources metadata from {SOURCES_JSON}")
        return []

    def _load_previous_sources_by_url(self) -> Dict[str, Dict]:
        """Index previous successful sources by URL."""
        by_url: Dict[str, Dict] = {}
        for source in self._load_previous_sources():
            if source.get("status") != "success":
                continue
            url = source.get("url")
            filepath = source.get("filepath")
            if not url or not filepath or not Path(filepath).exists():
                continue
            existing = by_url.get(url)
            source_ts = self._parse_timestamp(source.get("fetched_at"))
            existing_ts = self._parse_timestamp(existing.get("fetched_at")) if existing else None
            if not existing or (source_ts and (not existing_ts or source_ts >= existing_ts)):
                by_url[url] = source
        return by_url

    def _load_previous_sources_by_filename(self) -> Dict[str, Dict]:
        """Index previous successful sources by filename."""
        by_filename: Dict[str, Dict] = {}
        for source in self.previous_sources_by_url.values():
            filepath = source.get("filepath")
            if not filepath:
                continue
            by_filename[Path(filepath).name] = source
        return by_filename

    def _get_cached_source(self, url: str, refresh_window: timedelta) -> Optional[Dict]:
        """Return a valid cached source entry when not stale."""
        source = self.previous_sources_by_url.get(url)
        if not source:
            return None
        source_ts = self._parse_timestamp(source.get("fetched_at"))
        if not source_ts:
            return None
        if datetime.now(timezone.utc) - source_ts > refresh_window:
            return None
        filepath = source.get("filepath")
        if not filepath or not Path(filepath).exists():
            return None
        return source

    def _record_cached_source(self, source: Dict):
        """Record reuse of cached source while preserving original fetch timestamp."""
        cached_entry = dict(source)
        cached_entry["status"] = "success"
        cached_entry["reused_at"] = datetime.now(timezone.utc).isoformat()
        with self.sources_lock:
            self.sources.append(cached_entry)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_url(self, url: str, timeout: int = 30) -> Optional[requests.Response]:
        """Fetch URL with retries."""
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None

    def compute_sha256(self, content: bytes) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content).hexdigest()

    def save_file(self, content: bytes, filename: str) -> str:
        """Save content to cache directory and return filepath."""
        filepath = CACHE_DIR / filename
        filepath.write_bytes(content)
        return str(filepath)

    def record_source(self, url: str, status: str, filepath: Optional[str] = None,
                     etag: Optional[str] = None, last_modified: Optional[str] = None,
                     sha256: Optional[str] = None):
        """Record metadata about a fetched source (thread-safe)."""
        source_entry = {
            "url": url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "filepath": filepath,
            "etag": etag,
            "last_modified": last_modified,
            "sha256": sha256
        }
        with self.sources_lock:
            self.sources.append(source_entry)

    def fetch_assessment_data(self, instid: str, district_name: str):
        """Fetch NYSED assessment data for a district."""
        logger.info(f"Fetching assessment data for {district_name} (instid={instid})")
        
        for year in ASSESSMENT_YEARS:
            for subject in SUBJECTS:
                url = f"https://data.nysed.gov/assessment38.php?instid={instid}&year={year}&subject={subject}"
                logger.info(f"  Fetching {subject.upper()} {year}: {url}")
                cached_source = self._get_cached_source(url, self.frequent_refresh_window)
                if cached_source:
                    logger.info(f"  Using cached {subject.upper()} {year} for {district_name}")
                    self._record_cached_source(cached_source)
                    continue
                response = self.fetch_url(url)
                if response:
                    filename = f"{district_name.lower().replace(' ', '_')}_assessment_{subject}_{year}.html"
                    filepath = self.save_file(response.content, filename)
                    sha256 = self.compute_sha256(response.content)
                    
                    self.record_source(
                        url=url,
                        status="success",
                        filepath=filepath,
                        etag=response.headers.get('ETag'),
                        last_modified=response.headers.get('Last-Modified'),
                        sha256=sha256
                    )
                else:
                    self.record_source(url=url, status="failed")

    def fetch_enrollment_data(self, instid: str, district_name: str):
        """Fetch NYSED enrollment data for a district."""
        logger.info(f"Fetching enrollment data for {district_name} (instid={instid})")
        
        for year in ASSESSMENT_YEARS:
            url = f"https://data.nysed.gov/enrollment.php?instid={instid}&year={year}"
            logger.info(f"  Fetching enrollment {year}: {url}")
            cached_source = self._get_cached_source(url, self.frequent_refresh_window)
            if cached_source:
                logger.info(f"  Using cached enrollment {year} for {district_name}")
                self._record_cached_source(cached_source)
                continue
            response = self.fetch_url(url)
            if response:
                filename = f"{district_name.lower().replace(' ', '_')}_enrollment_{year}.html"
                filepath = self.save_file(response.content, filename)
                sha256 = self.compute_sha256(response.content)
                
                self.record_source(
                    url=url,
                    status="success",
                    filepath=filepath,
                    etag=response.headers.get('ETag'),
                    last_modified=response.headers.get('Last-Modified'),
                    sha256=sha256
                )
            else:
                self.record_source(url=url, status="failed")

    def fetch_budget_page(self, budget_url: str, district_name: str):
        """Fetch district budget/levy page."""
        logger.info(f"Fetching budget page for {district_name}: {budget_url}")
        cached_source = self._get_cached_source(budget_url, self.background_refresh_window)
        if cached_source:
            logger.info(f"Using cached budget page for {district_name}")
            self._record_cached_source(cached_source)
            return
        response = self.fetch_url(budget_url)
        if response:
            filename = f"{district_name.lower().replace(' ', '_')}_budget.html"
            filepath = self.save_file(response.content, filename)
            sha256 = self.compute_sha256(response.content)
            
            self.record_source(
                url=budget_url,
                status="success",
                filepath=filepath,
                etag=response.headers.get('ETag'),
                last_modified=response.headers.get('Last-Modified'),
                sha256=sha256
            )
        else:
            self.record_source(url=budget_url, status="failed")

    def fetch_fiscal_profiles(self):
        """Fetch NYSED School District Fiscal Profiles XLSX (once for all districts)."""
        cached_fiscal = self.previous_sources_by_filename.get("fiscal_profiles.xlsx")
        if cached_fiscal and self._get_cached_source(
            cached_fiscal.get("url", ""), self.background_refresh_window
        ):
            logger.info("Using cached Fiscal Profiles XLSX")
            self._record_cached_source(cached_fiscal)
            return

        page_url = "https://www.nysed.gov/fiscal-analysis-research/school-district-fiscal-profiles"
        logger.info(f"Fetching Fiscal Profiles page to discover XLSX link: {page_url}")

        xlsx_url = None
        try:
            response = self.fetch_url(page_url)
            if response:
                # Parse page to find the first .xlsx link
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    if href.lower().endswith(".xlsx"):
                        if not href.startswith("http"):
                            href = "https://www.nysed.gov" + href
                        xlsx_url = href
                        break
        except Exception as e:
            logger.warning(f"Error parsing Fiscal Profiles page: {e}")

        if not xlsx_url:
            logger.warning("Could not discover Fiscal Profiles XLSX URL from page")
            self.record_source(url=page_url, status="failed")
            return

        logger.info(f"Downloading Fiscal Profiles XLSX: {xlsx_url}")
        response = self.fetch_url(xlsx_url, timeout=120)
        if response:
            filename = "fiscal_profiles.xlsx"
            filepath = self.save_file(response.content, filename)
            sha256 = self.compute_sha256(response.content)
            self.record_source(
                url=xlsx_url,
                status="success",
                filepath=filepath,
                etag=response.headers.get("ETag"),
                last_modified=response.headers.get("Last-Modified"),
                sha256=sha256,
            )
        else:
            self.record_source(url=xlsx_url, status="failed")

    def fetch_graduation_rate_data(self, instid: str, district_name: str):
        """Fetch NYSED graduation rate data for a district."""
        logger.info(f"Fetching graduation rate data for {district_name} (instid={instid})")
        district_lower = district_name.lower().replace(' ', '_')

        for year in GRADUATION_YEARS:
            url = f"https://data.nysed.gov/gradrate.php?instid={instid}&year={year}"
            logger.info(f"  Fetching grad rate {year}: {url}")
            cached_source = self._get_cached_source(url, self.frequent_refresh_window)
            if cached_source:
                logger.info(f"  Using cached grad rate {year} for {district_name}")
                self._record_cached_source(cached_source)
                continue
            response = self.fetch_url(url)
            if response:
                filename = f"{district_lower}_gradrate_{year}.html"
                filepath = self.save_file(response.content, filename)
                sha256 = self.compute_sha256(response.content)

                self.record_source(
                    url=url,
                    status="success",
                    filepath=filepath,
                    etag=response.headers.get('ETag'),
                    last_modified=response.headers.get('Last-Modified'),
                    sha256=sha256
                )
            else:
                self.record_source(url=url, status="failed")

    def fetch_graduation_pathways_data(self, instid: str, district_name: str):
        """Fetch NYSED graduation pathways data for a district."""
        logger.info(f"Fetching graduation pathways data for {district_name} (instid={instid})")
        district_lower = district_name.lower().replace(' ', '_')

        for year in GRADUATION_YEARS:
            url = f"https://data.nysed.gov/gradrate.php?instid={instid}&year={year}"
            logger.info(f"  Fetching pathways {year}: {url}")

            try:
                cached_source = self._get_cached_source(url, self.frequent_refresh_window)
                if cached_source:
                    logger.info(f"  Using cached pathways {year} for {district_name}")
                    self._record_cached_source(cached_source)
                    continue
                response = self.fetch_url(url)
                if response:
                    filename = f"{district_lower}_pathways_{year}.html"
                    filepath = self.save_file(response.content, filename)
                    sha256 = self.compute_sha256(response.content)

                    self.record_source(
                        url=url,
                        status="success",
                        filepath=filepath,
                        etag=response.headers.get('ETag'),
                        last_modified=response.headers.get('Last-Modified'),
                        sha256=sha256
                    )
                else:
                    logger.warning(f"  Failed to fetch pathways {year} for {district_name}")
                    self.record_source(url=url, status="failed")
            except Exception as e:
                logger.warning(f"  Error fetching pathways {year} for {district_name}: {e}")
                self.record_source(url=url, status="failed")

    def fetch_district_data(self, district: Dict):
        """Fetch all data for a single district.
        
        This method is called in parallel for multiple districts.
        Within a single district, fetch methods execute sequentially.
        """
        name = district["name"]
        instid = district["instid"]
        budget_url = district.get("budget_url")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing district: {name}")
        logger.info(f"{'='*60}")
        
        # Fetch all data types for this district
        # These are independent and can run concurrently
        self.fetch_assessment_data(instid, name)
        self.fetch_enrollment_data(instid, name)
        self.fetch_graduation_rate_data(instid, name)
        self.fetch_graduation_pathways_data(instid, name)
        
        if budget_url:
            self.fetch_budget_page(budget_url, name)
        
        logger.info(f"Completed processing: {name}")
        return name

    def save_sources_metadata(self):
        """Save sources metadata to JSON."""
        SOURCES_JSON.write_text(json.dumps(self.sources, indent=2))
        logger.info(f"Saved sources metadata to {SOURCES_JSON}")
        logger.info(f"Total sources: {len(self.sources)}, "
                   f"Successful: {sum(1 for s in self.sources if s['status'] == 'success')}, "
                   f"Failed: {sum(1 for s in self.sources if s['status'] == 'failed')}")


def main():
    """Main entry point."""
    # Load districts configuration
    if not DISTRICTS_CONFIG.exists():
        logger.error(f"Districts config not found: {DISTRICTS_CONFIG}")
        return 1
    
    with open(DISTRICTS_CONFIG) as f:
        districts = json.load(f)
    
    logger.info(f"Loaded {len(districts)} districts from config")
    
    # Get max workers from environment variable, default to 4
    max_workers = int(os.getenv("FETCH_MAX_WORKERS", "4"))
    logger.info(f"Using {max_workers} parallel workers for district data fetching")
    
    # Fetch data for each district
    fetcher = DataFetcher()
    
    # Fetch fiscal profiles XLSX once (shared across all districts)
    fetcher.fetch_fiscal_profiles()
    
    # Process districts in parallel
    logger.info(f"\n{'='*60}")
    logger.info(f"Starting parallel fetch for {len(districts)} districts")
    logger.info(f"{'='*60}")
    
    completed_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all district fetch tasks
        future_to_district = {
            executor.submit(fetcher.fetch_district_data, district): district
            for district in districts
        }
        
        # Process completed tasks as they finish
        for future in as_completed(future_to_district):
            district = future_to_district[future]
            try:
                district_name = future.result()
                completed_count += 1
                logger.info(f"Progress: {completed_count}/{len(districts)} districts completed")
            except Exception as e:
                logger.error(f"Error processing district {district.get('name', 'unknown')}: {e}")
    
    # Save sources metadata
    fetcher.save_sources_metadata()
    
    logger.info("\n" + "="*60)
    logger.info("Data fetching complete!")
    logger.info("="*60)
    
    return 0


if __name__ == "__main__":
    exit(main())
