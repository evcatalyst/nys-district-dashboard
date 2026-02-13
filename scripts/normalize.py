#!/usr/bin/env python3
"""
Normalize cached raw data into structured CSV/JSON files.

Reads from cache/ and produces:
- out/data/assessments.csv
- out/data/enrollment.csv
- out/data/levy.csv
- JSON versions of each
- out/data/sources.json (copy from cache)
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
CACHE_DIR = Path("cache")
OUT_DATA_DIR = Path("out/data")


class DataNormalizer:
    """Normalize raw HTML data to structured formats."""

    def __init__(self):
        OUT_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.assessments: List[Dict] = []
        self.enrollments: List[Dict] = []
        self.levies: List[Dict] = []

    def parse_assessment_html(self, filepath: Path, district: str, year: int, subject: str, source_url: str):
        """Parse NYSED assessment HTML page."""
        logger.info(f"Parsing assessment data: {filepath.name}")
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'lxml')
            
            # Look for assessment tables
            # NYSED typically has tables with grade-level proficiency data
            tables = soup.find_all('table')
            
            if not tables:
                logger.warning(f"No tables found in {filepath.name}")
                return
            
            # Try to find proficiency data in tables
            # This is a simplified parser - actual NYSED format may vary
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 3:
                        # Look for grade band and proficiency percentage
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        
                        # Try to identify grade information
                        for i, text in enumerate(cell_texts):
                            if 'grade' in text.lower() or text.isdigit():
                                # Try to extract proficiency percentage from adjacent cells
                                for j in range(len(cell_texts)):
                                    # Look for percentage values
                                    pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', cell_texts[j])
                                    if pct_match:
                                        try:
                                            proficient_pct = float(pct_match.group(1))
                                            # Look for N tested
                                            tested_n = None
                                            for k in range(len(cell_texts)):
                                                n_match = re.search(r'^(\d+)$', cell_texts[k])
                                                if n_match and int(n_match.group(1)) > 10:  # Reasonable N
                                                    tested_n = int(n_match.group(1))
                                                    break
                                            
                                            self.assessments.append({
                                                'district': district,
                                                'year': year,
                                                'subject': subject,
                                                'grade_band': cell_texts[i] if i < len(cell_texts) else 'All',
                                                'proficient_pct': proficient_pct,
                                                'tested_n': tested_n or '',
                                                'source_url': source_url
                                            })
                                            break
                                        except (ValueError, IndexError):
                                            continue
                                break
        
        except Exception as e:
            logger.warning(f"Error parsing {filepath.name}: {e}")

    def parse_enrollment_html(self, filepath: Path, district: str, year: int, source_url: str):
        """Parse NYSED enrollment HTML page."""
        logger.info(f"Parsing enrollment data: {filepath.name}")
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'lxml')
            
            # Look for total enrollment number
            # NYSED pages typically have "Total" or "All Students" row
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    cell_texts = [cell.get_text(strip=True) for cell in cells]
                    
                    # Look for "Total" or "All" in first column
                    if cell_texts and ('total' in cell_texts[0].lower() or 'all' in cell_texts[0].lower()):
                        # Try to find enrollment number
                        for text in cell_texts[1:]:
                            # Look for a reasonable enrollment number (100-20000)
                            match = re.search(r'^(\d{3,5})$', text.replace(',', ''))
                            if match:
                                enrollment = int(match.group(1))
                                if 100 <= enrollment <= 20000:
                                    self.enrollments.append({
                                        'district': district,
                                        'year': year,
                                        'enrollment_total': enrollment,
                                        'source_url': source_url
                                    })
                                    return
        
        except Exception as e:
            logger.warning(f"Error parsing {filepath.name}: {e}")

    def parse_budget_html(self, filepath: Path, district: str, source_url: str):
        """Parse district budget HTML page for levy information."""
        logger.info(f"Parsing budget data: {filepath.name}")
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                soup = BeautifulSoup(content, 'lxml')
            
            # Look for levy-related keywords
            text = soup.get_text()
            
            # Try to extract fiscal year
            fiscal_year_match = re.search(r'20(\d{2})[/-]20?(\d{2})', text)
            fiscal_year = f"20{fiscal_year_match.group(1)}-20{fiscal_year_match.group(2)}" if fiscal_year_match else ""
            
            # Try to extract levy percentage change
            levy_pct_match = re.search(r'levy.*?(\d+(?:\.\d+)?)\s*%', text, re.IGNORECASE)
            levy_pct = float(levy_pct_match.group(1)) if levy_pct_match else None
            
            # Try to extract levy amounts (in millions/dollars)
            levy_limit_match = re.search(r'levy\s+limit.*?\$?([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
            levy_limit = levy_limit_match.group(1).replace(',', '') if levy_limit_match else ""
            
            proposed_levy_match = re.search(r'proposed\s+levy.*?\$?([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
            proposed_levy = proposed_levy_match.group(1).replace(',', '') if proposed_levy_match else ""
            
            if levy_pct or levy_limit or proposed_levy:
                self.levies.append({
                    'district': district,
                    'fiscal_year': fiscal_year,
                    'levy_pct_change': levy_pct if levy_pct is not None else '',
                    'levy_limit': levy_limit,
                    'proposed_levy': proposed_levy,
                    'source_url': source_url
                })
        
        except Exception as e:
            logger.warning(f"Error parsing {filepath.name}: {e}")

    def process_cached_files(self):
        """Process all cached files."""
        # Load sources metadata
        sources_file = CACHE_DIR / "sources.json"
        if not sources_file.exists():
            logger.error("sources.json not found in cache/")
            return
        
        with open(sources_file) as f:
            sources = json.load(f)
        
        # Process each source
        for source in sources:
            if source['status'] != 'success' or not source.get('filepath'):
                continue
            
            filepath = Path(source['filepath'])
            if not filepath.exists():
                logger.warning(f"File not found: {filepath}")
                continue
            
            url = source['url']
            
            # Determine file type and parse accordingly
            if 'assessment38.php' in url:
                # Extract district, year, subject from URL
                instid_match = re.search(r'instid=(\d+)', url)
                year_match = re.search(r'year=(\d+)', url)
                subject_match = re.search(r'subject=(\w+)', url)
                
                if instid_match and year_match and subject_match:
                    # Extract district name from filename
                    district = filepath.stem.split('_assessment_')[0].replace('_', ' ').title()
                    year = int(year_match.group(1))
                    subject = subject_match.group(1).upper()
                    
                    self.parse_assessment_html(filepath, district, year, subject, url)
            
            elif 'enrollment.php' in url:
                # Extract district, year from URL
                year_match = re.search(r'year=(\d+)', url)
                
                if year_match:
                    district = filepath.stem.split('_enrollment_')[0].replace('_', ' ').title()
                    year = int(year_match.group(1))
                    
                    self.parse_enrollment_html(filepath, district, year, url)
            
            elif '_budget.html' in filepath.name:
                district = filepath.stem.replace('_budget', '').replace('_', ' ').title()
                self.parse_budget_html(filepath, district, url)

    def save_data(self):
        """Save normalized data to CSV and JSON."""
        # Assessments
        if self.assessments:
            df = pd.DataFrame(self.assessments)
            csv_path = OUT_DATA_DIR / "assessments.csv"
            json_path = OUT_DATA_DIR / "assessments.json"
            df.to_csv(csv_path, index=False)
            df.to_json(json_path, orient='records', indent=2)
            logger.info(f"Saved {len(self.assessments)} assessment records")
        else:
            logger.warning("No assessment data found")
            # Create empty files
            pd.DataFrame(columns=['district', 'year', 'subject', 'grade_band', 
                                 'proficient_pct', 'tested_n', 'source_url']).to_csv(
                OUT_DATA_DIR / "assessments.csv", index=False)
        
        # Enrollments
        if self.enrollments:
            df = pd.DataFrame(self.enrollments)
            csv_path = OUT_DATA_DIR / "enrollment.csv"
            json_path = OUT_DATA_DIR / "enrollment.json"
            df.to_csv(csv_path, index=False)
            df.to_json(json_path, orient='records', indent=2)
            logger.info(f"Saved {len(self.enrollments)} enrollment records")
        else:
            logger.warning("No enrollment data found")
            pd.DataFrame(columns=['district', 'year', 'enrollment_total', 
                                 'source_url']).to_csv(
                OUT_DATA_DIR / "enrollment.csv", index=False)
        
        # Levies
        if self.levies:
            df = pd.DataFrame(self.levies)
            csv_path = OUT_DATA_DIR / "levy.csv"
            json_path = OUT_DATA_DIR / "levy.json"
            df.to_csv(csv_path, index=False)
            df.to_json(json_path, orient='records', indent=2)
            logger.info(f"Saved {len(self.levies)} levy records")
        else:
            logger.warning("No levy data found")
            pd.DataFrame(columns=['district', 'fiscal_year', 'levy_pct_change',
                                 'levy_limit', 'proposed_levy', 'source_url']).to_csv(
                OUT_DATA_DIR / "levy.csv", index=False)
        
        # Copy sources.json
        sources_src = CACHE_DIR / "sources.json"
        sources_dst = OUT_DATA_DIR / "sources.json"
        if sources_src.exists():
            sources_dst.write_text(sources_src.read_text())
            logger.info("Copied sources.json to out/data/")


def main():
    """Main entry point."""
    normalizer = DataNormalizer()
    normalizer.process_cached_files()
    normalizer.save_data()
    
    logger.info("\nData normalization complete!")
    return 0


if __name__ == "__main__":
    exit(main())
