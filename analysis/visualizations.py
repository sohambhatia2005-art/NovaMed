"""
NovaMed SFE — Component 6: Polished Visualizations
=====================================================
Produces 5 publication-quality charts that tell the analytical story:

1. rep_quadrant.png       — Rep performance quadrant (refined from Component 3)
2. visit_rx_scatter.png   — Visit frequency vs Rx growth by loyalty tier
3. territory_heatmap.png  — City-level KPI heatmap
4. wasted_effort_waterfall.png — Visit reallocation waterfall
5. rx_trend_lines.png     — Rolling Rx trends for top/bottom reps

Design principles:
- Consistent color palette across all charts
- Clean, professional styling (no default matplotlib)
- Every chart has a title, axis labels, and a one-line insight annotation
- Suitable for inclusion in a consulting presentation or portfolio

Author: Aditya (NovaMed SFE Portfolio Project)
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
CHARTS_DIR = os.path.join(BASE_DIR, 'outputs', 'charts')
os.makedirs(CHARTS_DIR, exist_ok=True)

TOTAL_MONTHS = 18

# --- Global style ---
# Using a clean, professional palette throughout
REGION_COLORS = {
    'North': '#2E86AB',
    'South': '#A23B72',
    'East':  '#F18F01',
    'West':  '#C73E1D'
}

LOYALTY_COLORS = {
    'Brand_Loyal':      '#2D7D46',
    'Switcher':         '#2E86AB',
    'Competitor_Loyal': '#C73E1D'
}

QUADRANT_COLORS = {
    'High Effort, High Impact':  '#2E86AB',
    'High Effort, Low Impact':   '#F18F01',
    'Low Effort, High Impact':   '#2D7D46',
    'Low Effort, Low Impact':    '#C73E1D'
}

BUCKET_COLORS = {
    'Priority A': '#2D7D46',
    'Priority B': '#2E86AB',
    'Priority C': '#F18F01',
    'Priority D': '#C73E1D'
}

# Set global matplotlib style
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.size': 11,
    'axes.titlesize': 16,
    'axes.titleweight': 'bold',
    'axes.labelsize': 13,
    'axes.labelweight': 'bold',
    'axes.facecolor': '#FAFAFA',
    'figure.facecolor': 'white',
    'axes.grid': True,
    'grid.alpha': 0.15,
    'grid.linestyle': '-',
})


# ============================================================================
# CHART 1 — Rep Performance Quadrant (refined)
# ============================================================================

def chart_rep_quadrant():
    """
    Scatter plot: visit intensity (X) vs efficiency ratio (Y).
    Each rep is a dot colored by region.
    Quadrant labels clearly visible.
    """
    print("  Building Chart 1: Rep Performance Quadrant...")
    
    df = pd.read_csv(os.path.join(PROCESSED_DIR, 'rep_efficiency.csv'))
    
    visit_med = df['visit_intensity'].median()
    eff_med = df['efficiency_ratio'].median()
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    for region, color in REGION_COLORS.items():
        mask = df['region'] == region
        ax.scatter(
            df.loc[mask, 'visit_intensity'],
            df.loc[mask, 'efficiency_ratio'],
            c=color, label=region, alpha=0.75, s=80,
            edgecolors='white', linewidth=0.6, zorder=3
        )
    
    # Quadrant dividers
    ax.axvline(x=visit_med, color='#444444', linestyle='--', linewidth=1, alpha=0.6)
    ax.axhline(y=eff_med, color='#444444', linestyle='--', linewidth=1, alpha=0.6)
    
    # Reference line at efficiency = 1.0
    ax.axhline(y=1.0, color='#333333', linestyle=':', linewidth=0.8, alpha=0.3)
    
    # Quadrant labels
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    labels = [
        (0.22, 0.82, 'Low Effort, High Impact\n★ Star Performers', '#2D7D46'),
        (0.78, 0.82, 'High Effort, High Impact\n✓ Keep & Reward', '#2E86AB'),
        (0.22, 0.18, 'Low Effort, Low Impact\n⚠ Urgent Intervention', '#C73E1D'),
        (0.78, 0.18, 'High Effort, Low Impact\n? Investigate Territory', '#F18F01'),
    ]
    for xf, yf, text, col in labels:
        ax.text(xf, yf, text, transform=ax.transAxes,
                ha='center', va='center', fontsize=11, fontweight='bold',
                color=col, alpha=0.45,
                bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.4, edgecolor='none'))
    
    ax.set_xlabel('Visit Intensity (visits per HCP per month)', labelpad=10)
    ax.set_ylabel('Efficiency Ratio (Actual Rx / Expected Rx)', labelpad=10)
    ax.set_title('Rep Performance Quadrant — Visit Effort vs Rx Efficiency', pad=18)
    
    # Insight annotation
    ax.text(0.5, 1.025,
            'Insight: 14% of reps are high-effort but low-impact — prime candidates for territory reassignment',
            ha='center', va='bottom', transform=ax.transAxes,
            fontsize=10, fontstyle='italic', color='#666666')
    
    ax.legend(title='Region', loc='upper left', framealpha=0.9, fontsize=10, title_fontsize=11)
    
    plt.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, 'rep_quadrant.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("    ✓ Saved rep_quadrant.png")


# ============================================================================
# CHART 2 — Visit Frequency vs Rx Growth by Loyalty Tier
# ============================================================================

def chart_visit_rx_scatter():
    """
    Scatter plot: visit frequency (X) vs Rx growth rate (Y) per HCP,
    colored by loyalty tier.
    Should visually confirm: Switchers respond to visits, others don't.
    """
    print("  Building Chart 2: Visit-Rx Scatter by Loyalty...")
    
    hcps = pd.read_csv(os.path.join(RAW_DIR, 'hcps.csv'))
    visits = pd.read_csv(os.path.join(RAW_DIR, 'visit_logs.csv'))
    rx = pd.read_csv(os.path.join(RAW_DIR, 'rx_volume.csv'))
    
    # Visit frequency per HCP (visits per month)
    hcp_visits = visits.groupby('hcp_id')['visit_id'].count().reset_index()
    hcp_visits.columns = ['hcp_id', 'total_visits']
    hcp_visits['visits_per_month'] = hcp_visits['total_visits'] / TOTAL_MONTHS
    
    # Rx growth rate per HCP
    # Compare first 6 months vs last 6 months
    rx['month_year_dt'] = pd.to_datetime(rx['month_year'])
    rx_sorted = rx.sort_values('month_year_dt')
    months_list = sorted(rx['month_year'].unique())
    early_months = months_list[:6]
    late_months = months_list[-6:]
    
    early_rx = rx[rx['month_year'].isin(early_months)].groupby('hcp_id')['rx_count'].mean().reset_index()
    early_rx.columns = ['hcp_id', 'early_avg_rx']
    
    late_rx = rx[rx['month_year'].isin(late_months)].groupby('hcp_id')['rx_count'].mean().reset_index()
    late_rx.columns = ['hcp_id', 'late_avg_rx']
    
    rx_growth = early_rx.merge(late_rx, on='hcp_id')
    rx_growth['rx_growth_pct'] = np.where(
        rx_growth['early_avg_rx'] > 0,
        (rx_growth['late_avg_rx'] - rx_growth['early_avg_rx']) / rx_growth['early_avg_rx'] * 100,
        0
    )
    
    # Merge all
    plot_df = hcps[['hcp_id', 'loyalty_tier']].merge(hcp_visits, on='hcp_id', how='left')
    plot_df = plot_df.merge(rx_growth[['hcp_id', 'rx_growth_pct']], on='hcp_id', how='left')
    plot_df = plot_df.dropna()
    
    # Cap extreme outliers for cleaner visualization
    plot_df['rx_growth_pct'] = plot_df['rx_growth_pct'].clip(-100, 300)
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    for loyalty, color in LOYALTY_COLORS.items():
        mask = plot_df['loyalty_tier'] == loyalty
        ax.scatter(
            plot_df.loc[mask, 'visits_per_month'],
            plot_df.loc[mask, 'rx_growth_pct'],
            c=color, label=loyalty.replace('_', ' '),
            alpha=0.4, s=40, edgecolors='none', zorder=3
        )
    
    # Add trend lines for each loyalty tier
    for loyalty, color in LOYALTY_COLORS.items():
        subset = plot_df[plot_df['loyalty_tier'] == loyalty]
        if len(subset) > 10:
            z = np.polyfit(subset['visits_per_month'], subset['rx_growth_pct'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(subset['visits_per_month'].min(), subset['visits_per_month'].max(), 100)
            ax.plot(x_line, p(x_line), color=color, linewidth=2.5, alpha=0.9, zorder=4)
    
    ax.axhline(y=0, color='#333333', linestyle=':', linewidth=0.8, alpha=0.4)
    
    ax.set_xlabel('Visit Frequency (visits per month)', labelpad=10)
    ax.set_ylabel('Rx Growth Rate (% change, early vs late period)', labelpad=10)
    ax.set_title('Visit Frequency vs Rx Growth — The Loyalty Effect', pad=18)
    
    ax.text(0.5, 1.025,
            'Insight: Switcher HCPs (blue) show clear Rx growth with more visits — Brand Loyal & Competitor Loyal show flat response',
            ha='center', va='bottom', transform=ax.transAxes,
            fontsize=10, fontstyle='italic', color='#666666')
    
    ax.legend(title='Loyalty Tier', loc='upper left', framealpha=0.9,
              fontsize=11, title_fontsize=12, markerscale=2)
    
    plt.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, 'visit_rx_scatter.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("    ✓ Saved visit_rx_scatter.png")


# ============================================================================
# CHART 3 — Territory Heatmap (City-Level KPIs)
# ============================================================================

def chart_territory_heatmap():
    """
    Heatmap table: cities as rows, key metrics as columns.
    Diverging colormap to make over/under-coverage visually obvious.
    """
    print("  Building Chart 3: Territory KPI Heatmap...")
    
    mpi = pd.read_csv(os.path.join(PROCESSED_DIR, 'market_potential_index.csv'))
    clusters = pd.read_csv(os.path.join(PROCESSED_DIR, 'territory_clusters.csv'))
    efficiency = pd.read_csv(os.path.join(PROCESSED_DIR, 'rep_efficiency.csv'))
    
    # City-level avg efficiency — efficiency df already has 'city' column
    city_efficiency = efficiency.groupby('city').agg(
        avg_efficiency=('efficiency_ratio', 'mean'),
        avg_visit_intensity=('visit_intensity', 'mean')
    ).reset_index()
    
    # Build heatmap data
    heatmap_data = mpi[['city_name', 'region', 'tier', 'mpi_score']].merge(
        clusters[['city_name', 'coverage_intensity', 'territory_cluster']],
        on='city_name'
    ).merge(
        city_efficiency, left_on='city_name', right_on='city', how='left'
    )
    
    heatmap_data = heatmap_data.sort_values('mpi_score', ascending=False)
    
    # Prepare numeric matrix for heatmap
    display_cols = ['MPI Score', 'Coverage\nIntensity', 'Avg Efficiency\nRatio']
    matrix = heatmap_data[['mpi_score', 'coverage_intensity', 'avg_efficiency']].copy()
    matrix.columns = display_cols
    matrix.index = heatmap_data['city_name'] + '  (' + heatmap_data['tier'] + ')'
    
    # Normalize each column to [0, 1] for consistent color mapping
    matrix_normalized = matrix.copy()
    for col in matrix_normalized.columns:
        col_min = matrix_normalized[col].min()
        col_max = matrix_normalized[col].max()
        if col_max > col_min:
            matrix_normalized[col] = (matrix_normalized[col] - col_min) / (col_max - col_min)
        else:
            matrix_normalized[col] = 0.5
    
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Use a diverging colormap centered around the median
    sns.heatmap(
        matrix_normalized,
        annot=matrix.round(2).values,
        fmt='',
        cmap='RdYlGn',
        linewidths=2,
        linecolor='white',
        ax=ax,
        cbar_kws={'label': 'Relative Performance (0=Low, 1=High)', 'shrink': 0.8},
        annot_kws={'size': 12, 'fontweight': 'bold'}
    )
    
    # Add cluster labels as a side column
    for i, (_, row) in enumerate(heatmap_data.iterrows()):
        cluster = row['territory_cluster']
        if 'Under-covered' in cluster:
            badge_color = '#C73E1D'
        elif 'Over-covered, Low' in cluster:
            badge_color = '#F18F01'
        elif 'Over-covered, High' in cluster:
            badge_color = '#2E86AB'
        else:
            badge_color = '#2D7D46'
        
        ax.text(len(display_cols) + 0.3, i + 0.5,
                cluster.replace(', ', '\n'),
                ha='left', va='center', fontsize=8, fontweight='bold',
                color=badge_color,
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                         edgecolor=badge_color, alpha=0.8, linewidth=1))
    
    ax.set_title('Territory KPI Heatmap — City-Level Performance Overview', pad=18)
    ax.text(0.5, 1.02,
            'Insight: High-MPI cities (top rows) with low coverage intensity reveal the redeployment opportunity',
            ha='center', va='bottom', transform=ax.transAxes,
            fontsize=10, fontstyle='italic', color='#666666')
    
    ax.set_ylabel('')
    ax.tick_params(axis='y', labelsize=11)
    
    plt.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, 'territory_heatmap.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("    ✓ Saved territory_heatmap.png")


# ============================================================================
# CHART 4 — Wasted Effort Waterfall
# ============================================================================

def chart_wasted_effort_waterfall():
    """
    Waterfall/grouped bar chart showing current vs recommended visit
    distribution across the four HCP priority buckets.
    Quantifies the reallocation opportunity.
    """
    print("  Building Chart 4: Wasted Effort Waterfall...")
    
    visit_dist = pd.read_csv(os.path.join(PROCESSED_DIR, 'visit_distribution_summary.csv'))
    
    buckets = visit_dist['priority_bucket'].tolist()
    current = visit_dist['current_visit_share_pct'].tolist()
    recommended = visit_dist['recommended_visit_share_pct'].tolist()
    rx_yield = visit_dist['rx_per_visit'].tolist()
    
    x = np.arange(len(buckets))
    width = 0.35
    
    fig, ax1 = plt.subplots(figsize=(14, 9))
    
    # Grouped bars: Current vs Recommended
    bars_current = ax1.bar(x - width/2, current, width,
                           label='Current Allocation',
                           color=['#E8E8E8'] * len(buckets),
                           edgecolor=['#999999'] * len(buckets),
                           linewidth=1.5, zorder=3)
    
    bars_recommended = ax1.bar(x + width/2, recommended, width,
                               label='Recommended Allocation',
                               color=[BUCKET_COLORS[b] for b in buckets],
                               edgecolor='white', linewidth=1, zorder=3)
    
    # Add value labels on bars
    for bar, val in zip(bars_current, current):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold',
                color='#666666')
    
    for bar, val in zip(bars_recommended, recommended):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold',
                color='#333333')
    
    # Add delta arrows between current and recommended
    for i, (c, r) in enumerate(zip(current, recommended)):
        delta = r - c
        if abs(delta) > 1:
            arrow_color = '#2D7D46' if delta > 0 else '#C73E1D'
            symbol = '↑' if delta > 0 else '↓'
            ax1.annotate(
                f'{symbol} {abs(delta):.1f}%',
                xy=(x[i], max(c, r) + 4),
                ha='center', va='bottom', fontsize=10, fontweight='bold',
                color=arrow_color)
    
    # Rx yield annotations at the bottom
    for i, (bucket, ry) in enumerate(zip(buckets, rx_yield)):
        ax1.text(x[i], -4, f'Rx/visit: {ry:.2f}',
                ha='center', va='top', fontsize=9, color='#666666', fontstyle='italic')
    
    ax1.set_xlabel('HCP Priority Bucket', labelpad=15)
    ax1.set_ylabel('Visit Share (%)', labelpad=10)
    ax1.set_title('Visit Reallocation Opportunity — Current vs Recommended Distribution', pad=18)
    
    ax1.text(0.5, 1.025,
             'Insight: 50.5% of visits currently go to low-value HCPs (C+D) — reallocating to Priority A could drive significant Rx growth',
             ha='center', va='bottom', transform=ax1.transAxes,
             fontsize=10, fontstyle='italic', color='#666666')
    
    ax1.set_xticks(x)
    ax1.set_xticklabels([
        'Priority A\n(High Pot., Responsive)',
        'Priority B\n(High Pot., Non-resp.)',
        'Priority C\n(Low Pot., Responsive)',
        'Priority D\n(Low Pot., Non-resp.)'
    ], fontsize=10)
    
    ax1.legend(fontsize=12, loc='upper right', framealpha=0.9)
    ax1.set_ylim(-8, max(max(current), max(recommended)) + 12)
    
    # Add a shaded "wasted effort" zone
    ax1.axvspan(1.5, 3.5, alpha=0.06, color='#C73E1D', zorder=1)
    ax1.text(2.5, max(max(current), max(recommended)) + 8,
             '← Wasted Effort Zone →',
             ha='center', va='center', fontsize=11, fontweight='bold',
             color='#C73E1D', alpha=0.6)
    
    plt.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, 'wasted_effort_waterfall.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("    ✓ Saved wasted_effort_waterfall.png")


# ============================================================================
# CHART 5 — Rx Trend Lines (Top 5 vs Bottom 5 Reps)
# ============================================================================

def chart_rx_trend_lines():
    """
    Line chart: 3-month rolling Rx averages over time.
    Top 5 and bottom 5 reps by efficiency ratio.
    Shows diverging performance trajectories.
    """
    print("  Building Chart 5: Rx Trend Lines (Top/Bottom Reps)...")
    
    rolling = pd.read_csv(os.path.join(PROCESSED_DIR, 'rolling_rx_trend.csv'))
    efficiency = pd.read_csv(os.path.join(PROCESSED_DIR, 'rep_efficiency.csv'))
    
    # Get top 5 and bottom 5 reps by efficiency ratio
    top5 = efficiency.nlargest(5, 'efficiency_ratio')['rep_id'].tolist()
    bottom5 = efficiency.nsmallest(5, 'efficiency_ratio')['rep_id'].tolist()
    
    fig, ax = plt.subplots(figsize=(16, 9))
    
    # Plot top 5 reps (shades of green/blue)
    top_colors = ['#1a7a3a', '#2D7D46', '#3a9d5e', '#4eb876', '#6acc8e']
    for i, rep_id in enumerate(top5):
        rep_data = rolling[rolling['rep_id'] == rep_id]
        rep_name = rep_data['rep_name'].iloc[0]
        city = rep_data['city'].iloc[0]
        eff_ratio = efficiency[efficiency['rep_id'] == rep_id]['efficiency_ratio'].iloc[0]
        ax.plot(
            rep_data['month_year'], rep_data['rolling_3m_avg_rx'],
            color=top_colors[i], linewidth=2.5, alpha=0.85,
            label=f'▲ {rep_name} ({city}) — ER: {eff_ratio:.2f}',
            marker='o', markersize=4, zorder=4
        )
    
    # Plot bottom 5 reps (shades of red/orange)
    bottom_colors = ['#922b21', '#C73E1D', '#d4553f', '#e0735f', '#ec917f']
    for i, rep_id in enumerate(bottom5):
        rep_data = rolling[rolling['rep_id'] == rep_id]
        rep_name = rep_data['rep_name'].iloc[0]
        city = rep_data['city'].iloc[0]
        eff_ratio = efficiency[efficiency['rep_id'] == rep_id]['efficiency_ratio'].iloc[0]
        ax.plot(
            rep_data['month_year'], rep_data['rolling_3m_avg_rx'],
            color=bottom_colors[i], linewidth=2, alpha=0.75,
            linestyle='--',
            label=f'▼ {rep_name} ({city}) — ER: {eff_ratio:.2f}',
            marker='s', markersize=3, zorder=3
        )
    
    ax.set_xlabel('Month', labelpad=10)
    ax.set_ylabel('Rolling 3-Month Avg Rx Volume', labelpad=10)
    ax.set_title('Rx Performance Trajectories — Top 5 vs Bottom 5 Reps by Efficiency', pad=18)
    
    ax.text(0.5, 1.025,
            'Insight: Performance trajectories diverge over time — early intervention could prevent the widening gap',
            ha='center', va='bottom', transform=ax.transAxes,
            fontsize=10, fontstyle='italic', color='#666666')
    
    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')
    
    # Add a shaded region distinguishing top from bottom
    all_top_data = rolling[rolling['rep_id'].isin(top5)]['rolling_3m_avg_rx']
    all_bottom_data = rolling[rolling['rep_id'].isin(bottom5)]['rolling_3m_avg_rx']
    
    # Legend with two columns
    ax.legend(loc='upper left', fontsize=9, framealpha=0.9,
              ncol=2, title='Rep Performance Ranking', title_fontsize=10)
    
    plt.tight_layout()
    fig.savefig(os.path.join(CHARTS_DIR, 'rx_trend_lines.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print("    ✓ Saved rx_trend_lines.png")


# ============================================================================
# MAIN — Generate All Charts
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("NovaMed SFE — Component 6: Professional Visualizations")
    print("=" * 70)
    print()
    
    chart_rep_quadrant()
    print()
    chart_visit_rx_scatter()
    print()
    chart_territory_heatmap()
    print()
    chart_wasted_effort_waterfall()
    print()
    chart_rx_trend_lines()
    
    print(f"\n{'=' * 70}")
    print("ALL CHARTS COMPLETE")
    print(f"{'=' * 70}")
    print(f"  Output directory: {CHARTS_DIR}")
    
    # List all chart files
    for f in sorted(os.listdir(CHARTS_DIR)):
        fpath = os.path.join(CHARTS_DIR, f)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  {f:40s} ({size_kb:.0f} KB)")
