#!/usr/bin/env python3
"""
Generate ChartSpec JSON files for visualizations.

Creates small-multiples charts showing:
- Proficiency trends (ELA + Math) over time
- Levy percentage change by year
- BOCES regional benchmarks and clustering

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
SEED_DATA_DIR = Path("data/seed")
CONFIG_DIR = Path("config")


class SpecBuilder:
    """Build ChartSpec JSON specifications."""

    def __init__(self):
        OUT_SPEC_DIR.mkdir(parents=True, exist_ok=True)
        self.districts = []
        self.boces_map = {}  # district_name -> boces_name

    def load_boces_map(self):
        """Load BOCES mapping from config."""
        config_file = CONFIG_DIR / "districts.json"
        if config_file.exists():
            with open(config_file) as f:
                config_districts = json.load(f)
                for d in config_districts:
                    self.boces_map[d['name']] = d.get('boces', 'Unknown')

    def load_data(self):
        """Load normalized data, falling back to seed data if empty."""
        self.load_boces_map()

        assessments_file = OUT_DATA_DIR / "assessments.csv"
        levy_file = OUT_DATA_DIR / "levy.csv"
        seed_assessments = SEED_DATA_DIR / "assessments.csv"
        seed_levy = SEED_DATA_DIR / "levy.csv"
        
        if assessments_file.exists():
            self.assessments_df = pd.read_csv(assessments_file)
        else:
            self.assessments_df = pd.DataFrame()
        
        if self.assessments_df.empty and seed_assessments.exists():
            logger.info("No fetched assessment data; using seed data")
            self.assessments_df = pd.read_csv(seed_assessments)
        elif self.assessments_df.empty:
            logger.warning("No assessments.csv found and no seed data available")
        
        if levy_file.exists():
            self.levy_df = pd.read_csv(levy_file)
        else:
            self.levy_df = pd.DataFrame()
        
        if self.levy_df.empty and seed_levy.exists():
            logger.info("No fetched levy data; using seed data")
            self.levy_df = pd.read_csv(seed_levy)
        elif self.levy_df.empty:
            logger.warning("No levy.csv found and no seed data available")

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

    def compute_boces_benchmarks(self):
        """Compute BOCES regional benchmark averages."""
        benchmarks = {}

        if not self.assessments_df.empty:
            # Add boces column
            df = self.assessments_df.copy()
            df['boces'] = df['district'].map(self.boces_map)
            df = df.dropna(subset=['boces'])

            for boces_name, group in df.groupby('boces'):
                agg = group.groupby(['year', 'subject'])['proficient_pct'].mean().reset_index()
                benchmarks.setdefault(boces_name, {})['assessment'] = [
                    {"year": int(r['year']), "subject": r['subject'],
                     "proficient_pct": round(float(r['proficient_pct']), 1)}
                    for _, r in agg.iterrows()
                ]

        if not self.levy_df.empty:
            df = self.levy_df.copy()
            df['boces'] = df['district'].map(self.boces_map)
            df = df.dropna(subset=['boces'])
            df['levy_pct_change'] = pd.to_numeric(df['levy_pct_change'], errors='coerce')
            df = df.dropna(subset=['levy_pct_change'])

            for boces_name, group in df.groupby('boces'):
                agg = group.groupby('fiscal_year')['levy_pct_change'].mean().reset_index()
                benchmarks.setdefault(boces_name, {})['levy'] = [
                    {"fiscal_year": str(r['fiscal_year']),
                     "levy_pct_change": round(float(r['levy_pct_change']), 2)}
                    for _, r in agg.iterrows()
                ]

        return benchmarks

    def build_boces_cluster_spec(self, boces_name, district_names, benchmarks):
        """Build a cluster comparison spec for a BOCES region."""
        charts = []

        # Proficiency comparison chart
        if not self.assessments_df.empty:
            boces_districts = self.assessments_df[
                self.assessments_df['district'].isin(district_names)
            ]
            if not boces_districts.empty:
                agg = boces_districts.groupby(
                    ['district', 'year', 'subject']
                )['proficient_pct'].mean().reset_index()

                data = []
                for _, row in agg.iterrows():
                    data.append({
                        "district": row['district'],
                        "year": int(row['year']),
                        "subject": row['subject'],
                        "proficient_pct": round(float(row['proficient_pct']), 1)
                    })

                # Add benchmark
                bench_data = benchmarks.get(boces_name, {}).get('assessment', [])
                for b in bench_data:
                    data.append({
                        "district": f"{boces_name} Avg",
                        "year": b['year'],
                        "subject": b['subject'],
                        "proficient_pct": b['proficient_pct']
                    })

                series = []
                colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                          '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
                all_names = sorted(district_names) + [f"{boces_name} Avg"]
                for i, dn in enumerate(all_names):
                    is_bench = dn.endswith(' Avg')
                    for subj in ['ELA', 'MATH']:
                        series.append({
                            "name": f"{dn} {subj}",
                            "field": "proficient_pct",
                            "filter": {"district": dn, "subject": subj},
                            "color": colors[i % len(colors)],
                            "dashStyle": "dashed" if is_bench else "solid"
                        })

                charts.append({
                    "type": "line",
                    "title": f"{boces_name} — ELA & Math Proficiency Comparison",
                    "data": data,
                    "xAxis": {"label": "Year", "field": "year"},
                    "yAxis": {"label": "Proficient %", "min": 0, "max": 100},
                    "series": series,
                    "annotation": "Dashed lines show BOCES regional average. No causal claim is made."
                })

        # Levy comparison chart
        if not self.levy_df.empty:
            boces_levy = self.levy_df[self.levy_df['district'].isin(district_names)]
            if not boces_levy.empty:
                data = []
                for _, row in boces_levy.iterrows():
                    if pd.notna(row['levy_pct_change']) and row['levy_pct_change'] != '':
                        data.append({
                            "district": row['district'],
                            "fiscal_year": str(row['fiscal_year']),
                            "levy_pct_change": float(row['levy_pct_change'])
                        })

                bench_levy = benchmarks.get(boces_name, {}).get('levy', [])
                for b in bench_levy:
                    data.append({
                        "district": f"{boces_name} Avg",
                        "fiscal_year": b['fiscal_year'],
                        "levy_pct_change": b['levy_pct_change']
                    })

                series = []
                all_names = sorted(district_names) + [f"{boces_name} Avg"]
                for i, dn in enumerate(all_names):
                    is_bench = dn.endswith(' Avg')
                    series.append({
                        "name": dn,
                        "field": "levy_pct_change",
                        "filter": {"district": dn},
                        "color": colors[i % len(colors)],
                        "dashStyle": "dashed" if is_bench else "solid"
                    })

                charts.append({
                    "type": "line",
                    "title": f"{boces_name} — Levy Change Comparison",
                    "data": data,
                    "xAxis": {"label": "Fiscal Year", "field": "fiscal_year"},
                    "yAxis": {"label": "Levy % Change", "min": -1, "max": 5},
                    "series": series,
                    "annotation": "Dashed lines show BOCES regional average. No causal claim is made."
                })

        return {
            "boces": boces_name,
            "districts": sorted(district_names),
            "charts": charts,
            "metadata": {
                "generated_at": pd.Timestamp.now().isoformat(),
                "disclaimer": "No causal claim: This dashboard presents public data side-by-side but makes no claims about causation between test scores and budget decisions."
            }
        }

    def build_all_specs(self):
        """Build specs for all districts and BOCES clusters."""
        # Get unique districts from both datasets
        districts = set()
        
        if not self.assessments_df.empty:
            districts.update(self.assessments_df['district'].unique())
        
        if not self.levy_df.empty:
            districts.update(self.levy_df['district'].unique())
        
        # Also add districts from config even if no data
        config_file = CONFIG_DIR / "districts.json"
        if config_file.exists():
            with open(config_file) as f:
                config_districts = json.load(f)
                districts.update([d['name'] for d in config_districts])
        
        if not districts:
            logger.warning("No districts found in data")
            districts = {'Niskayuna', 'Bethlehem', 'Shenendehowa'}
        
        logger.info(f"Building specs for {len(districts)} districts")
        
        # Compute BOCES benchmarks
        benchmarks = self.compute_boces_benchmarks()
        
        # Build spec for each district
        for district in sorted(districts):
            spec = self.build_district_spec(district)
            
            # Save spec file
            filename = f"{district.lower().replace(' ', '_').replace('-', '_')}.json"
            spec_file = OUT_SPEC_DIR / filename
            with open(spec_file, 'w') as f:
                json.dump(spec, f, indent=2)
            
            boces = self.boces_map.get(district, 'Unknown')
            self.districts.append({
                "name": district,
                "spec_file": filename,
                "boces": boces
            })
            
            logger.info(f"Created spec: {filename}")
        
        # Build BOCES cluster specs
        boces_groups = {}
        for d_name, b_name in self.boces_map.items():
            if d_name in districts:
                boces_groups.setdefault(b_name, []).append(d_name)
        
        boces_index = []
        for boces_name in sorted(boces_groups.keys()):
            district_names = boces_groups[boces_name]
            spec = self.build_boces_cluster_spec(boces_name, district_names, benchmarks)
            
            filename = f"boces_{boces_name.lower().replace(' ', '_').replace('/', '_')}.json"
            spec_file = OUT_SPEC_DIR / filename
            with open(spec_file, 'w') as f:
                json.dump(spec, f, indent=2)
            
            boces_index.append({
                "name": boces_name,
                "spec_file": filename,
                "district_count": len(district_names)
            })
            logger.info(f"Created BOCES cluster spec: {filename}")
        
        # Save index
        index_file = OUT_SPEC_DIR / "index.json"
        with open(index_file, 'w') as f:
            json.dump({
                "districts": self.districts,
                "boces": boces_index,
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
