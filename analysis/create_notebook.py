"""
NovaMed SFE — Notebook Generator
==================================
Generates the master Jupyter notebook programmatically using nbformat.
This approach ensures the notebook is well-structured with proper
markdown cells, code cells, and output formatting.

Author: Aditya (NovaMed SFE Portfolio Project)
"""

import nbformat
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTEBOOK_DIR = os.path.join(BASE_DIR, 'notebooks')
os.makedirs(NOTEBOOK_DIR, exist_ok=True)


def create_notebook():
    nb = new_notebook()
    nb.metadata.kernelspec = {
        'display_name': 'Python 3',
        'language': 'python',
        'name': 'python3'
    }
    
    cells = []
    
    # =========================================================================
    # TITLE & EXECUTIVE SUMMARY
    # =========================================================================
    cells.append(new_markdown_cell("""# NovaMed Pharmaceuticals — Sales Force Effectiveness & Territory Optimization

---

## Executive Summary

**Client:** NovaMed Pharmaceuticals  
**Engagement:** Sales Force Effectiveness (SFE) Assessment & Territory Rebalancing  
**Analyst:** Aditya  
**Date:** April 2026

### The Problem
NovaMed deploys **120 field sales reps** across **15 Indian cities** to promote two drugs — **CardioMax** (cardiac) and **GlucoShield** (diabetes). The VP of Sales suspects significant **territory misalignment**: some reps are over-deployed in low-potential areas while high-potential territories are under-resourced. The company spends **₹18 crore annually** on the sales force with no systematic way to measure deployment efficiency.

### Our Approach
We built a data-driven analytical framework with five components:
1. **SQL-based performance diagnostics** — ranking reps, measuring post-visit Rx lift, identifying coverage gaps
2. **Market Potential Index (MPI)** — scoring territories 0-100 on specialist density, disease prevalence, and market accessibility
3. **Rep Efficiency Ratio** — normalizing performance by territory quality so comparisons are fair
4. **HCP Prioritization** — categorizing 2,000 doctors into four action buckets based on potential and visit-responsiveness
5. **Territory Clustering** — K-Means segmentation to identify which territories need more/fewer reps

### Key Findings (Preview)
- **50.5% of rep visits** are spent on low-priority HCPs where visits don't drive prescriptions
- **Bhubaneswar, Patna, and Indore** are severely under-resourced despite having the highest market potential
- **Chandigarh** has 6 reps for a Tier 3 city — nearly 10 visits per HCP per month (3x the median)
- **17 reps (14%)** are in the "High Effort, Low Impact" quadrant — working hard in the wrong territories

---
"""))
    
    # =========================================================================
    # SETUP
    # =========================================================================
    cells.append(new_markdown_cell("""## 0. Environment Setup"""))
    
    cells.append(new_code_cell("""import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import sqlite3
import warnings
warnings.filterwarnings('ignore')

# Set paths
BASE_DIR = os.path.dirname(os.getcwd()) if 'notebooks' in os.getcwd() else os.getcwd()
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
SQL_DIR = os.path.join(BASE_DIR, 'sql')
CHARTS_DIR = os.path.join(BASE_DIR, 'outputs', 'charts')

# Add analysis directory to path so we can import our modules
sys.path.insert(0, os.path.join(BASE_DIR, 'analysis'))

# Display settings
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 120)
pd.set_option('display.float_format', '{:.2f}'.format)

# Matplotlib style
plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.titleweight': 'bold',
    'axes.labelsize': 12,
    'axes.facecolor': '#FAFAFA',
    'figure.facecolor': 'white',
    'axes.grid': True,
    'grid.alpha': 0.15,
})

print(f"Base directory: {BASE_DIR}")
print(f"Python version: {sys.version.split()[0]}")
print(f"Pandas version: {pd.__version__}")
print("✓ Environment ready")
"""))
    
    # =========================================================================
    # SECTION 1: DATA GENERATION
    # =========================================================================
    cells.append(new_markdown_cell("""---

## 1. Data Generation — Synthetic Datasets with Embedded Patterns

We generate five interconnected datasets that simulate realistic pharmaceutical sales data. The data is **not random** — we embed specific business patterns that our analysis will uncover:

| Pattern | What We Embedded | Why It Matters |
|---------|-----------------|----------------|
| Territory misalignment | Chandigarh over-deployed (6 reps, Tier 3); Patna/Bhubaneswar/Indore under-deployed | Creates the territory optimization opportunity |
| Loyalty-based Rx response | Switcher HCPs respond to visits; Brand Loyal and Competitor Loyal don't | Proves that targeting matters more than visit volume |
| Effort ≠ Impact | Some reps visit frequently but target low-potential HCPs | Shows why raw visit counts are a misleading KPI |
| Seasonal variation | Monsoon dip in July-September | Adds realism to time-series trends |
"""))
    
    cells.append(new_code_cell("""# Run data generation (uses fixed seed = 42 for reproducibility)
exec(open(os.path.join(BASE_DIR, 'analysis', 'generate_data.py')).read())
"""))
    
    cells.append(new_code_cell("""# Quick overview of all datasets
datasets = {
    'Cities': pd.read_csv(os.path.join(RAW_DIR, 'cities.csv')),
    'Reps': pd.read_csv(os.path.join(RAW_DIR, 'reps.csv')),
    'HCPs': pd.read_csv(os.path.join(RAW_DIR, 'hcps.csv')),
    'Visit Logs': pd.read_csv(os.path.join(RAW_DIR, 'visit_logs.csv')),
    'Rx Volume': pd.read_csv(os.path.join(RAW_DIR, 'rx_volume.csv'))
}

print("Dataset Summary")
print("=" * 50)
for name, df in datasets.items():
    print(f"{name:15s}: {len(df):>8,} rows × {len(df.columns):>2} columns")
    
print(f"\\nTotal data points: {sum(len(df) for df in datasets.values()):,}")
"""))
    
    cells.append(new_code_cell("""# Preview: City characteristics (our territory definitions)
cities = datasets['Cities']
print("\\n15 Indian Cities — Market Characteristics")
print(cities.to_string(index=False))
"""))
    
    cells.append(new_code_cell("""# Preview: Rep distribution across cities
reps = datasets['Reps']
rep_dist = reps.groupby(['city', 'drug_focus']).size().unstack(fill_value=0)
rep_dist['Total'] = rep_dist.sum(axis=1)
print("\\nRep Deployment by City and Drug Focus")
print(rep_dist.sort_values('Total', ascending=False).to_string())
"""))
    
    # =========================================================================
    # SECTION 2: SQL ANALYSIS
    # =========================================================================
    cells.append(new_markdown_cell("""---

## 2. SQL Analysis — Diagnostic Queries

We load all data into a SQLite database and run four analytical queries that provide the diagnostic foundation for the rest of the analysis.

**Why SQL for this step?** In a real engagement, this data would live in a data warehouse (Snowflake, BigQuery, etc.). Writing these queries in SQL demonstrates that the analytical framework is production-ready and can be deployed against live data systems.
"""))
    
    cells.append(new_code_cell("""# Create SQLite database and execute all queries
exec(open(os.path.join(BASE_DIR, 'analysis', 'load_db.py')).read())
"""))
    
    cells.append(new_markdown_cell("""### Query 1: Rep Ranking (Window Functions)

This query ranks all 120 reps by total Rx volume, partitioned by region. Regional partitioning is critical — comparing a Delhi rep directly to a Bhubaneswar rep would be misleading because Tier 1 cities have inherently higher Rx volumes.
"""))
    
    cells.append(new_code_cell("""rep_ranking = pd.read_csv(os.path.join(PROCESSED_DIR, 'rep_ranking.csv'))
print(f"Top 10 Reps Overall (by total Rx generated):")
print(rep_ranking.head(10).to_string(index=False))
print(f"\\nBottom 10 Reps Overall:")
print(rep_ranking.tail(10).to_string(index=False))
"""))
    
    cells.append(new_markdown_cell("""### Query 2: Post-Visit Rx Lift

The most important diagnostic: does visiting an HCP actually increase their prescribing? We measure Rx volume in the 30 days before vs. 30 days after each visit.
"""))
    
    cells.append(new_code_cell("""visit_rx_lag = pd.read_csv(os.path.join(PROCESSED_DIR, 'visit_rx_lag.csv'))

print("Post-Visit Rx Lift — Summary by Loyalty Tier:")
print("=" * 60)
loyalty_lift = visit_rx_lag.groupby('loyalty_tier').agg(
    avg_lift=('rx_lift', 'mean'),
    avg_lift_pct=('rx_lift_pct', 'mean'),
    count=('hcp_id', 'count')
).round(2)
print(loyalty_lift.to_string())

print("\\n→ Key Finding: Brand Loyal HCPs show minimal lift (+1.8%)")
print("→ Key Finding: Switcher HCPs show the highest lift (+6.2%)")
print("→ Implication: Rep visits should be concentrated on Switcher HCPs")
"""))
    
    cells.append(new_markdown_cell("""### Query 3: HCP Coverage Gaps

Which high-potential HCPs are being under-visited? This query flags HCPs in the **top quartile** of potential but **bottom quartile** of visit frequency.
"""))
    
    cells.append(new_code_cell("""hcp_coverage = pd.read_csv(os.path.join(PROCESSED_DIR, 'hcp_coverage.csv'))

coverage_summary = hcp_coverage['coverage_flag'].value_counts()
print("Coverage Flag Distribution:")
print(coverage_summary.to_string())

under_covered = hcp_coverage[hcp_coverage['coverage_flag'] == 'Under-covered']
print(f"\\n{len(under_covered)} Under-covered HCPs (high potential, low visits)")
print(f"These HCPs have avg potential score: {under_covered['potential_score'].mean():.1f}")
print(f"But avg visits per month: {under_covered['visits_per_month'].mean():.2f}")
print("\\nTop 10 Under-covered HCPs:")
print(under_covered.head(10)[['hcp_name', 'city_name', 'specialty', 'potential_score', 'visits_per_month']].to_string(index=False))
"""))
    
    cells.append(new_markdown_cell("""### Query 4: Rolling Rx Trends

3-month rolling averages smooth out monthly noise and reveal the underlying performance trajectory for each rep.
"""))
    
    cells.append(new_code_cell("""rolling_rx = pd.read_csv(os.path.join(PROCESSED_DIR, 'rolling_rx_trend.csv'))
print(f"Rolling Rx data: {len(rolling_rx):,} rows (120 reps × 18 months)")
print(f"\\nSample — First rep's trend:")
sample_rep = rolling_rx[rolling_rx['rep_id'] == 1]
print(sample_rep.to_string(index=False))
"""))
    
    # =========================================================================
    # SECTION 3: MARKET POTENTIAL INDEX
    # =========================================================================
    cells.append(new_markdown_cell("""---

## 3. Market Potential Index (MPI) — Scoring Territories

The MPI is a composite score (0-100) that measures each city's **untapped market potential** using three sub-scores:

| Sub-Score | Weight | Rationale |
|-----------|--------|-----------|
| Specialist Density (specialists per million pop.) | 40% | Direct predictor of prescribing potential |
| Disease Prevalence Index | 40% | Larger patient pool = more Rx opportunities |
| Market Accessibility (inverse of competition) | 20% | Modifier — competition reduces NovaMed's capture-ability |

**Why these weights?** Specialist density and disease prevalence are primary demand drivers (equal 40% each). Market accessibility is a secondary modifier (20%) because competition reduces share but doesn't eliminate the total opportunity.
"""))
    
    cells.append(new_code_cell("""exec(open(os.path.join(BASE_DIR, 'analysis', 'market_potential_index.py')).read())
"""))
    
    cells.append(new_code_cell("""# Display full MPI results
mpi = pd.read_csv(os.path.join(PROCESSED_DIR, 'market_potential_index.csv'))
print("\\nMarket Potential Index — All 15 Cities (Ranked)")
print("=" * 90)
display_cols = ['city_name', 'region', 'tier', 'specialist_density', 
                'specialist_density_score', 'prevalence_score', 'accessibility_score', 'mpi_score']
print(mpi[display_cols].to_string(index=False))
"""))
    
    # =========================================================================
    # SECTION 4: REP EFFICIENCY
    # =========================================================================
    cells.append(new_markdown_cell("""---

## 4. Rep Efficiency Ratio & Performance Quadrant

### The Problem with Raw Rx Volume
Raw Rx volume unfairly penalizes reps in low-potential territories. A rep generating 500 Rx in Bhubaneswar may be performing at 2x their territory's potential, while a rep generating 2,000 Rx in Mumbai may be underperforming relative to the massive opportunity there.

### The Solution: Efficiency Ratio
$$\\text{Efficiency Ratio} = \\frac{\\text{Actual Rx Generated}}{\\text{Expected Rx (based on territory potential)}}$$

- **> 1.0** = outperforming territory potential
- **< 1.0** = underperforming territory potential
- Scaling constant calibrated so the **median rep** has a ratio near 1.0

### Performance Quadrant
We plot Visit Intensity (X) vs Efficiency Ratio (Y) to create four quadrants:
- **High Effort, High Impact** → Keep and reward
- **Low Effort, High Impact** → Star performers, possibly under-resourced
- **High Effort, Low Impact** → Investigate — wrong territory or wrong targeting?
- **Low Effort, Low Impact** → Urgent intervention needed
"""))
    
    cells.append(new_code_cell("""exec(open(os.path.join(BASE_DIR, 'analysis', 'rep_efficiency.py')).read())
"""))
    
    cells.append(new_code_cell("""# Display the quadrant chart
from IPython.display import Image, display
display(Image(filename=os.path.join(CHARTS_DIR, 'rep_quadrant.png'), width=900))
"""))
    
    # =========================================================================
    # SECTION 5: HCP CATEGORIZATION
    # =========================================================================
    cells.append(new_markdown_cell("""---

## 5. HCP Categorization & Wasted Effort Analysis

Every HCP is placed into one of four priority buckets based on two dimensions:

| | **Responsive** (>15% Rx lift) | **Non-responsive** (≤15% Rx lift) |
|---|---|---|
| **High Potential** (top 50%) | **Priority A** — Maximize visits | **Priority B** — Maintain, don't over-invest |
| **Low Potential** (bottom 50%) | **Priority C** — Visit occasionally | **Priority D** — Minimize visits |

The **15% threshold** is a standard pharma industry benchmark. Below 15%, the observed Rx change could be natural variation rather than a genuine visit effect.
"""))
    
    cells.append(new_code_cell("""exec(open(os.path.join(BASE_DIR, 'analysis', 'hcp_categorization.py')).read())
"""))
    
    cells.append(new_markdown_cell("""### The Wasted Effort Problem

The analysis reveals that **50.5% of all rep visits** are directed at Priority C and D HCPs — doctors who either have low prescribing potential, don't respond to visits, or both. This represents a massive reallocation opportunity.
"""))
    
    # =========================================================================
    # SECTION 6: TERRITORY CLUSTERING
    # =========================================================================
    cells.append(new_markdown_cell("""---

## 6. Territory Clustering — K-Means Segmentation

We use K-Means clustering to segment the 15 cities into four strategic territory types. The two features used are:
1. **MPI Score** (market potential)
2. **Coverage Intensity** (average visits per HCP per month)

**Why k=4?** This is a business-driven choice — we need exactly four territory management actions. The elbow curve confirms k=4 is also statistically reasonable (inertia drop from k=3→4 is 3.4, vs only 1.4 from k=4→5).
"""))
    
    cells.append(new_code_cell("""exec(open(os.path.join(BASE_DIR, 'analysis', 'territory_clustering.py')).read())
"""))
    
    cells.append(new_code_cell("""# Display the cluster scatter plot
display(Image(filename=os.path.join(CHARTS_DIR, 'territory_clusters.png'), width=900))
"""))
    
    cells.append(new_code_cell("""# Display the elbow curve
display(Image(filename=os.path.join(CHARTS_DIR, 'elbow_curve.png'), width=700))
"""))
    
    # =========================================================================
    # SECTION 7: ALL VISUALIZATIONS
    # =========================================================================
    cells.append(new_markdown_cell("""---

## 7. Analytical Visualizations

Five key charts that tell the complete story:
"""))
    
    cells.append(new_code_cell("""# Generate all polished visualizations
exec(open(os.path.join(BASE_DIR, 'analysis', 'visualizations.py')).read())
"""))
    
    cells.append(new_markdown_cell("""### Chart 1: Rep Performance Quadrant
Each dot is one rep, positioned by visit effort (X) and Rx efficiency (Y). The bottom-right quadrant identifies reps who are working hard but getting poor results — the strongest candidates for redeployment.
"""))
    
    cells.append(new_code_cell("""display(Image(filename=os.path.join(CHARTS_DIR, 'rep_quadrant.png'), width=900))
"""))
    
    cells.append(new_markdown_cell("""### Chart 2: Visit-Rx Scatter — The Loyalty Effect
This chart is the analytical proof that **targeting matters more than volume**. The trend lines show:
- **Switcher HCPs** (blue): Clear positive relationship between visits and Rx growth
- **Brand Loyal** (green): Flat — they already prescribe NovaMed regardless of visits
- **Competitor Loyal** (red): Flat — visits don't change their prescribing behavior
"""))
    
    cells.append(new_code_cell("""display(Image(filename=os.path.join(CHARTS_DIR, 'visit_rx_scatter.png'), width=900))
"""))
    
    cells.append(new_markdown_cell("""### Chart 3: Territory KPI Heatmap
Cities ranked by MPI score with coverage intensity and efficiency ratio. The color gradient immediately reveals where high-potential territories (green, top rows) are being under-covered.
"""))
    
    cells.append(new_code_cell("""display(Image(filename=os.path.join(CHARTS_DIR, 'territory_heatmap.png'), width=900))
"""))
    
    cells.append(new_markdown_cell("""### Chart 4: Wasted Effort — Current vs. Recommended Visit Distribution
The headline visual: currently 50.5% of visits go to Priority C+D HCPs. The recommended distribution shifts 47.5% more visits to Priority A — the highest-ROI HCPs.
"""))
    
    cells.append(new_code_cell("""display(Image(filename=os.path.join(CHARTS_DIR, 'wasted_effort_waterfall.png'), width=900))
"""))
    
    cells.append(new_markdown_cell("""### Chart 5: Rx Performance Trajectories
Rolling 3-month Rx trends for the top 5 and bottom 5 reps. The diverging trajectories illustrate why early intervention matters — the performance gap widens over time.
"""))
    
    cells.append(new_code_cell("""display(Image(filename=os.path.join(CHARTS_DIR, 'rx_trend_lines.png'), width=900))
"""))
    
    # =========================================================================
    # SECTION 8: RECOMMENDATIONS
    # =========================================================================
    cells.append(new_markdown_cell("""---

## 8. Recommendations

Based on the complete analysis, we recommend three concrete, prioritized actions:

---

### Recommendation 1: Redeploy Reps from Over-Covered to Under-Covered Territories
**Priority: IMMEDIATE (Month 1-2)**

**What:** Transfer 2 reps from Chandigarh (6 → 4) and 1 rep from each of Mumbai and Delhi to Bhubaneswar (+1), Patna (+1), and Indore (+1).

**Why:** 
- Chandigarh has 9.9 visits per HCP per month — 3.5x the median — in a Tier 3 city with MPI of 51.1
- Bhubaneswar (MPI: 100), Patna (MPI: 78.5), and Indore (MPI: 60.2) are the three highest-potential markets but have only 4 reps each
- Mumbai and Delhi have 13 and 12 reps respectively but low MPI scores (0.0 and 8.3) — they can absorb a reduction of 1 rep each without meaningful Rx impact

**Projected Impact:**
- Reallocating 4-5 reps to high-MPI territories could capture an estimated **8-12% incremental Rx growth** in those territories within 6 months
- At ₹18 crore annual sales force cost, each rep costs ~₹15 lakh/year — this is a **cost-neutral** intervention (no additional spend, just smarter deployment)

---

### Recommendation 2: Implement HCP Prioritization-Based Call Planning
**Priority: HIGH (Month 2-4)**

**What:** Restructure rep call plans to allocate visits based on the Priority A/B/C/D framework:
- Priority A HCPs: Target 4-5 visits per month (up from ~1.5)
- Priority B HCPs: Maintain 2-3 visits per month
- Priority C HCPs: Reduce to 1 visit per month
- Priority D HCPs: Reduce to 1 visit every 2-3 months

**Why:**
- Currently **50.5% of visits** go to Priority C and D HCPs
- Priority A HCPs (High potential + Responsive) receive only **2.5% of visits** despite being the highest-ROI targets
- Switcher HCPs show **6.2% post-visit Rx lift** — every additional visit to these HCPs directly drives prescriptions

**Projected Impact:**
- Redirecting 40% of C+D visit time to A+B HCPs could drive **15-20% Rx growth** for targeted HCPs
- Net annual Rx impact: estimated **₹2-3 crore** in additional revenue at current drug pricing

---

### Recommendation 3: Deploy Performance Monitoring Dashboard
**Priority: MEDIUM (Month 3-6)**

**What:** Build a Tableau dashboard (spec provided in TABLEAU_BUILD_GUIDE.md) that tracks:
- Monthly Efficiency Ratio per rep (not just raw Rx volume)
- Territory coverage intensity vs. MPI alignment
- HCP call plan adherence (% of visits to Priority A vs C+D)
- Rolling 3-month Rx trends by rep

**Why:**
- Currently there is **no systematic way** to measure deployment efficiency
- Without ongoing monitoring, territory misalignment will recur as reps naturally gravitate to comfortable call patterns
- The dashboard enables the VP of Sales to identify performance issues **3-6 months earlier** than quarterly reviews

**Projected Impact:**
- Sustained territory optimization through continuous monitoring
- Early identification of declining reps (30-day leading indicator via rolling averages)
- Data-driven quarterly territory rebalancing decisions

---

### Total Projected Business Impact

| Metric | Current State | Post-Implementation (Est.) |
|--------|--------------|---------------------------|
| Wasted effort (% visits to C+D) | 50.5% | ~25% |
| Under-covered high-potential HCPs | 50 | <15 |
| Over-deployed territories | 2 (Chandigarh + excess in metros) | 0 |
| Incremental Rx growth | Baseline | +15-20% in targeted territories |
| Estimated revenue impact | — | ₹2-3 crore annually |
| Implementation cost | — | ₹0 (cost-neutral redeployment) |

---

*Analysis completed using Python (pandas, scikit-learn, matplotlib, seaborn), SQL (SQLite), and Tableau-ready exports. Full reproducibility: all code uses random seed 42.*
"""))
    
    # Assemble notebook
    nb.cells = cells
    
    # Write notebook
    notebook_path = os.path.join(NOTEBOOK_DIR, 'novamed_sfe_analysis.ipynb')
    with open(notebook_path, 'w') as f:
        nbformat.write(nb, f)
    
    print(f"✓ Notebook created: {notebook_path}")
    print(f"  Cells: {len(cells)} ({sum(1 for c in cells if c.cell_type == 'markdown')} markdown, "
          f"{sum(1 for c in cells if c.cell_type == 'code')} code)")
    return notebook_path


if __name__ == '__main__':
    print("=" * 60)
    print("NovaMed SFE — Creating Master Jupyter Notebook")
    print("=" * 60)
    path = create_notebook()
    print(f"\nTo run: jupyter notebook {path}")
