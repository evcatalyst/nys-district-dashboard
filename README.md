# NYS District Dashboard

[![Build and Deploy](https://github.com/evcatalyst/nys-district-dashboard/actions/workflows/publish.yml/badge.svg)](https://github.com/evcatalyst/nys-district-dashboard/actions/workflows/publish.yml)

An automated data pipeline and visualization dashboard for New York State school district assessment and budget data.

## Overview

This project implements a fully automated pipeline that:
1. Fetches public data from NYSED (New York State Education Department) and school district websites
2. Normalizes the data into structured CSV/JSON formats
3. Generates chart specifications for visualizations
4. Builds a static dashboard site
5. Publishes to GitHub Pages automatically

**Live Dashboard:** https://evcatalyst.github.io/nys-district-dashboard

## Features

- **74 Districts, 18 BOCES Regions**: Comprehensive coverage across New York State
- **BOCES Clustering**: Filter and compare districts within their BOCES region
- **Regional Benchmarks**: Dashed benchmark lines showing BOCES regional averages
- **Automated Data Collection**: Nightly updates from public NYSED sources
- **Proficiency Trends**: ELA and Math assessment data over time
- **Budget Analysis**: School district levy percentage changes
- **No Causal Claims**: Data is presented side-by-side for informational purposes only
- **Full Transparency**: All data sources documented with timestamps and links
- **Integrity Verification**: SHA256 hashes for all generated artifacts

## Repository Structure

```
.
├── config/
│   └── districts.json          # District configuration (instid, budget URLs)
├── scripts/
│   ├── fetch_sources.py        # Download public data sources
│   ├── normalize.py            # Transform to normalized CSV/JSON
│   ├── build_specs.py          # Generate ChartSpec JSON
│   └── build_site.py           # Build static site + manifest
├── site/
│   ├── index.html              # Dashboard HTML
│   ├── app.js                  # Chart renderer (vanilla JS)
│   └── styles.css              # Styling
├── out/                        # Generated site (published to Pages)
│   ├── index.html
│   ├── data/                   # CSV/JSON datasets
│   ├── spec/                   # Chart specifications
│   └── manifest.json           # SHA256 integrity hashes
├── cache/                      # Cached raw data files
├── .github/workflows/
│   └── publish.yml             # GitHub Actions CI/CD
└── requirements.txt            # Python dependencies
```

## Current Districts

The dashboard currently tracks **74 school districts** across **18 BOCES regions** in New York State, including:

- **Capital Region BOCES**: Niskayuna, Shenendehowa, Guilderland, Schenectady, and more
- **Questar III BOCES**: Bethlehem, East Greenbush, Averill Park, Ravena-Coeymans-Selkirk
- **Nassau BOCES**: Great Neck, Garden City, Manhasset, Jericho
- **Monroe 1 BOCES**: Pittsford, Brighton, Penfield, Fairport
- **Southern Westchester BOCES**: Scarsdale, Mamaroneck, Rye, White Plains
- And 13 more BOCES regions across the state

### BOCES Clustering & Benchmarking

Districts are organized by their regional BOCES affiliation. The dashboard supports:
- **Filtering** districts by BOCES region
- **Cluster comparison** of all districts within a BOCES region
- **Regional benchmarks** (dashed lines) showing BOCES average proficiency and levy changes

## Running Tests

```bash
# Install test dependencies
pip install pytest

# Run all tests
python -m pytest tests/ -v
```

The test suite includes:
- **Configuration tests**: Validate districts.json structure, BOCES assignments, instid format
- **Seed data tests**: Validate CSV/JSON data files for completeness and correctness
- **Build specs tests**: Verify BOCES benchmarks, cluster specs, and district spec generation
- **Pipeline integration tests**: Full normalize → build_specs → build_site pipeline
- **Frontend tests**: HTML structure, CSS rules, JS code coverage for BOCES features

## Running Locally

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/evcatalyst/nys-district-dashboard.git
cd nys-district-dashboard

# Install dependencies
pip install -r requirements.txt
```

### Build the Dashboard

Run the scripts in order:

```bash
# 1. Fetch data from public sources
python scripts/fetch_sources.py

# 2. Normalize to structured formats
python scripts/normalize.py

# 3. Generate chart specifications
python scripts/build_specs.py

# 4. Build the static site
python scripts/build_site.py
```

### View Locally

Open `out/index.html` in your web browser:

```bash
# Linux/Mac
open out/index.html

# Or use a simple HTTP server
cd out
python -m http.server 8000
# Then visit http://localhost:8000
```

## Adding a New District

To add a new district to the dashboard:

1. Find the district's NYSED institution ID (instid) from https://data.nysed.gov
2. Find the district's budget/levy notice URL (official district website)
3. Add an entry to `config/districts.json`:

```json
{
  "name": "District Name",
  "instid": "123456789000",
  "budget_url": "https://www.districtwebsite.org/budget"
}
```

4. Re-run the pipeline scripts (or wait for the nightly automated run)

## Data Sources

All data is sourced from public websites:

- **NYSED Assessment Data**: https://data.nysed.gov/assessment38.php
- **NYSED Enrollment Data**: https://data.nysed.gov/enrollment.php
- **District Budget Pages**: Official district websites (URLs in config)

The dashboard does NOT:
- Access any private or restricted data
- Require authentication or API keys
- Make claims about causation between metrics

## Data Provenance

- All fetched sources are documented in `cache/sources.json` with timestamps, URLs, and SHA256 hashes
- This metadata is copied to `out/data/sources.json` and displayed on the dashboard
- The "Sources" section on the live dashboard links to all upstream data

## Automation

The GitHub Actions workflow (`.github/workflows/publish.yml`) runs:

- **Nightly** at 06:00 UTC (via cron schedule)
- **On push** to the `main` branch
- **Manually** via workflow_dispatch

The workflow:
1. Sets up Python 3.11
2. Installs dependencies (with pip caching)
3. Runs all pipeline scripts
4. Deploys to GitHub Pages

Data is cached between runs to minimize redundant fetching.

## Technical Stack

- **Data Collection**: Python (requests, BeautifulSoup, tenacity)
- **Data Processing**: pandas
- **Visualization**: Vanilla JavaScript + SVG (no frameworks)
- **Deployment**: GitHub Actions → GitHub Pages
- **Styling**: Pure CSS (responsive design)

## Design Principles

1. **Public Data Only**: No secrets, no authentication required
2. **Deterministic Builds**: Cached sources, stable filenames
3. **No Causal Claims**: Dashboard presents data side-by-side for informational purposes
4. **Full Transparency**: All sources documented and linked
5. **Minimal Dependencies**: Plain HTML/CSS/JS, no build tools required
6. **Integrity Verification**: SHA256 hashes in manifest.json

## Data Limitations

- **Parsing Challenges**: NYSED HTML pages vary in structure; not all data may be extracted
- **Missing Data**: Some districts/years may have incomplete data
- **No Guarantees**: Data is provided "as-is" from public sources
- **No Expert Analysis**: This is a data presentation tool, not an analytical report

When data cannot be parsed or is unavailable, fields are left blank and warnings are logged.

## Contributing

Contributions welcome! To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the pipeline locally to test
5. Submit a pull request

Please ensure:
- Code follows existing style
- Scripts run without errors
- Changes are minimal and focused
- Documentation is updated

## License

This project is open source. The code is provided as-is for educational and research purposes.

Data sourced from public websites remains subject to their respective terms of use.

## Disclaimer

**This dashboard makes no causal claims.** It presents publicly available assessment and budget data side-by-side for informational purposes only. No inference should be made about causation between test scores and budget decisions.

The dashboard is maintained independently and is not affiliated with or endorsed by:
- New York State Education Department (NYSED)
- Any school district included in the dashboard
- Any government agency

## Contact

For questions or issues, please open a GitHub issue.

---

**Data Last Updated**: Check the live dashboard for the most recent update timestamp.