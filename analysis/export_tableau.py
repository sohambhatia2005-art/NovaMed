"""
NovaMed SFE — Component 8A: Tableau-Ready CSV Export
=====================================================
Exports 5 fully joined, wide-format CSV files for Tableau Public.
Each CSV is self-contained — Tableau can connect to each independently
without needing further transformation or joining.

Files exported:
1. tableau_rep_performance.csv    — One row per rep (scorecard)
2. tableau_hcp_coverage.csv       — One row per HCP (coverage map)
3. tableau_territory_summary.csv  — One row per city (territory view + lat/lon)
4. tableau_rx_trends.csv          — One row per rep per month (time series)
5. tableau_visit_distribution.csv — Priority bucket current vs recommended

After export, runs data quality checks on every file.

Author: Aditya (NovaMed SFE Portfolio Project)
"""

import os
import pandas as pd
import numpy as np

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
TABLEAU_DIR = os.path.join(BASE_DIR, 'outputs', 'tableau')
os.makedirs(TABLEAU_DIR, exist_ok=True)

TOTAL_MONTHS = 18

# Lat/Lon for the 15 Indian cities (for Tableau map geocoding)
CITY_COORDS = {
    'Delhi':       (28.6139, 77.2090),
    'Lucknow':     (26.8467, 80.9462),
    'Jaipur':      (26.9124, 75.7873),
    'Chandigarh':  (30.7333, 76.7794),
    'Bangalore':   (12.9716, 77.5946),
    'Chennai':     (13.0827, 80.2707),
    'Hyderabad':   (17.3850, 78.4867),
    'Kochi':       (9.9312,  76.2673),
    'Kolkata':     (22.5726, 88.3639),
    'Patna':       (25.6093, 85.1376),
    'Bhubaneswar': (20.2961, 85.8245),
    'Mumbai':      (19.0760, 72.8777),
    'Pune':        (18.5204, 73.8567),
    'Ahmedabad':   (23.0225, 72.5714),
    'Indore':      (22.7196, 75.8577),
}


# ============================================================================
# LOAD ALL SOURCE DATA
# ============================================================================

def load_all_data():
    """Load all raw and processed data needed for exports."""
    data = {}
    
    # Raw
    data['reps'] = pd.read_csv(os.path.join(RAW_DIR, 'reps.csv'))
    data['cities'] = pd.read_csv(os.path.join(RAW_DIR, 'cities.csv'))
    data['hcps'] = pd.read_csv(os.path.join(RAW_DIR, 'hcps.csv'))
    data['visits'] = pd.read_csv(os.path.join(RAW_DIR, 'visit_logs.csv'))
    data['rx'] = pd.read_csv(os.path.join(RAW_DIR, 'rx_volume.csv'))
    
    # Processed
    data['rep_ranking'] = pd.read_csv(os.path.join(PROCESSED_DIR, 'rep_ranking.csv'))
    data['rep_efficiency'] = pd.read_csv(os.path.join(PROCESSED_DIR, 'rep_efficiency.csv'))
    data['hcp_coverage'] = pd.read_csv(os.path.join(PROCESSED_DIR, 'hcp_coverage.csv'))
    data['hcp_categorization'] = pd.read_csv(os.path.join(PROCESSED_DIR, 'hcp_categorization.csv'))
    data['mpi'] = pd.read_csv(os.path.join(PROCESSED_DIR, 'market_potential_index.csv'))
    data['clusters'] = pd.read_csv(os.path.join(PROCESSED_DIR, 'territory_clusters.csv'))
    data['rolling_rx'] = pd.read_csv(os.path.join(PROCESSED_DIR, 'rolling_rx_trend.csv'))
    data['visit_rx_lag'] = pd.read_csv(os.path.join(PROCESSED_DIR, 'visit_rx_lag.csv'))
    data['visit_dist'] = pd.read_csv(os.path.join(PROCESSED_DIR, 'visit_distribution_summary.csv'))
    
    return data


# ============================================================================
# EXPORT 1: Rep Performance (one row per rep)
# ============================================================================

def export_rep_performance(data):
    """
    Wide-format rep scorecard: powers quadrant chart, leaderboard, scorecards.
    One row per rep with all performance metrics and territory context.
    """
    print("  Exporting tableau_rep_performance.csv...")
    
    # Start with rep efficiency (has most fields)
    df = data['rep_efficiency'].copy()
    
    # Add ranking columns from rep_ranking
    ranking = data['rep_ranking'][['rep_id', 'region_rank', 'overall_rank', 'total_rx']]
    # Rename total_rx from ranking to avoid conflict
    ranking = ranking.rename(columns={'total_rx': 'total_rx_generated'})
    df = df.merge(ranking, on='rep_id', how='left')
    
    # Add MPI score for the rep's city
    mpi_by_city = data['mpi'][['city_name', 'mpi_score']]
    df = df.merge(mpi_by_city, left_on='city', right_on='city_name', how='left')
    
    # Add territory cluster label for the rep's city
    cluster_by_city = data['clusters'][['city_name', 'territory_cluster']]
    df = df.merge(cluster_by_city, left_on='city', right_on='city_name', how='left',
                  suffixes=('', '_cluster'))
    
    # Select and rename final columns
    output = df[[
        'rep_id', 'rep_name', 'city', 'region', 'drug_focus', 'tenure_years',
        'total_visits', 'total_rx_generated', 'visit_intensity',
        'efficiency_ratio', 'performance_quadrant',
        'region_rank', 'overall_rank', 'mpi_score', 'territory_cluster'
    ]].copy()
    
    output.to_csv(os.path.join(TABLEAU_DIR, 'tableau_rep_performance.csv'), index=False)
    return output


# ============================================================================
# EXPORT 2: HCP Coverage (one row per HCP)
# ============================================================================

def export_hcp_coverage(data):
    """
    Wide-format HCP coverage: powers coverage map and priority bucket breakdown.
    One row per HCP with coverage metrics, priority bucket, and assigned rep.
    """
    print("  Exporting tableau_hcp_coverage.csv...")
    
    hcps = data['hcps'].copy()
    cities = data['cities'][['city_id', 'city_name']].copy()
    
    # Add city name
    hcps = hcps.merge(cities, on='city_id', how='left')
    
    # Add coverage stats from hcp_coverage
    coverage = data['hcp_coverage'][['hcp_id', 'visits_per_month', 'coverage_flag']].copy()
    hcps = hcps.merge(coverage, on='hcp_id', how='left')
    
    # Add priority bucket from hcp_categorization
    cat = data['hcp_categorization'][['hcp_id', 'priority_bucket', 'avg_rx_lift_pct']].copy()
    cat = cat.rename(columns={'avg_rx_lift_pct': 'post_visit_rx_lift_pct'})
    hcps = hcps.merge(cat, on='hcp_id', how='left')
    
    # Add assigned rep (the rep who visits this HCP most frequently)
    visits = data['visits'].copy()
    rep_hcp_visits = visits.groupby(['hcp_id', 'rep_id']).size().reset_index(name='visit_count')
    # Get the rep with most visits per HCP
    idx = rep_hcp_visits.groupby('hcp_id')['visit_count'].idxmax()
    primary_rep = rep_hcp_visits.loc[idx][['hcp_id', 'rep_id']].copy()
    primary_rep.columns = ['hcp_id', 'assigned_rep_id']
    
    hcps = hcps.merge(primary_rep, on='hcp_id', how='left')
    
    # Add rep name
    rep_names = data['reps'][['rep_id', 'rep_name']].copy()
    rep_names.columns = ['assigned_rep_id', 'assigned_rep_name']
    hcps = hcps.merge(rep_names, on='assigned_rep_id', how='left')
    
    # Select final columns
    output = hcps[[
        'hcp_id', 'hcp_name', 'city_name', 'specialty', 'loyalty_tier',
        'potential_score', 'visits_per_month', 'post_visit_rx_lift_pct',
        'priority_bucket', 'coverage_flag',
        'assigned_rep_id', 'assigned_rep_name'
    ]].copy()
    
    # Rename city_name to city for consistency
    output = output.rename(columns={'city_name': 'city'})
    
    output.to_csv(os.path.join(TABLEAU_DIR, 'tableau_hcp_coverage.csv'), index=False)
    return output


# ============================================================================
# EXPORT 3: Territory Summary (one row per city)
# ============================================================================

def export_territory_summary(data):
    """
    Wide-format territory summary: powers territory map and heatmap.
    One row per city with all KPIs and lat/lon for Tableau geocoding.
    """
    print("  Exporting tableau_territory_summary.csv...")
    
    cities = data['cities'].copy()
    mpi = data['mpi'][['city_id', 'mpi_score']].copy()
    clusters = data['clusters'][['city_id', 'coverage_intensity', 'territory_cluster',
                                  'total_visits', 'num_hcps']].copy()
    
    # City-level efficiency from rep data
    rep_eff = data['rep_efficiency'].copy()
    city_eff = rep_eff.groupby('city').agg(
        avg_visit_intensity=('visit_intensity', 'mean'),
        avg_efficiency_ratio=('efficiency_ratio', 'mean'),
        num_reps_assigned=('rep_id', 'count')
    ).reset_index()
    
    # Total Rx per city (from rep ranking, summed)
    rep_ranking = data['rep_ranking'].copy()
    city_rx = rep_ranking.groupby('city')['total_rx'].sum().reset_index()
    city_rx.columns = ['city', 'total_rx_volume']
    
    # Build output
    output = cities.merge(mpi, on='city_id')
    output = output.merge(clusters, on='city_id')
    output = output.merge(city_eff, left_on='city_name', right_on='city', how='left')
    output = output.merge(city_rx, left_on='city_name', right_on='city', how='left')
    
    # Add lat/lon
    output['latitude'] = output['city_name'].map(lambda x: CITY_COORDS.get(x, (0, 0))[0])
    output['longitude'] = output['city_name'].map(lambda x: CITY_COORDS.get(x, (0, 0))[1])
    
    # Rx per rep
    output['rx_per_rep'] = (output['total_rx_volume'] / output['num_reps_assigned']).round(1)
    
    # Select final columns
    output = output[[
        'city_name', 'region', 'tier', 'population_millions', 'specialist_count',
        'disease_prevalence_index', 'mpi_score',
        'avg_visit_intensity', 'avg_efficiency_ratio', 'territory_cluster',
        'num_reps_assigned', 'total_rx_volume', 'rx_per_rep',
        'latitude', 'longitude'
    ]].sort_values('mpi_score', ascending=False).reset_index(drop=True)
    
    output.to_csv(os.path.join(TABLEAU_DIR, 'tableau_territory_summary.csv'), index=False)
    return output


# ============================================================================
# EXPORT 4: Rx Trends (one row per rep per month)
# ============================================================================

def export_rx_trends(data):
    """
    Time series: powers the trend line chart.
    One row per rep per month with rolling averages and quadrant labels.
    """
    print("  Exporting tableau_rx_trends.csv...")
    
    rolling = data['rolling_rx'].copy()
    
    # Add region and city (already in rolling_rx from the SQL query)
    # Add efficiency ratio and quadrant from rep_efficiency
    rep_metrics = data['rep_efficiency'][['rep_id', 'efficiency_ratio', 'performance_quadrant']].copy()
    output = rolling.merge(rep_metrics, on='rep_id', how='left')
    
    output = output[[
        'rep_id', 'rep_name', 'region', 'city', 'month_year',
        'monthly_rx', 'rolling_3m_avg_rx', 'efficiency_ratio', 'performance_quadrant'
    ]]
    
    output.to_csv(os.path.join(TABLEAU_DIR, 'tableau_rx_trends.csv'), index=False)
    return output


# ============================================================================
# EXPORT 5: Visit Distribution (priority buckets, current vs recommended)
# ============================================================================

def export_visit_distribution(data):
    """
    Before/after visit allocation: powers the waterfall/bar chart.
    Two rows per priority bucket (Current and Recommended states).
    """
    print("  Exporting tableau_visit_distribution.csv...")
    
    visit_dist = data['visit_dist'].copy()
    
    # Reshape to long format: one row per bucket per state
    rows = []
    for _, row in visit_dist.iterrows():
        bucket = row['priority_bucket']
        rx_yield = row['rx_per_visit']
        wasted = row['wasted_effort_flag']
        
        rows.append({
            'priority_bucket': bucket,
            'state': 'Current',
            'visit_share_pct': row['current_visit_share_pct'],
            'rx_yield_per_visit': rx_yield,
            'wasted_effort_flag': wasted
        })
        rows.append({
            'priority_bucket': bucket,
            'state': 'Recommended',
            'visit_share_pct': row['recommended_visit_share_pct'],
            'rx_yield_per_visit': rx_yield,
            'wasted_effort_flag': wasted
        })
    
    output = pd.DataFrame(rows)
    output.to_csv(os.path.join(TABLEAU_DIR, 'tableau_visit_distribution.csv'), index=False)
    return output


# ============================================================================
# DATA QUALITY CHECKS
# ============================================================================

def run_quality_checks(exports):
    """
    Runs comprehensive data quality checks on all exported CSVs.
    """
    print(f"\n{'=' * 70}")
    print("DATA QUALITY CHECKS")
    print(f"{'=' * 70}")
    
    all_passed = True
    
    for name, df in exports.items():
        print(f"\n  --- {name} ---")
        print(f"  Rows: {len(df):,} | Columns: {len(df.columns)}")
        print(f"  Columns: {list(df.columns)}")
        print(f"  First 3 rows:")
        print(df.head(3).to_string(index=False))
        
        # Check 1: No nulls in key columns
        # Define key columns per file
        key_cols_map = {
            'tableau_rep_performance.csv': ['rep_id', 'rep_name', 'city', 'region', 'efficiency_ratio'],
            'tableau_hcp_coverage.csv': ['hcp_id', 'hcp_name', 'city', 'specialty', 'potential_score'],
            'tableau_territory_summary.csv': ['city_name', 'region', 'tier', 'mpi_score', 'latitude', 'longitude'],
            'tableau_rx_trends.csv': ['rep_id', 'rep_name', 'month_year', 'monthly_rx'],
            'tableau_visit_distribution.csv': ['priority_bucket', 'state', 'visit_share_pct']
        }
        
        key_cols = key_cols_map.get(name, [])
        for col in key_cols:
            if col in df.columns:
                null_count = df[col].isna().sum()
                if null_count > 0:
                    print(f"  ⚠ WARNING: {col} has {null_count} null values")
                    all_passed = False
        
        # Check 2: Percentage columns between 0 and 100
        pct_cols = [c for c in df.columns if 'pct' in c.lower() or 'share' in c.lower()]
        for col in pct_cols:
            if col in df.columns and df[col].dtype in ['float64', 'int64']:
                min_val = df[col].min()
                max_val = df[col].max()
                if min_val < -10 or max_val > 110:  # Allow small rounding
                    print(f"  ⚠ WARNING: {col} range [{min_val:.1f}, {max_val:.1f}] exceeds [0, 100]")
                    all_passed = False
        
        # Check 3: ID column uniqueness where expected
        if name == 'tableau_rep_performance.csv':
            if df['rep_id'].nunique() != len(df):
                print(f"  ⚠ WARNING: rep_id has duplicates")
                all_passed = False
            else:
                print(f"  ✓ rep_id is unique ({df['rep_id'].nunique()} unique)")
        elif name == 'tableau_hcp_coverage.csv':
            if df['hcp_id'].nunique() != len(df):
                print(f"  ⚠ WARNING: hcp_id has duplicates")
                all_passed = False
            else:
                print(f"  ✓ hcp_id is unique ({df['hcp_id'].nunique()} unique)")
        elif name == 'tableau_territory_summary.csv':
            if df['city_name'].nunique() != len(df):
                print(f"  ⚠ WARNING: city_name has duplicates")
                all_passed = False
            else:
                print(f"  ✓ city_name is unique ({df['city_name'].nunique()} unique)")
    
    print(f"\n  {'✓ ALL CHECKS PASSED' if all_passed else '⚠ SOME CHECKS FAILED — review warnings above'}")
    return all_passed


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("NovaMed SFE — Component 8A: Tableau CSV Export")
    print("=" * 70)
    
    data = load_all_data()
    
    exports = {}
    exports['tableau_rep_performance.csv'] = export_rep_performance(data)
    exports['tableau_hcp_coverage.csv'] = export_hcp_coverage(data)
    exports['tableau_territory_summary.csv'] = export_territory_summary(data)
    exports['tableau_rx_trends.csv'] = export_rx_trends(data)
    exports['tableau_visit_distribution.csv'] = export_visit_distribution(data)
    
    # Summary
    print(f"\n{'=' * 70}")
    print("EXPORT SUMMARY")
    print(f"{'=' * 70}")
    for name, df in exports.items():
        size_kb = os.path.getsize(os.path.join(TABLEAU_DIR, name)) / 1024
        print(f"  {name:45s} {len(df):>6,} rows × {len(df.columns):>2} cols ({size_kb:.0f} KB)")
    
    # Quality checks
    run_quality_checks(exports)
