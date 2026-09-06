"""
NovaMed SFE — Component 4: HCP Categorization & Wasted Effort Analysis
========================================================================
Categorizes every HCP into one of four priority buckets based on two dimensions:

Dimension 1 — Potential Tier:
  - High: Top 50% of potential_score
  - Low:  Bottom 50% of potential_score
  (Using median split rather than quartiles for this categorization because
   we want a simpler 2×2 matrix. The quartile analysis was already done in
   the SQL coverage query — this is a different analytical lens.)

Dimension 2 — Visit Responsiveness:
  - Responsive:     Post-visit Rx lift > 15%
  - Non-responsive: Post-visit Rx lift ≤ 15%
  (The 15% threshold is an industry benchmark for "meaningful" Rx lift.
   Below 15%, the observed change could be natural variation, seasonal
   effects, or market trends rather than a direct visit effect. This is
   conservative — some firms use 10%, but 15% provides higher confidence
   that the visit genuinely drove incremental Rx.)

The Four Priority Buckets:
┌──────────────────────────────┬──────────────────────────────┐
│  PRIORITY A                  │  PRIORITY B                  │
│  High potential, Responsive  │  High potential, Non-resp.   │
│  → Maximize visits           │  → Maintain, don't over-     │
│  (Best ROI per visit)        │    invest (visits don't help) │
├──────────────────────────────┼──────────────────────────────┤
│  PRIORITY C                  │  PRIORITY D                  │
│  Low potential, Responsive   │  Low potential, Non-resp.    │
│  → Visit occasionally        │  → Minimize visits           │
│  (Some ROI but limited       │  (Lowest ROI — every visit   │
│   upside)                    │    here is wasted effort)    │
└──────────────────────────────┴──────────────────────────────┘

Key Metric: "Wasted Effort" = % of total rep visit time spent on
Priority C and D HCPs. This is the headline number for the final
recommendation — it quantifies the reallocation opportunity.

Output:
  - data/processed/hcp_categorization.csv (per-HCP bucket assignment)
  - data/processed/visit_distribution_summary.csv (visit share by bucket)

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
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Responsiveness threshold: 15% post-visit Rx lift
# Analytical judgment: Industry standard for pharma SFE. A visit that produces
# less than 15% Rx lift is not clearly generating incremental prescriptions
# above natural variation. Lower thresholds (e.g., 10%) would include more
# HCPs as "responsive" but risk counting noise as signal.
RX_LIFT_THRESHOLD = 15.0  # percent

TOTAL_MONTHS = 18


# ============================================================================
# MAIN — Categorize HCPs and Compute Wasted Effort
# ============================================================================

def categorize_hcps():
    """
    Categorizes all HCPs into priority buckets and computes wasted effort.
    """
    # Load data
    hcps = pd.read_csv(os.path.join(RAW_DIR, 'hcps.csv'))
    visits = pd.read_csv(os.path.join(RAW_DIR, 'visit_logs.csv'))
    rx = pd.read_csv(os.path.join(RAW_DIR, 'rx_volume.csv'))
    visit_rx_lag = pd.read_csv(os.path.join(PROCESSED_DIR, 'visit_rx_lag.csv'))
    
    print(f"  Loaded: {len(hcps)} HCPs, {len(visits):,} visits, {len(rx):,} Rx records")
    print(f"  Visit-Rx lag data: {len(visit_rx_lag):,} rep-HCP pairs")
    
    # ------------------------------------------------------------------
    # Step 1: Determine potential tier (High vs Low)
    # ------------------------------------------------------------------
    potential_median = hcps['potential_score'].median()
    hcps['potential_tier'] = np.where(
        hcps['potential_score'] >= potential_median, 'High', 'Low'
    )
    
    print(f"\n  --- Potential Tier Assignment ---")
    print(f"  Median potential_score: {potential_median}")
    print(f"  High potential HCPs: {(hcps['potential_tier'] == 'High').sum()}")
    print(f"  Low potential HCPs:  {(hcps['potential_tier'] == 'Low').sum()}")
    
    # ------------------------------------------------------------------
    # Step 2: Determine visit responsiveness (Responsive vs Non-responsive)
    # ------------------------------------------------------------------
    # Use the visit_rx_lag data (from SQL Query 2) to get per-HCP Rx lift.
    # Multiple reps may visit the same HCP — we take the AVERAGE lift across
    # all reps who visit that HCP to get a single responsiveness measure.
    #
    # Why average across reps: An HCP's responsiveness is intrinsic to the HCP
    # (influenced by their loyalty tier), not to which rep visits them. Averaging
    # removes rep-specific noise.
    
    hcp_lift = visit_rx_lag.groupby('hcp_id').agg(
        avg_rx_lift_pct=('rx_lift_pct', 'mean')
    ).reset_index()
    
    # Handle HCPs with no visit data (they have no lift — treat as non-responsive)
    hcps = hcps.merge(hcp_lift, on='hcp_id', how='left')
    hcps['avg_rx_lift_pct'] = hcps['avg_rx_lift_pct'].fillna(0)
    
    hcps['responsiveness'] = np.where(
        hcps['avg_rx_lift_pct'] > RX_LIFT_THRESHOLD,
        'Responsive', 'Non-responsive'
    )
    
    print(f"\n  --- Responsiveness Assignment (threshold: {RX_LIFT_THRESHOLD}% lift) ---")
    print(f"  Responsive HCPs:     {(hcps['responsiveness'] == 'Responsive').sum()}")
    print(f"  Non-responsive HCPs: {(hcps['responsiveness'] == 'Non-responsive').sum()}")
    
    # Verify the loyalty-based pattern
    loyalty_resp = hcps.groupby('loyalty_tier')['responsiveness'].value_counts(normalize=True)
    print(f"\n  Responsiveness by loyalty tier (should confirm data patterns):")
    for loyalty in ['Brand_Loyal', 'Switcher', 'Competitor_Loyal']:
        resp_rate = hcps[
            (hcps['loyalty_tier'] == loyalty) & 
            (hcps['responsiveness'] == 'Responsive')
        ].shape[0] / hcps[hcps['loyalty_tier'] == loyalty].shape[0] * 100
        print(f"    {loyalty:20s}: {resp_rate:.1f}% responsive")
    
    # ------------------------------------------------------------------
    # Step 3: Assign priority bucket
    # ------------------------------------------------------------------
    def assign_bucket(row):
        if row['potential_tier'] == 'High' and row['responsiveness'] == 'Responsive':
            return 'Priority A'  # Maximize visits — best ROI
        elif row['potential_tier'] == 'High' and row['responsiveness'] == 'Non-responsive':
            return 'Priority B'  # Maintain, don't over-invest
        elif row['potential_tier'] == 'Low' and row['responsiveness'] == 'Responsive':
            return 'Priority C'  # Visit occasionally
        else:
            return 'Priority D'  # Minimize visits — lowest ROI
    
    hcps['priority_bucket'] = hcps.apply(assign_bucket, axis=1)
    
    print(f"\n  --- Priority Bucket Distribution ---")
    bucket_counts = hcps['priority_bucket'].value_counts().sort_index()
    for bucket, count in bucket_counts.items():
        pct = count / len(hcps) * 100
        print(f"    {bucket}: {count:>5} HCPs ({pct:.1f}%)")
    
    # ------------------------------------------------------------------
    # Step 4: Compute visit distribution across buckets
    # ------------------------------------------------------------------
    # Join visits to HCP priority buckets
    visit_hcp = visits.merge(
        hcps[['hcp_id', 'priority_bucket', 'potential_tier', 'responsiveness']],
        on='hcp_id', how='left'
    )
    
    total_visit_minutes = visit_hcp['visit_duration_minutes'].sum()
    
    bucket_visit_stats = visit_hcp.groupby('priority_bucket').agg(
        visit_count=('visit_id', 'count'),
        total_duration_minutes=('visit_duration_minutes', 'sum')
    ).reset_index()
    
    bucket_visit_stats['visit_share_pct'] = (
        bucket_visit_stats['visit_count'] / bucket_visit_stats['visit_count'].sum() * 100
    ).round(1)
    
    bucket_visit_stats['duration_share_pct'] = (
        bucket_visit_stats['total_duration_minutes'] / total_visit_minutes * 100
    ).round(1)
    
    print(f"\n  --- Current Visit Distribution by Priority Bucket ---")
    print(f"  {'Bucket':<15} {'Visits':>8} {'Visit %':>10} {'Time %':>10}")
    print(f"  {'-'*45}")
    for _, row in bucket_visit_stats.sort_values('priority_bucket').iterrows():
        print(f"  {row['priority_bucket']:<15} {row['visit_count']:>8,} {row['visit_share_pct']:>9.1f}% {row['duration_share_pct']:>9.1f}%")
    
    # ------------------------------------------------------------------
    # Step 5: Calculate "Wasted Effort" metric
    # ------------------------------------------------------------------
    # Wasted effort = % of visit time spent on Priority C and D HCPs
    # These are HCPs where visits generate minimal ROI (low potential and/or
    # non-responsive to visits)
    
    wasted_mask = bucket_visit_stats['priority_bucket'].isin(['Priority C', 'Priority D'])
    wasted_visit_pct = bucket_visit_stats.loc[wasted_mask, 'visit_share_pct'].sum()
    wasted_duration_pct = bucket_visit_stats.loc[wasted_mask, 'duration_share_pct'].sum()
    
    print(f"\n  ╔══════════════════════════════════════════════════╗")
    print(f"  ║  WASTED EFFORT METRIC                            ║")
    print(f"  ║  Visit share on Priority C+D: {wasted_visit_pct:.1f}%              ║")
    print(f"  ║  Time share on Priority C+D:  {wasted_duration_pct:.1f}%              ║")
    print(f"  ╚══════════════════════════════════════════════════╝")
    
    # ------------------------------------------------------------------
    # Step 6: Compute recommended visit distribution
    # ------------------------------------------------------------------
    # Recommended allocation based on priority logic:
    # - Priority A (High potential, Responsive): 50% of visits (maximize)
    # - Priority B (High potential, Non-responsive): 25% of visits (maintain)
    # - Priority C (Low potential, Responsive): 15% of visits (occasional)
    # - Priority D (Low potential, Non-responsive): 10% of visits (minimal)
    #
    # Analytical judgment: These are based on diminishing returns logic.
    # Priority A gets 50% because each visit drives the most incremental Rx.
    # Priority B still gets 25% because maintaining relationships with high-
    # potential HCPs is important even if visit-response is low (they may
    # switch loyalty over time). C and D get the remainder.
    
    recommended = {
        'Priority A': 50.0,
        'Priority B': 25.0,
        'Priority C': 15.0,
        'Priority D': 10.0
    }
    
    print(f"\n  --- Recommended vs Current Visit Distribution ---")
    print(f"  {'Bucket':<15} {'Current %':>12} {'Recommended %':>15} {'Delta':>10}")
    print(f"  {'-'*55}")
    for bucket in ['Priority A', 'Priority B', 'Priority C', 'Priority D']:
        current = bucket_visit_stats[
            bucket_visit_stats['priority_bucket'] == bucket
        ]['visit_share_pct'].values[0] if bucket in bucket_visit_stats['priority_bucket'].values else 0
        rec = recommended[bucket]
        delta = rec - current
        direction = '↑' if delta > 0 else '↓' if delta < 0 else '='
        print(f"  {bucket:<15} {current:>11.1f}% {rec:>14.1f}% {direction}{abs(delta):>8.1f}%")
    
    # ------------------------------------------------------------------
    # Step 7: Calculate Rx yield per visit by bucket (for waterfall chart)
    # ------------------------------------------------------------------
    # Join Rx data to visits to compute Rx yield per visit for each bucket
    # Total Rx per HCP
    hcp_total_rx = rx.groupby('hcp_id')['rx_count'].sum().reset_index()
    hcp_total_rx.columns = ['hcp_id', 'total_rx']
    
    hcp_with_rx = hcps.merge(hcp_total_rx, on='hcp_id', how='left')
    hcp_with_rx['total_rx'] = hcp_with_rx['total_rx'].fillna(0)
    
    # Total visits per HCP
    hcp_visits = visits.groupby('hcp_id').size().reset_index(name='total_visits')
    hcp_with_rx = hcp_with_rx.merge(hcp_visits, on='hcp_id', how='left')
    hcp_with_rx['total_visits'] = hcp_with_rx['total_visits'].fillna(0)
    
    # Rx yield per visit by bucket
    rx_yield = hcp_with_rx.groupby('priority_bucket').agg(
        total_rx=('total_rx', 'sum'),
        total_visits=('total_visits', 'sum')
    ).reset_index()
    rx_yield['rx_per_visit'] = (rx_yield['total_rx'] / rx_yield['total_visits']).round(2)
    
    print(f"\n  --- Rx Yield per Visit by Priority Bucket ---")
    for _, row in rx_yield.sort_values('priority_bucket').iterrows():
        print(f"    {row['priority_bucket']}: {row['rx_per_visit']:.2f} Rx per visit")
    
    # ------------------------------------------------------------------
    # Save outputs
    # ------------------------------------------------------------------
    
    # HCP categorization (full detail)
    output_cols = [
        'hcp_id', 'hcp_name', 'city_id', 'specialty', 'loyalty_tier',
        'potential_score', 'potential_tier', 'avg_rx_lift_pct',
        'responsiveness', 'priority_bucket'
    ]
    hcps[output_cols].to_csv(
        os.path.join(PROCESSED_DIR, 'hcp_categorization.csv'), index=False
    )
    
    # Visit distribution summary (for waterfall chart in Component 6)
    visit_dist = pd.DataFrame({
        'priority_bucket': ['Priority A', 'Priority B', 'Priority C', 'Priority D'],
        'current_visit_share_pct': [
            bucket_visit_stats[bucket_visit_stats['priority_bucket'] == b]['visit_share_pct'].values[0]
            if b in bucket_visit_stats['priority_bucket'].values else 0
            for b in ['Priority A', 'Priority B', 'Priority C', 'Priority D']
        ],
        'recommended_visit_share_pct': [recommended[b] for b in ['Priority A', 'Priority B', 'Priority C', 'Priority D']],
        'rx_per_visit': [
            rx_yield[rx_yield['priority_bucket'] == b]['rx_per_visit'].values[0]
            if b in rx_yield['priority_bucket'].values else 0
            for b in ['Priority A', 'Priority B', 'Priority C', 'Priority D']
        ]
    })
    visit_dist['wasted_effort_flag'] = visit_dist['priority_bucket'].isin(['Priority C', 'Priority D'])
    visit_dist.to_csv(
        os.path.join(PROCESSED_DIR, 'visit_distribution_summary.csv'), index=False
    )
    
    return hcps, visit_dist, wasted_visit_pct


# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("NovaMed SFE — Component 4: HCP Categorization & Wasted Effort")
    print("=" * 70)
    print(f"  Responsiveness threshold: {RX_LIFT_THRESHOLD}% post-visit Rx lift")
    print()
    
    hcps_df, visit_dist_df, wasted_pct = categorize_hcps()
    
    # Cross-tabulation: Loyalty tier × Priority bucket
    print(f"\n--- Cross-tab: Loyalty Tier × Priority Bucket ---")
    cross = pd.crosstab(hcps_df['loyalty_tier'], hcps_df['priority_bucket'], margins=True)
    print(cross.to_string())
    
    # Identify the most "wasted" rep-HCP pairings
    print(f"\n  Saved: data/processed/hcp_categorization.csv ({len(hcps_df)} rows)")
    print(f"  Saved: data/processed/visit_distribution_summary.csv")
    print(f"\n  Visit distribution summary:")
    print(visit_dist_df.to_string(index=False))
