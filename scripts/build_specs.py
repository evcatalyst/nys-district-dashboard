#!/usr/bin/env python3
"""
Generate ChartSpec JSON files for visualizations.

Creates small-multiples charts showing:
- Proficiency trends (ELA + Math) over time
- Levy percentage change by year

Outputs to out/spec/
"""

import json
import logging
from pathlib import Path
from typing import List, Dict

import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
OUT_DATA_DIR = Path("out/data")
OUT_SPEC_DIR = Path("out/spec")


class SpecBuilder:
    """Build ChartSpec JSON specifications."""

    def __init__(self):
        OUT_SPEC_DIR.mkdir(parents=True, exist_ok=True)
        self.districts = []

    def load_data(self):
        """Load normalized data."""
        assessments_file = OUT_DATA_DIR / "assessments.csv"
        levy_file = OUT_DATA_DIR / "levy.csv"
        
        if assessments_file.exists():
            self.assessments_df = pd.read_csv(assessments_file)
        else:
            self.assessments_df = pd.DataFrame()
            logger.warning("No assessments.csv found")
        
        if levy_file.exists():
            self.levy_df = pd.read_csv(levy_file)
        else:
            self.levy_df = pd.DataFrame()
            logger.warning("No levy.csv found")

    def build_proficiency_chart(self, district: str) -> Dict:
        """Build proficiency trends chart spec."""
        if self.assessments_df.empty:
            return {
                "type": "line",
                "title": f"{district} - Proficiency Trends",
                "data": [],
                "xAxis": {"label": "Year", "field": "year"},
                "yAxis": {"label": "Proficient %", "min": 0, "max": 100},
                "series": []
            }
        
        # Filter data for this district
        district_data = self.assessments_df[self.assessments_df['district'] == district]
        
        if district_data.empty:
            logger.warning(f"No assessment data for {district}")
            return {
                "type": "line",
                "title": f"{district} - Proficiency Trends",
                "data": [],
                "xAxis": {"label": "Year", "field": "year"},
                "yAxis": {"label": "Proficient %", "min": 0, "max": 100},
                "series": []
            }
        
        # Aggregate by year and subject (average across grades)
        aggregated = district_data.groupby(['year', 'subject'])['proficient_pct'].mean().reset_index()
        
        # Prepare data
        data = []
        for _, row in aggregated.iterrows():
            data.append({
                "year": int(row['year']),
                "subject": row['subject'],
                "proficient_pct": round(float(row['proficient_pct']), 1)
            })
        
        # Create series for ELA and Math
        series = []
        for subject in ['ELA', 'MATH']:
            subject_data = [d for d in data if d['subject'] == subject]
            if subject_data:
                series.append({
                    "name": subject,
                    "field": "proficient_pct",
                    "filter": {"subject": subject},
                    "color": "#1f77b4" if subject == "ELA" else "#ff7f0e"
                })
        
        return {
            "type": "line",
            "title": f"{district} - Proficiency Trends",
            "data": data,
            "xAxis": {
                "label": "Year",
                "field": "year"
            },
            "yAxis": {
                "label": "Proficient %",
                "min": 0,
                "max": 100
            },
            "series": series,
            "annotation": "Data shows test score trends. No causal claim is made."
        }

    def build_levy_chart(self, district: str) -> Dict:
        """Build levy change chart spec."""
        if self.levy_df.empty:
            return {
                "type": "bar",
                "title": f"{district} - Levy Change",
                "data": [],
                "xAxis": {"label": "Fiscal Year", "field": "fiscal_year"},
                "yAxis": {"label": "Levy % Change", "min": -5, "max": 10},
                "series": []
            }
        
        # Filter data for this district
        district_levy = self.levy_df[self.levy_df['district'] == district]
        
        if district_levy.empty:
            logger.warning(f"No levy data for {district}")
            return {
                "type": "bar",
                "title": f"{district} - Levy Change",
                "data": [],
                "xAxis": {"label": "Fiscal Year", "field": "fiscal_year"},
                "yAxis": {"label": "Levy % Change", "min": -5, "max": 10},
                "series": []
            }
        
        # Prepare data
        data = []
        for _, row in district_levy.iterrows():
            if pd.notna(row['levy_pct_change']) and row['levy_pct_change'] != '':
                data.append({
                    "fiscal_year": str(row['fiscal_year']),
                    "levy_pct_change": float(row['levy_pct_change'])
                })
        
        return {
            "type": "bar",
            "title": f"{district} - Levy Change",
            "data": data,
            "xAxis": {
                "label": "Fiscal Year",
                "field": "fiscal_year"
            },
            "yAxis": {
                "label": "Levy % Change",
                "min": -5,
                "max": 10
            },
            "series": [
                {
                    "name": "Levy Change",
                    "field": "levy_pct_change",
                    "color": "#2ca02c"
                }
            ],
            "annotation": "Budget levy changes. No causal claim is made."
        }

    def build_district_spec(self, district: str) -> Dict:
        """Build complete spec for a district."""
        return {
            "district": district,
            "charts": [
                self.build_proficiency_chart(district),
                self.build_levy_chart(district)
            ],
            "metadata": {
                "generated_at": pd.Timestamp.now().isoformat(),
                "disclaimer": "No causal claim: This dashboard presents public data side-by-side but makes no claims about causation between test scores and budget decisions."
            }
        }

    def build_all_specs(self):
        """Build specs for all districts."""
        # Get unique districts from both datasets
        districts = set()
        
        if not self.assessments_df.empty:
            districts.update(self.assessments_df['district'].unique())
        
        if not self.levy_df.empty:
            districts.update(self.levy_df['district'].unique())
        
        # Also add districts from config even if no data
        config_file = Path("config/districts.json")
        if config_file.exists():
            with open(config_file) as f:
                config_districts = json.load(f)
                districts.update([d['name'] for d in config_districts])
        
        if not districts:
            logger.warning("No districts found in data")
            districts = {'Niskayuna', 'Bethlehem', 'Shenendehowa'}  # Default from config
        
        logger.info(f"Building specs for {len(districts)} districts")
        
        # Build spec for each district
        for district in sorted(districts):
            spec = self.build_district_spec(district)
            
            # Save spec file
            filename = f"{district.lower().replace(' ', '_')}.json"
            spec_file = OUT_SPEC_DIR / filename
            with open(spec_file, 'w') as f:
                json.dump(spec, f, indent=2)
            
            self.districts.append({
                "name": district,
                "spec_file": filename
            })
            
            logger.info(f"Created spec: {filename}")
        
        # Save index
        index_file = OUT_SPEC_DIR / "index.json"
        with open(index_file, 'w') as f:
            json.dump({
                "districts": self.districts,
                "generated_at": pd.Timestamp.now().isoformat()
            }, f, indent=2)
        
        logger.info(f"Saved spec index: {index_file}")


def main():
    """Main entry point."""
    builder = SpecBuilder()
    builder.load_data()
    builder.build_all_specs()
    
    logger.info("\nSpec generation complete!")
    return 0


if __name__ == "__main__":
    exit(main())
