"""
NovaMed SFE — Component 2: Market Potential Index (MPI)
========================================================
Builds a territory-level Market Potential Index (0-100) for each of the
15 cities based on three normalized sub-scores:

1. Specialist Density Score (40% weight)
   - specialist_count / population_millions
   - WHY 40%: Specialist density is the strongest direct predictor of
     prescribing potential. More cardiologists and diabetologists per capita
     means more potential prescribers for CardioMax / GlucoShield.

2. Disease Prevalence Score (40% weight)
   - Directly from disease_prevalence_index (0-100)
   - WHY 40%: High disease prevalence = larger patient pool = more Rx
     opportunities. This is equally important as specialist density because
     even with many specialists, without patients there's no demand.

3. Market Accessibility Score (20% weight)
   - Inverse of a competition proxy based on city tier
   - Tier1 cities have MORE competitors but also more infrastructure;
     net accessibility is moderate. Tier3 cities have fewer competitors
     but also less infrastructure.
   - WHY 20%: This is a modifier, not a primary demand driver. Competition
     reduces the SHARE NovaMed can capture, but doesn't eliminate opportunity.
     It's weighted lower because the MPI should reflect total market potential,
     not just NovaMed's capture-ability.

Normalization: Min-max scaling to [0, 1] for each sub-score before weighting.
This ensures all three sub-scores contribute on the same scale regardless of
their original value ranges.

Output: data/processed/market_potential_index.csv

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

# Sub-score weights (must sum to 1.0)
W_SPECIALIST_DENSITY = 0.40
W_DISEASE_PREVALENCE = 0.40
W_MARKET_ACCESSIBILITY = 0.20

assert abs(W_SPECIALIST_DENSITY + W_DISEASE_PREVALENCE + W_MARKET_ACCESSIBILITY - 1.0) < 1e-6, \
    "Weights must sum to 1.0"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def min_max_normalize(series):
    """
    Min-max normalization to [0, 1] range.
    
    Why min-max over z-score: 
    - Produces bounded [0, 1] values that are directly interpretable
    - When we multiply by 100 at the end, scores have a natural 0-100 meaning
    - Z-scores could produce negative values and have no natural upper bound,
      making them harder to explain to business stakeholders
    """
    return (series - series.min()) / (series.max() - series.min())


# ============================================================================
# MAIN — Compute Market Potential Index
# ============================================================================

def compute_mpi():
    """
    Computes the MPI for all 15 cities and returns the result DataFrame.
    """
    # Load cities data
    cities = pd.read_csv(os.path.join(RAW_DIR, 'cities.csv'))
    
    print(f"  Loaded {len(cities)} cities")
    print(f"  Columns: {list(cities.columns)}")
    
    # -----------------------------------------------------------------------
    # Sub-score 1: Specialist Density Score
    # -----------------------------------------------------------------------
    # Specialists per million population — measures how concentrated
    # the prescriber base is relative to city size
    cities['specialist_density'] = cities['specialist_count'] / cities['population_millions']
    cities['specialist_density_score'] = min_max_normalize(cities['specialist_density'])
    
    print(f"\n  --- Specialist Density ---")
    print(f"  Range: {cities['specialist_density'].min():.1f} to {cities['specialist_density'].max():.1f} per million")
    print(f"  Highest: {cities.loc[cities['specialist_density'].idxmax(), 'city_name']} "
          f"({cities['specialist_density'].max():.1f})")
    print(f"  Lowest:  {cities.loc[cities['specialist_density'].idxmin(), 'city_name']} "
          f"({cities['specialist_density'].min():.1f})")
    
    # -----------------------------------------------------------------------
    # Sub-score 2: Disease Prevalence Score
    # -----------------------------------------------------------------------
    # Direct from disease_prevalence_index, normalized to [0,1]
    cities['prevalence_score'] = min_max_normalize(cities['disease_prevalence_index'])
    
    print(f"\n  --- Disease Prevalence ---")
    print(f"  Range: {cities['disease_prevalence_index'].min()} to {cities['disease_prevalence_index'].max()}")
    print(f"  Highest: {cities.loc[cities['disease_prevalence_index'].idxmax(), 'city_name']} "
          f"({cities['disease_prevalence_index'].max()})")
    
    # -----------------------------------------------------------------------
    # Sub-score 3: Market Accessibility Score
    # -----------------------------------------------------------------------
    # Competition proxy by tier:
    #   Tier1 = 0.8 (high competition, many incumbent pharma companies)
    #   Tier2 = 0.5 (moderate competition)
    #   Tier3 = 0.3 (lower competition, but also less organized market)
    #
    # Accessibility = 1 - competition_proxy (inverse relationship)
    # Higher accessibility means easier to grow market share
    #
    # Analytical judgment: Tier1 competition is set high (0.8) because
    # metros like Mumbai/Delhi have 10+ competing pharma companies.
    # Tier3 cities have fewer competitors (0.3) but also less developed
    # distribution and physician engagement infrastructure.
    
    competition_proxy = {'Tier1': 0.8, 'Tier2': 0.5, 'Tier3': 0.3}
    cities['competition_level'] = cities['tier'].map(competition_proxy)
    cities['accessibility_raw'] = 1 - cities['competition_level']
    cities['accessibility_score'] = min_max_normalize(cities['accessibility_raw'])
    
    print(f"\n  --- Market Accessibility ---")
    print(f"  Competition proxy: {competition_proxy}")
    print(f"  Tier1 accessibility: {1 - 0.8:.1f} (low — high competition)")
    print(f"  Tier3 accessibility: {1 - 0.3:.1f} (high — low competition)")
    
    # -----------------------------------------------------------------------
    # Composite MPI Score (0-100)
    # -----------------------------------------------------------------------
    cities['mpi_raw'] = (
        W_SPECIALIST_DENSITY * cities['specialist_density_score'] +
        W_DISEASE_PREVALENCE * cities['prevalence_score'] +
        W_MARKET_ACCESSIBILITY * cities['accessibility_score']
    )
    
    # Scale to 0-100 for interpretability
    # Re-normalize the composite to ensure full 0-100 range utilization
    cities['mpi_score'] = (min_max_normalize(cities['mpi_raw']) * 100).round(1)
    
    # -----------------------------------------------------------------------
    # Output preparation
    # -----------------------------------------------------------------------
    output_cols = [
        'city_id', 'city_name', 'region', 'tier',
        'population_millions', 'specialist_count', 'disease_prevalence_index',
        'specialist_density', 'specialist_density_score',
        'prevalence_score', 'accessibility_score',
        'mpi_score'
    ]
    
    result = cities[output_cols].sort_values('mpi_score', ascending=False).reset_index(drop=True)
    
    # Save
    output_path = os.path.join(PROCESSED_DIR, 'market_potential_index.csv')
    result.to_csv(output_path, index=False)
    
    return result


# ============================================================================
# EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("NovaMed SFE — Component 2: Market Potential Index")
    print("=" * 70)
    print(f"  Weights: Specialist Density = {W_SPECIALIST_DENSITY:.0%}, "
          f"Disease Prevalence = {W_DISEASE_PREVALENCE:.0%}, "
          f"Market Accessibility = {W_MARKET_ACCESSIBILITY:.0%}")
    print()
    
    result = compute_mpi()
    
    print(f"\n{'=' * 70}")
    print("MPI RESULTS — All 15 Cities (Ranked)")
    print(f"{'=' * 70}")
    
    # Display clean summary
    display_cols = ['city_name', 'region', 'tier', 'specialist_density',
                    'specialist_density_score', 'prevalence_score',
                    'accessibility_score', 'mpi_score']
    print(result[display_cols].to_string(index=False))
    
    # Key insights
    print(f"\n--- Key Insights ---")
    
    top_3 = result.head(3)
    bottom_3 = result.tail(3)
    
    print(f"\n  Top 3 MPI cities:")
    for _, row in top_3.iterrows():
        print(f"    {row['city_name']:15s} ({row['tier']}, {row['region']:5s}) — MPI: {row['mpi_score']}")
    
    print(f"\n  Bottom 3 MPI cities:")
    for _, row in bottom_3.iterrows():
        print(f"    {row['city_name']:15s} ({row['tier']}, {row['region']:5s}) — MPI: {row['mpi_score']}")
    
    # Flag the territory misalignment — high MPI cities with few reps
    reps = pd.read_csv(os.path.join(RAW_DIR, 'reps.csv'))
    reps_per_city = reps.groupby('city').size().reset_index(name='num_reps')
    merged = result.merge(reps_per_city, left_on='city_name', right_on='city', how='left')
    merged['reps_per_mpi_point'] = (merged['num_reps'] / merged['mpi_score']).round(3)
    
    print(f"\n  --- Territory Alignment Check: Reps per MPI point ---")
    print(f"  (Lower = under-resourced relative to potential)")
    alignment = merged[['city_name', 'tier', 'mpi_score', 'num_reps', 'reps_per_mpi_point']].sort_values('reps_per_mpi_point')
    print(alignment.to_string(index=False))
    
    print(f"\n  Saved to: data/processed/market_potential_index.csv")
