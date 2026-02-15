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
- **Automated Data Collection**: Nightly updates with cache-aware refresh cadence (daily for frequent sources, monthly minimum for background sources)
- **Proficiency Trends**: ELA and Math assessment data over time
- **Graduation Rate Trends**: 4-year, 5-year, and 6-year cohort graduation rates over time
- **Graduation Pathways**: Regents, Advanced Regents, Local, and CDOS diploma breakdowns
- **Per-Pupil Expenditure Composition**: Instructional, administrative, and capital spending per pupil
- **Budget Analysis**: School district levy percentage changes
- **Annotation System**: Hand-curated vertical line markers highlighting policy and curriculum inflection points on charts
- **Interactive Legend Toggles & Tooltips**: Click legend items to show/hide series; hover data points for detailed tooltips
- **District Snapshot Header**: At-a-glance summary of the latest key metrics for each district
- **District Resources Page**: Appendix page with links to official district websites, board docs, and budget pages
- **No Causal Claims**: Data is presented side-by-side for informational purposes only
- **Full Transparency**: All data sources documented with timestamps and links
- **Integrity Verification**: SHA256 hashes for all generated artifacts

## Repository Structure

```
.
├── config/
│   ├── districts.json          # District configuration (instid, budget URLs)
│   ├── annotations.json        # Chart annotation markers (policy/curriculum events)
│   ├── resources.json          # District resource links (websites, board docs)
│   └── settings.json           # Year range settings for data fetching
├── scripts/
│   ├── fetch_sources.py        # Download public data sources
│   ├── normalize.py            # Transform to normalized CSV/JSON
│   ├── build_specs.py          # Generate ChartSpec JSON
│   └── build_site.py           # Build static site + manifest
├── site/
│   ├── index.html              # Dashboard HTML
│   ├── resources.html          # District resources appendix page
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

The test suite includes 122+ tests covering:
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
# 1. Fetch data from public sources (with parallel requests)
python scripts/fetch_sources.py

# 2. Normalize to structured formats
python scripts/normalize.py

# 3. Generate chart specifications
python scripts/build_specs.py

# 4. Build the static site
python scripts/build_site.py
```

#### Parallel Data Fetching

The `fetch_sources.py` script now supports **parallel data fetching** to speed up the data collection process. By default, it uses **4 parallel workers** to fetch data from multiple districts simultaneously.

**Environment Variable Configuration:**

You can control the number of parallel workers using the `FETCH_MAX_WORKERS` environment variable:

```bash
# Use 8 parallel workers
FETCH_MAX_WORKERS=8 python scripts/fetch_sources.py

# Use 2 parallel workers (more conservative)
FETCH_MAX_WORKERS=2 python scripts/fetch_sources.py

# Default is 4 if not set
python scripts/fetch_sources.py
```

**Performance Impact:**

With parallel fetching enabled:
- **Sequential (old)**: ~56 requests per district × 82 districts = ~4,600+ sequential requests
- **Parallel (new)**: Up to 4 districts fetched simultaneously, significantly reducing total runtime
- Typical speedup: **3-4x faster** with 4 workers

**GitHub Actions:**

The automated workflow (`.github/workflows/publish.yml`) is configured to use 4 parallel workers by default. This can be adjusted in the workflow file if needed.

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

## Annotations

Annotations are hand-curated vertical line markers displayed on charts to highlight important policy, curriculum, or assessment inflection points (e.g., COVID-19 assessment cancellations, Next Generation Learning Standards rollout).

- Annotations are stored in [`config/annotations.json`](config/annotations.json)
- Each annotation specifies an `id`, `x` position (year or fiscal year), `category`, `label`, `detail`, and which `charts` it applies to
- Annotations can be scoped `"statewide"` or to a specific `"district"`

### Schema

| Field      | Description                                              |
|------------|----------------------------------------------------------|
| `id`       | Unique identifier for the annotation                     |
| `scope`    | `"statewide"` or `"district"`                            |
| `district` | District name (if scope is `"district"`, else `null`)    |
| `axis`     | `"year"` or `"fiscal_year"`                              |
| `x`        | The x-axis position (e.g., `2020` or `"2012-2013"`)     |
| `category` | Category label (e.g., `"Curriculum"`, `"Budget Policy"`) |
| `label`    | Short label shown on the chart                           |
| `detail`   | Longer description shown in tooltips                     |
| `url`      | Source URL for the event                                 |
| `charts`   | Array of chart types: `"proficiency"`, `"graduation"`, `"levy"` |

### Adding a New Annotation

1. Edit `config/annotations.json` and add a new entry following the schema above
2. Run the pipeline locally to verify the annotation renders correctly
3. Submit a pull request

## District Resources

The dashboard includes a **District Resources** appendix page at `/resources.html` that provides quick links to official district websites, board documents, and budget pages.

- Resource links are stored in [`config/resources.json`](config/resources.json)
- Each entry contains the district `name` and optional URLs: `website_url`, `board_docs_url`, `board_meetings_url`, `budget_url`, `transparency_portal_url`

### Contributing District Links

1. Edit `config/resources.json` and fill in any missing URLs for a district
2. Run the pipeline locally to verify the resources page renders correctly
3. Submit a pull request

## Configurable Year Ranges

The file [`config/settings.json`](config/settings.json) controls the year ranges used when fetching and processing data:

| Setting                  | Description                                                  |
|--------------------------|--------------------------------------------------------------|
| `assessments_start_year` | First year of ELA/Math assessment data to fetch              |
| `assessments_end_year`   | Last year of ELA/Math assessment data to fetch               |
| `graduation_start_year`  | First year of graduation rate data to fetch                  |
| `graduation_end_year`    | Last year of graduation rate data to fetch                   |
| `expenditures_start_year`| First year of per-pupil expenditure data to fetch            |
| `expenditures_end_year`  | Last year of per-pupil expenditure data to fetch             |

To adjust the range of data collected, edit `config/settings.json` and re-run the pipeline.

## Data Sources

All data is sourced from public websites:

- **NYSED Assessment Data**: https://data.nysed.gov/assessment38.php
- **NYSED Graduation Rate Data**: https://data.nysed.gov/gradrate.php
- **NYSED Fiscal Profiles (Expenditures)**: https://data.nysed.gov/fiscal.php
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

`fetch_sources.py` refreshes high-churn NYSED district endpoints at most once every 24 hours by default, while lower-churn background sources (fiscal profiles and district budget pages) refresh at least every 30 days. These windows can be tuned with `FREQUENT_REFRESH_HOURS` and `BACKGROUND_REFRESH_DAYS`.

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

> **⚠️ No causal claims.** This dashboard does NOT claim or imply any cause-and-effect relationship between metrics.

It presents publicly available assessment, graduation, expenditure, and budget data side-by-side for informational purposes only. No inference should be made about causation between test scores, graduation rates, and budget decisions.

The dashboard is maintained independently and is not affiliated with or endorsed by:
- New York State Education Department (NYSED)
- Any school district included in the dashboard
- Any government agency

## Contact

For questions or issues, please open a GitHub issue.

---

**Data Last Updated**: Check the live dashboard for the most recent update timestamp.
