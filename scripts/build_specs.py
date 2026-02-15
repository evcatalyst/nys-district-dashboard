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

        # Load expenditures
        expenditures_file = OUT_DATA_DIR / "expenditures.csv"
        seed_expenditures = SEED_DATA_DIR / "expenditures.csv"

        if expenditures_file.exists():
            self.expenditures_df = pd.read_csv(expenditures_file)
        else:
            self.expenditures_df = pd.DataFrame()

        if self.expenditures_df.empty and seed_expenditures.exists():
            logger.info("No fetched expenditure data; using seed data")
            self.expenditures_df = pd.read_csv(seed_expenditures)
        elif self.expenditures_df.empty:
            logger.warning("No expenditures.csv found and no seed data available")

        # Load graduation
        graduation_file = OUT_DATA_DIR / "graduation.csv"
        seed_graduation = SEED_DATA_DIR / "graduation.csv"

        if graduation_file.exists():
            self.graduation_df = pd.read_csv(graduation_file)
        else:
            self.graduation_df = pd.DataFrame()

        if self.graduation_df.empty and seed_graduation.exists():
            logger.info("No fetched graduation data; using seed data")
            self.graduation_df = pd.read_csv(seed_graduation)
        elif self.graduation_df.empty:
            logger.warning("No graduation.csv found and no seed data available")

        # Load pathways
        pathways_file = OUT_DATA_DIR / "pathways.csv"
        seed_pathways = SEED_DATA_DIR / "pathways.csv"

        if pathways_file.exists():
            self.pathways_df = pd.read_csv(pathways_file)
        else:
            self.pathways_df = pd.DataFrame()

        if self.pathways_df.empty and seed_pathways.exists():
            logger.info("No fetched pathways data; using seed data")
            self.pathways_df = pd.read_csv(seed_pathways)
        elif self.pathways_df.empty:
            logger.warning("No pathways.csv found and no seed data available")

        # Load annotations
        annotations_file = CONFIG_DIR / "annotations.json"
        if annotations_file.exists():
            with open(annotations_file) as f:
                self.annotations = json.load(f)
        else:
            self.annotations = []

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

    def build_expenditure_chart(self, district: str) -> Dict:
        """Build per-pupil expenditure chart spec."""
        empty_chart = {
            "type": "line",
            "title": f"{district} - Per Pupil Expenditures (NYSED Fiscal Profiles)",
            "data": [],
            "xAxis": {"label": "School Year", "field": "school_year"},
            "yAxis": {"label": "Per Pupil ($)"},
            "series": [],
            "annotation": (
                "Educational = Instructional expenditures incl. fringe (IE2). "
                "Administrative = Board of Education + Central Administration. "
                "Capital = Debt service principal + interest + transfers to capital fund. "
                "Operational = Total expenditures minus the other three categories (residual). "
                "Denominator: DCAADM. No causal claim is made."
            )
        }

        if self.expenditures_df.empty:
            return empty_chart

        district_data = self.expenditures_df[self.expenditures_df['district'] == district]

        if district_data.empty:
            logger.warning(f"No expenditure data for {district}")
            return empty_chart

        data = []
        for _, row in district_data.iterrows():
            if pd.notna(row.get('per_pupil')) and row['per_pupil'] != '':
                data.append({
                    "school_year": str(row['school_year']),
                    "category": row['category'],
                    "per_pupil": float(row['per_pupil'])
                })

        categories = ["Educational", "Administrative", "Capital", "Operational"]
        colors = {"Educational": "#1f77b4", "Administrative": "#ff7f0e",
                  "Capital": "#2ca02c", "Operational": "#d62728"}

        series = []
        for cat in categories:
            cat_data = [d for d in data if d['category'] == cat]
            if cat_data:
                series.append({
                    "name": cat,
                    "field": "per_pupil",
                    "filter": {"category": cat},
                    "color": colors[cat]
                })

        # Calculate Y-axis range from actual data values
        if data:
            all_values = [d['per_pupil'] for d in data]
            y_min = 0  # Start at 0 for expenditure data
            y_max = max(all_values) * 1.1  # Add 10% padding at top
        else:
            y_min = 0
            y_max = 100

        return {
            "type": "line",
            "title": f"{district} - Per Pupil Expenditures (NYSED Fiscal Profiles)",
            "data": data,
            "xAxis": {"label": "School Year", "field": "school_year"},
            "yAxis": {"label": "Per Pupil ($)", "min": y_min, "max": y_max},
            "series": series,
            "annotation": (
                "Educational = Instructional expenditures incl. fringe (IE2). "
                "Administrative = Board of Education + Central Administration. "
                "Capital = Debt service principal + interest + transfers to capital fund. "
                "Operational = Total expenditures minus the other three categories (residual). "
                "Denominator: DCAADM. No causal claim is made."
            )
        }

    def build_graduation_chart(self, district: str) -> Dict:
        """Build graduation rate trend chart spec."""
        empty_chart = {
            "type": "line",
            "title": f"{district} - Graduation Rate Trend",
            "data": [],
            "xAxis": {"label": "Year", "field": "year"},
            "yAxis": {"label": "Graduation Rate %", "min": 0, "max": 100},
            "series": [],
            "annotation": "Graduation rates by cohort. No causal claim is made."
        }

        if self.graduation_df.empty:
            return empty_chart

        district_data = self.graduation_df[self.graduation_df['district'] == district]

        if district_data.empty:
            logger.warning(f"No graduation data for {district}")
            return empty_chart

        data = []
        for _, row in district_data.iterrows():
            if pd.notna(row.get('value_pct')) and row['value_pct'] != '':
                data.append({
                    "year": int(row['year']),
                    "metric": row['metric'],
                    "value_pct": float(row['value_pct'])
                })

        metric_labels = {
            "grad_4yr_aug": "4-Year (Aug)",
            "grad_5yr": "5-Year",
            "grad_6yr": "6-Year"
        }
        metric_colors = {
            "grad_4yr_aug": "#1f77b4",
            "grad_5yr": "#ff7f0e",
            "grad_6yr": "#2ca02c"
        }

        series = []
        for metric, label in metric_labels.items():
            metric_data = [d for d in data if d['metric'] == metric]
            if metric_data:
                series.append({
                    "name": label,
                    "field": "value_pct",
                    "filter": {"metric": metric},
                    "color": metric_colors[metric]
                })

        return {
            "type": "line",
            "title": f"{district} - Graduation Rate Trend",
            "data": data,
            "xAxis": {"label": "Year", "field": "year"},
            "yAxis": {"label": "Graduation Rate %", "min": 0, "max": 100},
            "series": series,
            "annotation": "Graduation rates by cohort. No causal claim is made."
        }

    def build_pathways_chart(self, district: str) -> Dict:
        """Build graduation pathways chart spec."""
        empty_chart = {
            "type": "line",
            "title": f"{district} - Graduation Pathways",
            "data": [],
            "xAxis": {"label": "Year", "field": "year"},
            "yAxis": {"label": "Pathway %", "min": 0, "max": 100},
            "series": [],
            "annotation": "Graduation pathways. No causal claim is made."
        }

        if self.pathways_df.empty:
            return empty_chart

        district_data = self.pathways_df[self.pathways_df['district'] == district]

        if district_data.empty:
            logger.warning(f"No pathways data for {district}")
            return empty_chart

        data = []
        for _, row in district_data.iterrows():
            if pd.notna(row.get('value_pct')) and row['value_pct'] != '':
                data.append({
                    "year": int(row['year']),
                    "pathway": row['pathway'],
                    "value_pct": float(row['value_pct'])
                })

        pathway_names = ["Regents", "Advanced Regents", "Local", "CDOS"]
        pathway_colors = {
            "Regents": "#1f77b4",
            "Advanced Regents": "#ff7f0e",
            "Local": "#2ca02c",
            "CDOS": "#d62728"
        }

        series = []
        for pw in pathway_names:
            pw_data = [d for d in data if d['pathway'] == pw]
            if pw_data:
                series.append({
                    "name": pw,
                    "field": "value_pct",
                    "filter": {"pathway": pw},
                    "color": pathway_colors[pw]
                })

        return {
            "type": "line",
            "title": f"{district} - Graduation Pathways",
            "data": data,
            "xAxis": {"label": "Year", "field": "year"},
            "yAxis": {"label": "Pathway %", "min": 0, "max": 100},
            "series": series,
            "annotation": "Graduation pathways. No causal claim is made."
        }

    def attach_annotations(self, chart: Dict, chart_id: str, district: str = None):
        """Attach relevant annotations to a chart spec."""
        if not self.annotations:
            return
        matching = []
        for ann in self.annotations:
            if chart_id not in ann.get("charts", []):
                continue
            if ann["scope"] == "district" and ann.get("district") != district:
                continue
            matching.append(ann)
        if matching:
            chart["annotations"] = matching

    def build_district_spec(self, district: str) -> Dict:
        """Build complete spec for a district."""
        proficiency = self.build_proficiency_chart(district)
        self.attach_annotations(proficiency, "proficiency", district)
        levy = self.build_levy_chart(district)
        self.attach_annotations(levy, "levy", district)
        expenditures = self.build_expenditure_chart(district)
        self.attach_annotations(expenditures, "expenditures", district)

        charts = [proficiency, levy, expenditures]

        if not self.graduation_df.empty:
            graduation = self.build_graduation_chart(district)
            self.attach_annotations(graduation, "graduation", district)
            charts.append(graduation)

        if not self.pathways_df.empty:
            pathways = self.build_pathways_chart(district)
            self.attach_annotations(pathways, "pathways", district)
            charts.append(pathways)

        return {
            "district": district,
            "charts": charts,
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

        if not self.graduation_df.empty:
            df = self.graduation_df.copy()
            df['boces'] = df['district'].map(self.boces_map)
            df = df.dropna(subset=['boces'])
            df['value_pct'] = pd.to_numeric(df['value_pct'], errors='coerce')
            df = df.dropna(subset=['value_pct'])

            for boces_name, group in df.groupby('boces'):
                agg = group.groupby(['year', 'metric'])['value_pct'].mean().reset_index()
                benchmarks.setdefault(boces_name, {})['graduation'] = [
                    {"year": int(r['year']), "metric": r['metric'],
                     "value_pct": round(float(r['value_pct']), 1)}
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

        # Graduation comparison chart
        if not self.graduation_df.empty:
            boces_grad = self.graduation_df[
                self.graduation_df['district'].isin(district_names)
            ]
            if not boces_grad.empty:
                colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                          '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']
                boces_grad = boces_grad.copy()
                boces_grad['value_pct'] = pd.to_numeric(boces_grad['value_pct'], errors='coerce')
                boces_grad = boces_grad.dropna(subset=['value_pct'])

                data = []
                for _, row in boces_grad.iterrows():
                    data.append({
                        "district": row['district'],
                        "year": int(row['year']),
                        "metric": row['metric'],
                        "value_pct": round(float(row['value_pct']), 1)
                    })

                bench_grad = benchmarks.get(boces_name, {}).get('graduation', [])
                for b in bench_grad:
                    data.append({
                        "district": f"{boces_name} Avg",
                        "year": b['year'],
                        "metric": b['metric'],
                        "value_pct": b['value_pct']
                    })

                metric_labels = {
                    "grad_4yr_aug": "4-Year (Aug)",
                    "grad_5yr": "5-Year",
                    "grad_6yr": "6-Year"
                }
                series = []
                all_names = sorted(district_names) + [f"{boces_name} Avg"]
                for i, dn in enumerate(all_names):
                    is_bench = dn.endswith(' Avg')
                    for metric, label in metric_labels.items():
                        series.append({
                            "name": f"{dn} {label}",
                            "field": "value_pct",
                            "filter": {"district": dn, "metric": metric},
                            "color": colors[i % len(colors)],
                            "dashStyle": "dashed" if is_bench else "solid"
                        })

                charts.append({
                    "type": "line",
                    "title": f"{boces_name} — Graduation Rate Comparison",
                    "data": data,
                    "xAxis": {"label": "Year", "field": "year"},
                    "yAxis": {"label": "Graduation Rate %", "min": 0, "max": 100},
                    "series": series,
                    "annotation": "Dashed lines show BOCES regional average. No causal claim is made."
                })

        # Attach annotations to all charts
        chart_ids = ["proficiency", "levy", "graduation"]
        for idx, chart in enumerate(charts):
            cid = chart_ids[idx] if idx < len(chart_ids) else "unknown"
            self.attach_annotations(chart, cid)

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

        if not self.graduation_df.empty:
            districts.update(self.graduation_df['district'].unique())

        if not self.pathways_df.empty:
            districts.update(self.pathways_df['district'].unique())
        
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
