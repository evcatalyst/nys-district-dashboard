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
from datetime import datetime
from pathlib import Path
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

# Years to fetch (recent years)
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]
SUBJECTS = ["math", "ela"]


class DataFetcher:
    """Fetch and cache NYS education data sources."""

    def __init__(self):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.sources: List[Dict] = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'NYS-District-Dashboard/1.0 (Educational Research)'
        })

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
        """Record metadata about a fetched source."""
        self.sources.append({
            "url": url,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "status": status,
            "filepath": filepath,
            "etag": etag,
            "last_modified": last_modified,
            "sha256": sha256
        })

    def fetch_assessment_data(self, instid: str, district_name: str):
        """Fetch NYSED assessment data for a district."""
        logger.info(f"Fetching assessment data for {district_name} (instid={instid})")
        
        for year in YEARS:
            for subject in SUBJECTS:
                url = f"https://data.nysed.gov/assessment38.php?instid={instid}&year={year}&subject={subject}"
                logger.info(f"  Fetching {subject.upper()} {year}: {url}")
                
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
        
        for year in YEARS:
            url = f"https://data.nysed.gov/enrollment.php?instid={instid}&year={year}"
            logger.info(f"  Fetching enrollment {year}: {url}")
            
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
    
    # Fetch data for each district
    fetcher = DataFetcher()
    
    for district in districts:
        name = district["name"]
        instid = district["instid"]
        budget_url = district.get("budget_url")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing district: {name}")
        logger.info(f"{'='*60}")
        
        # Fetch assessment data
        fetcher.fetch_assessment_data(instid, name)
        
        # Fetch enrollment data
        fetcher.fetch_enrollment_data(instid, name)
        
        # Fetch budget page if URL provided
        if budget_url:
            fetcher.fetch_budget_page(budget_url, name)
    
    # Save sources metadata
    fetcher.save_sources_metadata()
    
    logger.info("\n" + "="*60)
    logger.info("Data fetching complete!")
    logger.info("="*60)
    
    return 0


if __name__ == "__main__":
    exit(main())
