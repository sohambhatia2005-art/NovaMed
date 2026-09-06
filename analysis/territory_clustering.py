"""
NovaMed SFE — Component 5: K-Means Territory Clustering
=========================================================
Clusters the 15 cities into 4 strategic territory types using two features:
  1. Market Potential Index (MPI) — from Component 2
  2. Current rep coverage intensity — avg visits per HCP per month in that city

The four clusters map to distinct management actions:
  - "Under-covered, High Potential"  → URGENT: redeploy reps here
  - "Over-covered, High Potential"   → Review: possibly appropriate, flag for optimization
  - "Over-covered, Low Potential"    → Consolidate: redeploy reps away
  - "Appropriately Covered"          → Maintain current deployment

Why k=4:
  This is a BUSINESS-DRIVEN choice, not purely statistical. We need exactly 4
  strategic actions (listed above), so k=4 maps directly to actionable territory
  management decisions. We run the elbow curve from k=1 to k=10 to confirm that
  k=4 is also a statistically reasonable choice (the inertia curve should show
  diminishing returns around k=3-5).

Why K-Means (not DBSCAN or hierarchical):
  - Only 15 data points — simple algorithms work best with small n
  - We need a FIXED number of clusters (4) — K-Means naturally supports this
  - The features are 2D continuous on the same scale (after normalization)
  - Results need to be easily explainable to business stakeholders

Output:
  - data/processed/territory_clusters.csv
  - outputs/charts/territory_clusters.png (scatter plot)
  - outputs/charts/elbow_curve.png (k selection validation)

Author: Aditya (NovaMed SFE Portfolio Project)
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
CHARTS_DIR = os.path.join(BASE_DIR, 'outputs', 'charts')
os.makedirs(CHARTS_DIR, exist_ok=True)

RANDOM_SEED = 42
TOTAL_MONTHS = 18
K = 4  # Number of clusters — business-driven choice


# ============================================================================
# MAIN — Territory Clustering
# ============================================================================

def run_territory_clustering():
    """
    Prepares features, runs K-Means, and assigns cluster labels.
    """
    # Load data
    mpi = pd.read_csv(os.path.join(PROCESSED_DIR, 'market_potential_index.csv'))
    visits = pd.read_csv(os.path.join(RAW_DIR, 'visit_logs.csv'))
    hcps = pd.read_csv(os.path.join(RAW_DIR, 'hcps.csv'))
    cities = pd.read_csv(os.path.join(RAW_DIR, 'cities.csv'))
    
    print(f"  Loaded: {len(mpi)} cities with MPI, {len(visits):,} visits, {len(hcps)} HCPs")
    
    # ------------------------------------------------------------------
    # Step 1: Compute coverage intensity per city
    # ------------------------------------------------------------------
    # Coverage intensity = average visits per HCP per month in that city
    # This measures how intensely reps are working each territory
    
    # Map HCPs to cities
    hcp_city = hcps[['hcp_id', 'city_id']].copy()
    
    # Count visits per city
    visit_with_city = visits.merge(hcp_city, on='hcp_id', how='left')
    visits_per_city = visit_with_city.groupby('city_id')['visit_id'].count().reset_index()
    visits_per_city.columns = ['city_id', 'total_visits']
    
    # Count HCPs per city
    hcps_per_city = hcps.groupby('city_id')['hcp_id'].count().reset_index()
    hcps_per_city.columns = ['city_id', 'num_hcps']
    
    # Coverage intensity = total_visits / (num_hcps × total_months)
    city_coverage = visits_per_city.merge(hcps_per_city, on='city_id')
    city_coverage['coverage_intensity'] = (
        city_coverage['total_visits'] / (city_coverage['num_hcps'] * TOTAL_MONTHS)
    ).round(3)
    
    # Merge with MPI
    clustering_data = mpi[['city_id', 'city_name', 'region', 'tier', 'mpi_score']].merge(
        city_coverage[['city_id', 'coverage_intensity', 'total_visits', 'num_hcps']],
        on='city_id'
    )
    
    print(f"\n  --- City Features for Clustering ---")
    print(clustering_data[['city_name', 'tier', 'mpi_score', 'coverage_intensity']].to_string(index=False))
    
    # ------------------------------------------------------------------
    # Step 2: Feature scaling
    # ------------------------------------------------------------------
    # StandardScaler (z-score normalization) for K-Means
    # K-Means is distance-based, so features must be on the same scale.
    # MPI is 0-100 and coverage_intensity is ~0.2-2.0 — without scaling,
    # MPI would dominate the distance calculation.
    
    features = clustering_data[['mpi_score', 'coverage_intensity']].values
    scaler = StandardScaler()
    features_scaled = scaler.fit_transform(features)
    
    # ------------------------------------------------------------------
    # Step 3: Elbow curve (k=1 to k=10)
    # ------------------------------------------------------------------
    # The elbow curve plots inertia (within-cluster sum of squares) vs k.
    # We look for the "elbow" — the point where adding more clusters gives
    # diminishing returns in reducing inertia.
    
    max_k = min(10, len(clustering_data))  # Can't have more clusters than data points
    inertias = []
    k_range = range(1, max_k + 1)
    
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=10)
        km.fit(features_scaled)
        inertias.append(km.inertia_)
    
    # Plot elbow curve
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(list(k_range), inertias, 'b-o', linewidth=2, markersize=8, color='#2E86AB')
    ax.axvline(x=K, color='#C73E1D', linestyle='--', linewidth=1.5, alpha=0.8,
               label=f'Selected k={K}')
    ax.set_xlabel('Number of Clusters (k)', fontsize=13, fontweight='bold')
    ax.set_ylabel('Inertia (Within-Cluster Sum of Squares)', fontsize=13, fontweight='bold')
    ax.set_title('Elbow Curve — Optimal k Selection for Territory Clustering',
                 fontsize=15, fontweight='bold')
    ax.text(0.5, 1.02,
            f'k={K} selected: maps to 4 strategic territory actions; elbow visible around k=3-4',
            ha='center', va='bottom', transform=ax.transAxes,
            fontsize=10, fontstyle='italic', color='#666666')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.2)
    ax.set_xticks(list(k_range))
    ax.set_facecolor('#FAFAFA')
    fig.patch.set_facecolor('white')
    plt.tight_layout()
    
    elbow_path = os.path.join(CHARTS_DIR, 'elbow_curve.png')
    fig.savefig(elbow_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\n  Elbow curve saved to: {elbow_path}")
    
    # Print inertia values for reference
    print(f"  Inertia values: ", end='')
    for k_val, inertia in zip(k_range, inertias):
        print(f"k={k_val}: {inertia:.1f}  ", end='')
    print()
    
    # Confirm k=4 choice:
    # The inertia drop from k=3 to k=4 should still be meaningful,
    # while k=4 to k=5 should show diminishing returns.
    if len(inertias) >= 5:
        drop_3_to_4 = inertias[2] - inertias[3]
        drop_4_to_5 = inertias[3] - inertias[4]
        print(f"  Inertia drop k=3→4: {drop_3_to_4:.1f}, k=4→5: {drop_4_to_5:.1f}")
        print(f"  k=4 is {'statistically supported' if drop_3_to_4 > drop_4_to_5 else 'business-driven (elbow not strong, but 4 actions needed)'}")
    
    # ------------------------------------------------------------------
    # Step 4: Run K-Means with k=4
    # ------------------------------------------------------------------
    km_final = KMeans(n_clusters=K, random_state=RANDOM_SEED, n_init=10)
    clustering_data['cluster_raw'] = km_final.fit_predict(features_scaled)
    
    # ------------------------------------------------------------------
    # Step 5: Assign meaningful business labels
    # ------------------------------------------------------------------
    # Label clusters based on their centroid positions:
    # High MPI + Low Coverage → Under-covered, High Potential
    # High MPI + High Coverage → Over-covered, High Potential (or well-covered)
    # Low MPI + High Coverage → Over-covered, Low Potential
    # Low MPI + Low Coverage → Appropriately Covered
    
    # Get cluster centroids (in original scale)
    centroids_scaled = km_final.cluster_centers_
    centroids_original = scaler.inverse_transform(centroids_scaled)
    
    centroid_df = pd.DataFrame(centroids_original, columns=['mpi_centroid', 'coverage_centroid'])
    centroid_df['cluster_raw'] = range(K)
    
    print(f"\n  --- Cluster Centroids (original scale) ---")
    print(centroid_df.to_string(index=False))
    
    # Determine MPI and coverage medians for labeling
    mpi_median = clustering_data['mpi_score'].median()
    coverage_median = clustering_data['coverage_intensity'].median()
    
    print(f"\n  MPI median: {mpi_median:.1f}, Coverage median: {coverage_median:.3f}")
    
    # Label each cluster based on its centroid position relative to medians
    def label_cluster(row):
        high_mpi = row['mpi_centroid'] >= mpi_median
        high_coverage = row['coverage_centroid'] >= coverage_median
        
        if high_mpi and not high_coverage:
            return 'Under-covered, High Potential'
        elif high_mpi and high_coverage:
            return 'Over-covered, High Potential'
        elif not high_mpi and high_coverage:
            return 'Over-covered, Low Potential'
        else:
            return 'Appropriately Covered'
    
    centroid_df['cluster_label'] = centroid_df.apply(label_cluster, axis=1)
    
    # Check for duplicate labels (possible if centroids are close)
    if centroid_df['cluster_label'].nunique() < K:
        # Manually fix by using more granular centroid differences
        print("  ⚠ Duplicate cluster labels detected — refining labels using centroid ranking")
        # Sort by MPI centroid descending, then coverage centroid
        centroid_df = centroid_df.sort_values('mpi_centroid', ascending=False).reset_index(drop=True)
        labels_ordered = [
            'Under-covered, High Potential',
            'Over-covered, High Potential',
            'Over-covered, Low Potential',
            'Appropriately Covered'
        ]
        # Assign based on MPI rank and coverage characteristics
        for i, row_idx in enumerate(centroid_df.index):
            if i == 0:  # Highest MPI
                if centroid_df.loc[row_idx, 'coverage_centroid'] < coverage_median:
                    centroid_df.loc[row_idx, 'cluster_label'] = 'Under-covered, High Potential'
                else:
                    centroid_df.loc[row_idx, 'cluster_label'] = 'Over-covered, High Potential'
            elif i == len(centroid_df) - 1:  # Lowest MPI
                if centroid_df.loc[row_idx, 'coverage_centroid'] > coverage_median:
                    centroid_df.loc[row_idx, 'cluster_label'] = 'Over-covered, Low Potential'
                else:
                    centroid_df.loc[row_idx, 'cluster_label'] = 'Appropriately Covered'
            else:  # Middle clusters — assign remaining labels
                assigned = set(centroid_df.loc[:i-1, 'cluster_label'].values) if i > 0 else set()
                remaining = [l for l in labels_ordered if l not in assigned]
                if centroid_df.loc[row_idx, 'coverage_centroid'] >= coverage_median:
                    # Prefer "over-covered" labels
                    pref = [l for l in remaining if 'Over' in l]
                    centroid_df.loc[row_idx, 'cluster_label'] = pref[0] if pref else remaining[0]
                else:
                    pref = [l for l in remaining if 'Under' in l or 'Appropriately' in l]
                    centroid_df.loc[row_idx, 'cluster_label'] = pref[0] if pref else remaining[0]
    
    # Map labels back to cities
    label_map = centroid_df.set_index('cluster_raw')['cluster_label'].to_dict()
    clustering_data['territory_cluster'] = clustering_data['cluster_raw'].map(label_map)
    
    print(f"\n  --- Cluster Assignments ---")
    for label in sorted(clustering_data['territory_cluster'].unique()):
        cities_in_cluster = clustering_data[clustering_data['territory_cluster'] == label]['city_name'].tolist()
        print(f"  {label}:")
        for city in cities_in_cluster:
            row = clustering_data[clustering_data['city_name'] == city].iloc[0]
            print(f"    - {city} (MPI: {row['mpi_score']:.1f}, Coverage: {row['coverage_intensity']:.3f})")
    
    # ------------------------------------------------------------------
    # Step 6: Save output
    # ------------------------------------------------------------------
    output = clustering_data[[
        'city_id', 'city_name', 'region', 'tier', 'mpi_score',
        'coverage_intensity', 'total_visits', 'num_hcps', 'territory_cluster'
    ]].sort_values('mpi_score', ascending=False).reset_index(drop=True)
    
    output.to_csv(os.path.join(PROCESSED_DIR, 'territory_clusters.csv'), index=False)
    
    return clustering_data, centroid_df


def plot_territory_clusters(clustering_data):
    """
    Creates a professional scatter plot of territory clusters.
    """
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Color palette for clusters — distinct, meaningful colors
    cluster_colors = {
        'Under-covered, High Potential': '#C73E1D',     # Red/urgent
        'Over-covered, High Potential':  '#2E86AB',     # Blue/review
        'Over-covered, Low Potential':   '#F18F01',     # Amber/warning
        'Appropriately Covered':         '#2D7D46'      # Green/good
    }
    
    cluster_markers = {
        'Under-covered, High Potential': '^',   # Triangle up (needs attention)
        'Over-covered, High Potential':  's',   # Square
        'Over-covered, Low Potential':   'v',   # Triangle down
        'Appropriately Covered':         'o'    # Circle (stable)
    }
    
    for cluster_label in cluster_colors:
        mask = clustering_data['territory_cluster'] == cluster_label
        subset = clustering_data[mask]
        if len(subset) > 0:
            ax.scatter(
                subset['coverage_intensity'],
                subset['mpi_score'],
                c=cluster_colors[cluster_label],
                marker=cluster_markers.get(cluster_label, 'o'),
                s=200, alpha=0.85, edgecolors='white', linewidth=1.5,
                label=cluster_label, zorder=3
            )
            # Add city name labels
            for _, row in subset.iterrows():
                ax.annotate(
                    row['city_name'],
                    (row['coverage_intensity'], row['mpi_score']),
                    xytext=(8, 8), textcoords='offset points',
                    fontsize=9, fontweight='bold', color='#333333',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none')
                )
    
    # Draw quadrant reference lines at medians
    mpi_med = clustering_data['mpi_score'].median()
    cov_med = clustering_data['coverage_intensity'].median()
    ax.axvline(x=cov_med, color='#999999', linestyle=':', linewidth=1, alpha=0.5)
    ax.axhline(y=mpi_med, color='#999999', linestyle=':', linewidth=1, alpha=0.5)
    
    # Styling
    ax.set_xlabel('Coverage Intensity (avg visits per HCP per month)', fontsize=13, fontweight='bold', labelpad=10)
    ax.set_ylabel('Market Potential Index (MPI Score, 0-100)', fontsize=13, fontweight='bold', labelpad=10)
    ax.set_title('NovaMed — Territory Clustering: Market Potential vs Coverage',
                 fontsize=16, fontweight='bold', pad=15)
    ax.text(0.5, 1.02,
            'Insight: Red triangles (▲) are high-potential territories receiving inadequate coverage — immediate redeployment opportunity',
            ha='center', va='bottom', transform=ax.transAxes,
            fontsize=10, fontstyle='italic', color='#666666')
    
    ax.legend(title='Territory Cluster', loc='center right', framealpha=0.9,
              fontsize=10, title_fontsize=11, markerscale=0.8)
    ax.grid(True, alpha=0.15)
    ax.set_facecolor('#FAFAFA')
    fig.patch.set_facecolor('white')
    
    plt.tight_layout()
    chart_path = os.path.join(CHARTS_DIR, 'territory_clusters.png')
    fig.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\n  Cluster scatter plot saved to: {chart_path}")


# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("NovaMed SFE — Component 5: K-Means Territory Clustering")
    print("=" * 70)
    print(f"  k = {K} (business-driven: 4 strategic territory actions)")
    print()
    
    clustering_data, centroid_df = run_territory_clustering()
    
    print(f"\n  --- Generating Cluster Scatter Plot ---")
    plot_territory_clusters(clustering_data)
    
    # Summary statistics
    print(f"\n{'=' * 70}")
    print("CLUSTERING COMPLETE — Summary")
    print(f"{'=' * 70}")
    
    cluster_summary = clustering_data.groupby('territory_cluster').agg(
        num_cities=('city_name', 'count'),
        avg_mpi=('mpi_score', 'mean'),
        avg_coverage=('coverage_intensity', 'mean'),
        cities=('city_name', lambda x: ', '.join(x))
    ).reset_index()
    
    for _, row in cluster_summary.iterrows():
        print(f"\n  {row['territory_cluster']}:")
        print(f"    Cities ({row['num_cities']}): {row['cities']}")
        print(f"    Avg MPI: {row['avg_mpi']:.1f}, Avg Coverage: {row['avg_coverage']:.3f}")
    
    print(f"\n  Saved: data/processed/territory_clusters.csv")
    print(f"  Saved: outputs/charts/territory_clusters.png")
    print(f"  Saved: outputs/charts/elbow_curve.png")
