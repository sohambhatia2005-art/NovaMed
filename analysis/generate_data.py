"""
NovaMed SFE — Synthetic Data Generator
=======================================
Generates 5 interconnected datasets with realistic, non-trivial business patterns:

1. reps.csv        — 120 field sales reps across 15 Indian cities
2. cities.csv      — 15 cities with demographic and market characteristics
3. hcps.csv        — 2,000 healthcare professionals
4. visit_logs.csv  — ~80,000-100,000 visit records over 18 months
5. rx_volume.csv   — Monthly Rx counts per HCP per drug

Embedded Patterns:
- 3-4 reps over-covering low-potential territories (high visits, low Rx yield)
- 2-3 high-potential territories under-covered
- Loyalty-based Rx response (Brand_Loyal=steady, Switcher=visit-responsive, Competitor_Loyal=flat)
- Tier 1 cities have higher baseline Rx but more competition
- Some reps show high visit counts but low conversion (effort ≠ impact)

Author: Aditya (NovaMed SFE Portfolio Project)
"""

import os
import numpy as np
import pandas as pd
from faker import Faker

# ============================================================================
# CONFIGURATION
# ============================================================================

# Fixed seed for full reproducibility across all components
RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)
fake = Faker('en_IN')
Faker.seed(RANDOM_SEED)

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

# Date range: 18 months of data (Jul 2023 – Dec 2024)
START_DATE = pd.Timestamp('2023-07-01')
END_DATE = pd.Timestamp('2024-12-31')
MONTHS = pd.date_range(START_DATE, END_DATE, freq='MS')  # 18 month-starts

# ============================================================================
# 1. CITIES TABLE — 15 Indian cities with market characteristics
# ============================================================================

def generate_cities():
    """
    Creates 15 cities across 4 regions with realistic tier assignments.
    
    Design decisions:
    - Tier 1 = metros with high specialist density but also high competition
    - Tier 2 = emerging pharma markets with moderate density
    - Tier 3 = smaller cities with lower density but untapped potential in some cases
    - disease_prevalence_index is intentionally varied so some Tier 2/3 cities
      have HIGH prevalence (creating the misalignment opportunity for the analysis)
    """
    cities_data = [
        # city_id, city_name, region, tier, population_millions, specialist_count, disease_prevalence_index
        # --- NORTH ---
        (1,  'Delhi',       'North', 'Tier1', 19.0,  320, 72),
        (2,  'Lucknow',     'North', 'Tier2',  3.5,   85, 68),
        (3,  'Jaipur',      'North', 'Tier2',  3.1,   78, 55),
        (4,  'Chandigarh',  'North', 'Tier3',  1.1,   42, 48),
        # --- SOUTH ---
        (5,  'Bangalore',   'South', 'Tier1', 12.3,  290, 65),
        (6,  'Chennai',     'South', 'Tier1',  8.9,  240, 70),
        (7,  'Hyderabad',   'South', 'Tier2',  7.7,  185, 62),
        (8,  'Kochi',       'South', 'Tier3',  2.1,   55, 58),
        # --- EAST ---
        (9,  'Kolkata',     'East',  'Tier1', 14.9,  260, 75),
        (10, 'Patna',       'East',  'Tier2',  2.0,   60, 78),  # High prevalence, under-served
        (11, 'Bhubaneswar', 'East',  'Tier3',  0.9,   35, 70),  # High prevalence, under-served
        # --- WEST ---
        (12, 'Mumbai',      'West',  'Tier1', 20.7,  350, 68),
        (13, 'Pune',        'West',  'Tier2',  6.8,  155, 60),
        (14, 'Ahmedabad',   'West',  'Tier2',  5.6,  130, 64),
        (15, 'Indore',      'West',  'Tier3',  1.9,   45, 72),  # High prevalence, under-served
    ]
    
    cols = ['city_id', 'city_name', 'region', 'tier', 'population_millions',
            'specialist_count', 'disease_prevalence_index']
    df = pd.DataFrame(cities_data, columns=cols)
    df.to_csv(os.path.join(RAW_DIR, 'cities.csv'), index=False)
    print(f"✓ cities.csv — {len(df)} rows")
    return df


# ============================================================================
# 2. REPS TABLE — 120 field sales reps
# ============================================================================

def generate_reps(cities_df):
    """
    Creates 120 reps distributed across cities with intentional misalignment:
    
    Key patterns embedded:
    - Tier 1 cities get ~10 reps each (appropriate for market size)
    - Tier 2 cities get ~6-8 reps each
    - Tier 3 cities: Chandigarh gets 6 reps (OVER-deployed for its potential)
    - Patna, Bhubaneswar, Indore — high-prevalence Tier 3/2 cities — get only 3-4 reps
      each (UNDER-deployed relative to potential), creating the territory gap
    - Drug focus split ~50/50 but varies by city specialty mix
    """
    
    # Rep allocation per city — intentionally misaligned
    # Format: city_id -> (num_reps, cardiomax_share)
    # cardiomax_share = fraction of reps focused on CardioMax vs GlucoShield
    city_rep_allocation = {
        1:  (12, 0.50),  # Delhi — large market, balanced allocation
        2:  (7,  0.43),  # Lucknow
        3:  (7,  0.57),  # Jaipur
        4:  (6,  0.50),  # Chandigarh — OVER-DEPLOYED (small Tier3, 6 reps)
        5:  (11, 0.55),  # Bangalore
        6:  (10, 0.50),  # Chennai
        7:  (9,  0.44),  # Hyderabad
        8:  (5,  0.40),  # Kochi
        9:  (11, 0.45),  # Kolkata
        10: (4,  0.50),  # Patna — UNDER-DEPLOYED (high prevalence, only 4 reps)
        11: (3,  0.33),  # Bhubaneswar — UNDER-DEPLOYED (high prevalence, only 3 reps)
        12: (13, 0.46),  # Mumbai — large market
        13: (8,  0.50),  # Pune
        14: (7,  0.57),  # Ahmedabad
        15: (4,  0.50),  # Indore — UNDER-DEPLOYED (high prevalence, only 4 reps)
    }
    
    # Verify total = 120 - this catches allocation bugs early
    # (Sum should be: 12+7+7+6+11+10+9+5+11+4+3+13+8+7+4 = 117)
    # Adjust: add 1 rep each to Lucknow, Patna, Kochi to reach 120
    city_rep_allocation[2] = (8, 0.43)   # Lucknow +1
    city_rep_allocation[10] = (4, 0.50)  # Keep Patna at 4 (under-deployed)
    city_rep_allocation[8] = (6, 0.40)   # Kochi +1
    # Now: 12+8+7+6+11+10+9+6+11+4+3+13+8+7+4 = 119. Add 1 more to Indore.
    city_rep_allocation[15] = (4, 0.50)  # Keep Indore at 4
    # 119. Add 1 to Bhubaneswar to make it slightly less dire but still under-deployed
    city_rep_allocation[11] = (4, 0.50)  # Bhubaneswar +1 → now 120 total
    
    total_check = sum(v[0] for v in city_rep_allocation.values())
    assert total_check == 120, f"Rep count mismatch: {total_check} != 120"
    
    reps = []
    rep_id = 1
    city_lookup = cities_df.set_index('city_id')
    
    for city_id, (num_reps, cardio_share) in city_rep_allocation.items():
        city_row = city_lookup.loc[city_id]
        num_cardio = round(num_reps * cardio_share)
        
        for i in range(num_reps):
            drug_focus = 'CardioMax' if i < num_cardio else 'GlucoShield'
            
            # Tenure: 1-15 years, with slight skew toward mid-career
            tenure = int(np.clip(np.random.normal(6, 3), 1, 15))
            
            reps.append({
                'rep_id': rep_id,
                'rep_name': fake.name(),
                'region': city_row['region'],
                'city': city_row['city_name'],
                'drug_focus': drug_focus,
                'tenure_years': tenure
            })
            rep_id += 1
    
    df = pd.DataFrame(reps)
    df.to_csv(os.path.join(RAW_DIR, 'reps.csv'), index=False)
    print(f"✓ reps.csv — {len(df)} rows")
    return df


# ============================================================================
# 3. HCPS TABLE — 2,000 healthcare professionals
# ============================================================================

def generate_hcps(cities_df):
    """
    Creates 2,000 HCPs distributed across cities proportional to specialist_count.
    
    Key patterns:
    - Specialty mix: ~30% Cardiologists, ~35% Diabetologists, ~35% GPs
    - Loyalty distribution: 25% Brand_Loyal, 45% Switcher, 30% Competitor_Loyal
    - potential_score: Tier1 cities have higher mean but wider spread;
      some Tier2/3 HCPs have very high potential (the untapped opportunity)
    - Brand_Loyal HCPs tend to have higher potential_scores (they're established)
    """
    
    total_specialists = cities_df['specialist_count'].sum()
    
    hcps = []
    hcp_id = 1
    
    for _, city in cities_df.iterrows():
        # Number of HCPs proportional to specialist_count, scaled to total ~2000
        n_hcps = max(10, round(2000 * city['specialist_count'] / total_specialists))
        
        for _ in range(n_hcps):
            # Specialty assignment
            specialty_roll = np.random.random()
            if specialty_roll < 0.30:
                specialty = 'Cardiologist'
            elif specialty_roll < 0.65:
                specialty = 'Diabetologist'
            else:
                specialty = 'GP'
            
            # Loyalty tier — distribution varies slightly by tier
            # Tier1 cities have more Competitor_Loyal (more competition)
            if city['tier'] == 'Tier1':
                loyalty_probs = [0.20, 0.40, 0.40]  # Brand_Loyal, Switcher, Competitor_Loyal
            elif city['tier'] == 'Tier2':
                loyalty_probs = [0.25, 0.50, 0.25]
            else:  # Tier3
                loyalty_probs = [0.30, 0.50, 0.20]
            
            loyalty = np.random.choice(
                ['Brand_Loyal', 'Switcher', 'Competitor_Loyal'],
                p=loyalty_probs
            )
            
            # Potential score: higher baseline in Tier1, but with variance
            # Some Tier2/3 HCPs intentionally have high scores (untapped opportunity)
            tier_baseline = {'Tier1': 60, 'Tier2': 50, 'Tier3': 40}
            base = tier_baseline[city['tier']]
            
            # Brand_Loyal HCPs tend to be established with higher potential
            loyalty_bonus = {'Brand_Loyal': 10, 'Switcher': 0, 'Competitor_Loyal': 5}
            
            potential_score = int(np.clip(
                np.random.normal(base + loyalty_bonus[loyalty], 15),
                5, 100
            ))
            
            hcps.append({
                'hcp_id': hcp_id,
                'hcp_name': fake.name(),
                'city_id': city['city_id'],
                'specialty': specialty,
                'loyalty_tier': loyalty,
                'potential_score': potential_score
            })
            hcp_id += 1
    
    df = pd.DataFrame(hcps)
    
    # Trim or pad to exactly 2000
    if len(df) > 2000:
        df = df.sample(n=2000, random_state=RANDOM_SEED).reset_index(drop=True)
        df['hcp_id'] = range(1, 2001)
    elif len(df) < 2000:
        # Pad by adding more HCPs to the largest cities
        shortfall = 2000 - len(df)
        extra_city_ids = np.random.choice(
            cities_df[cities_df['tier'] == 'Tier1']['city_id'].values,
            size=shortfall
        )
        for cid in extra_city_ids:
            city = cities_df[cities_df['city_id'] == cid].iloc[0]
            hcp_id = df['hcp_id'].max() + 1
            specialty = np.random.choice(['Cardiologist', 'Diabetologist', 'GP'])
            loyalty = np.random.choice(['Brand_Loyal', 'Switcher', 'Competitor_Loyal'],
                                       p=[0.20, 0.40, 0.40])
            potential_score = int(np.clip(np.random.normal(60, 15), 5, 100))
            df = pd.concat([df, pd.DataFrame([{
                'hcp_id': hcp_id, 'hcp_name': fake.name(), 'city_id': cid,
                'specialty': specialty, 'loyalty_tier': loyalty,
                'potential_score': potential_score
            }])], ignore_index=True)
    
    df.to_csv(os.path.join(RAW_DIR, 'hcps.csv'), index=False)
    print(f"✓ hcps.csv — {len(df)} rows")
    return df


# ============================================================================
# 4. VISIT LOGS TABLE — ~80,000-100,000 visit records over 18 months
# ============================================================================

def generate_visit_logs(reps_df, hcps_df, cities_df):
    """
    Generates visit logs with realistic patterns:
    
    Visit frequency drivers:
    - Each rep visits ~40-60 HCPs per month (industry standard: 8-12 calls/day, 20 days/month)
    - Reps primarily visit HCPs in their assigned city
    - Drug promoted matches rep's drug_focus (with occasional cross-promotion)
    
    Embedded patterns for specific reps:
    - "Wasteful" reps (IDs 19-24 in Chandigarh): very high visit counts to low-potential HCPs
    - Under-covered territories (Patna, Bhubaneswar, Indore): fewer total visits despite high need
    - Visit duration: 15-45 min, with experienced reps having slightly longer visits (relationship depth)
    """
    
    # Create city_id lookup for reps
    city_name_to_id = cities_df.set_index('city_name')['city_id'].to_dict()
    reps_df = reps_df.copy()
    reps_df['city_id'] = reps_df['city'].map(city_name_to_id)
    
    # Pre-compute HCPs per city for quick lookup
    hcps_by_city = hcps_df.groupby('city_id')['hcp_id'].apply(list).to_dict()
    hcp_potential = hcps_df.set_index('hcp_id')['potential_score'].to_dict()
    
    # Identify "wasteful" reps — those in Chandigarh (over-deployed Tier3)
    chandigarh_rep_ids = reps_df[reps_df['city'] == 'Chandigarh']['rep_id'].tolist()
    
    # Reps flagged for "high effort, low impact" pattern (picked from various cities)
    # These reps will visit a LOT but target low-potential HCPs
    high_effort_low_impact_reps = set(chandigarh_rep_ids[:4])  # 4 Chandigarh reps
    
    visits = []
    visit_id = 1
    business_days = pd.bdate_range(START_DATE, END_DATE)
    
    for _, rep in reps_df.iterrows():
        rep_city_id = rep['city_id']
        available_hcps = hcps_by_city.get(rep_city_id, [])
        
        if not available_hcps:
            continue
        
        is_wasteful = rep['rep_id'] in high_effort_low_impact_reps
        
        # Monthly visit count varies by rep type
        if is_wasteful:
            # Wasteful reps: very high visit counts (60-80/month)
            monthly_visits_mean = 70
        else:
            # Normal reps: 40-55 visits/month depending on tenure
            monthly_visits_mean = 40 + min(rep['tenure_years'], 10) * 1.5
        
        for month_start in MONTHS:
            month_end = month_start + pd.offsets.MonthEnd(0)
            month_bdays = business_days[(business_days >= month_start) & (business_days <= month_end)]
            
            # Slight monsoon dip (Jul-Sep) — reps travel less
            month_num = month_start.month
            if month_num in [7, 8, 9]:
                seasonal_factor = 0.85
            elif month_num in [12, 1]:
                seasonal_factor = 0.90  # Holiday season dip
            else:
                seasonal_factor = 1.0
            
            n_visits = max(10, int(np.random.poisson(monthly_visits_mean * seasonal_factor)))
            
            # Select which HCPs to visit this month
            if is_wasteful:
                # Wasteful reps disproportionately visit LOW-potential HCPs
                # This creates the "high effort, low impact" signal
                hcp_potentials = np.array([hcp_potential.get(h, 50) for h in available_hcps])
                # Inverse potential weighting — more likely to visit low-potential HCPs
                weights = (110 - hcp_potentials).astype(float)
                weights = weights / weights.sum()
                visited_hcps = np.random.choice(available_hcps, size=n_visits, replace=True, p=weights)
            else:
                # Normal reps visit a mix, slightly favoring higher-potential HCPs
                hcp_potentials = np.array([hcp_potential.get(h, 50) for h in available_hcps])
                weights = hcp_potentials.astype(float) ** 0.5  # Mild potential-seeking
                weights = weights / weights.sum()
                visited_hcps = np.random.choice(available_hcps, size=n_visits, replace=True, p=weights)
            
            for hcp_id in visited_hcps:
                visit_date = np.random.choice(month_bdays)
                
                # Drug promoted: usually matches rep's focus, 10% cross-promotion
                if np.random.random() < 0.90:
                    drug = rep['drug_focus']
                else:
                    drug = 'GlucoShield' if rep['drug_focus'] == 'CardioMax' else 'CardioMax'
                
                # Visit duration: 15-45 min
                # Experienced reps have slightly longer visits (deeper relationships)
                base_duration = 20 + min(rep['tenure_years'], 10)
                duration = int(np.clip(np.random.normal(base_duration, 7), 10, 60))
                
                visits.append({
                    'visit_id': visit_id,
                    'rep_id': rep['rep_id'],
                    'hcp_id': int(hcp_id),
                    'visit_date': pd.Timestamp(visit_date).strftime('%Y-%m-%d'),
                    'drug_promoted': drug,
                    'visit_duration_minutes': duration
                })
                visit_id += 1
    
    df = pd.DataFrame(visits)
    df.to_csv(os.path.join(RAW_DIR, 'visit_logs.csv'), index=False)
    print(f"✓ visit_logs.csv — {len(df)} rows")
    return df


# ============================================================================
# 5. RX VOLUME TABLE — Monthly Rx counts per HCP per drug
# ============================================================================

def generate_rx_volume(hcps_df, visit_logs_df, cities_df):
    """
    Generates monthly Rx volumes with the most critical embedded patterns:
    
    Rx response model (the core analytical insight):
    - Brand_Loyal HCPs: Stable Rx ~proportional to potential_score, NOT visit-driven
      (These HCPs already prescribe NovaMed drugs; visits don't change behavior much)
    - Switcher HCPs: Rx IS positively correlated with monthly visit count
      (These are the reps' real targets for incremental Rx growth)
    - Competitor_Loyal HCPs: Low Rx regardless of visit count
      (These HCPs are unlikely to switch; visiting them is largely wasted effort)
    
    Additional patterns:
    - Tier1 cities: Higher absolute Rx volume (larger patient base)
    - Slight upward trend over time (market growth)
    - Monsoon dip in Rx volumes (patients visit doctors less)
    """
    
    # Pre-compute visit counts per HCP per month
    visit_logs_df = visit_logs_df.copy()
    visit_logs_df['visit_date'] = pd.to_datetime(visit_logs_df['visit_date'])
    visit_logs_df['month_year'] = visit_logs_df['visit_date'].dt.to_period('M')
    
    monthly_visits = visit_logs_df.groupby(
        ['hcp_id', 'month_year']
    ).size().reset_index(name='visit_count')
    monthly_visit_dict = {}
    for _, row in monthly_visits.iterrows():
        monthly_visit_dict[(row['hcp_id'], str(row['month_year']))] = row['visit_count']
    
    # City tier lookup
    hcp_city = hcps_df.set_index('hcp_id')['city_id'].to_dict()
    city_tier = cities_df.set_index('city_id')['tier'].to_dict()
    
    rx_records = []
    rx_id = 1
    
    drugs = ['CardioMax', 'GlucoShield']
    
    for _, hcp in hcps_df.iterrows():
        hcp_id = hcp['hcp_id']
        loyalty = hcp['loyalty_tier']
        potential = hcp['potential_score']
        specialty = hcp['specialty']
        tier = city_tier.get(hcp_city.get(hcp_id, 1), 'Tier2')
        
        # Tier multiplier for absolute Rx volume
        tier_mult = {'Tier1': 1.3, 'Tier2': 1.0, 'Tier3': 0.8}[tier]
        
        # Specialty-drug affinity
        # Cardiologists: prescribe more CardioMax; Diabetologists: more GlucoShield; GPs: balanced
        drug_affinity = {
            'Cardiologist': {'CardioMax': 1.4, 'GlucoShield': 0.7},
            'Diabetologist': {'CardioMax': 0.7, 'GlucoShield': 1.4},
            'GP': {'CardioMax': 1.0, 'GlucoShield': 1.0}
        }
        
        for drug in drugs:
            affinity = drug_affinity[specialty][drug]
            
            for month in MONTHS:
                month_str = str(month.to_period('M'))
                visits_this_month = monthly_visit_dict.get((hcp_id, month_str), 0)
                
                # --- CORE RX RESPONSE MODEL ---
                
                # Base Rx from potential score (scaled, 0-100 potential → 0-20 base Rx)
                base_rx = (potential / 100) * 15 * tier_mult * affinity
                
                if loyalty == 'Brand_Loyal':
                    # Stable prescribers: Rx = base + small noise, NOT visit driven
                    # They're already loyal — visits maintain relationship but don't drive incremental Rx
                    visit_effect = visits_this_month * 0.1  # Minimal visit effect
                    rx = base_rx + visit_effect + np.random.normal(0, 1.5)
                    
                elif loyalty == 'Switcher':
                    # VISIT-RESPONSIVE: This is where rep effort creates real impact
                    # Each visit drives ~0.8-1.2 incremental Rx (the core insight)
                    visit_effect = visits_this_month * np.random.uniform(0.8, 1.2)
                    rx = (base_rx * 0.5) + visit_effect + np.random.normal(0, 2)
                    
                elif loyalty == 'Competitor_Loyal':
                    # Low Rx regardless — these HCPs prefer competitor drugs
                    # Visit effect is negligible (0.05 per visit — essentially noise)
                    visit_effect = visits_this_month * 0.05
                    rx = (base_rx * 0.2) + visit_effect + np.random.normal(0, 1)
                
                # Time trend: ~1% monthly growth (market expansion)
                month_idx = list(MONTHS).index(month)
                time_growth = 1 + (month_idx * 0.008)
                
                # Seasonal dip (monsoon: Jul-Sep → patients visit doctors less → fewer Rx)
                month_num = month.month
                if month_num in [7, 8, 9]:
                    seasonal = 0.88
                elif month_num in [12, 1]:
                    seasonal = 0.93
                else:
                    seasonal = 1.0
                
                final_rx = max(0, int(round(rx * time_growth * seasonal)))
                
                rx_records.append({
                    'rx_id': rx_id,
                    'hcp_id': hcp_id,
                    'drug_name': drug,
                    'month_year': month_str,
                    'rx_count': final_rx
                })
                rx_id += 1
    
    df = pd.DataFrame(rx_records)
    df.to_csv(os.path.join(RAW_DIR, 'rx_volume.csv'), index=False)
    print(f"✓ rx_volume.csv — {len(df)} rows")
    return df


# ============================================================================
# MAIN — Generate all datasets
# ============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("NovaMed SFE — Generating Synthetic Datasets")
    print("=" * 60)
    print(f"Random seed: {RANDOM_SEED}")
    print(f"Date range: {START_DATE.date()} to {END_DATE.date()} ({len(MONTHS)} months)")
    print(f"Output directory: {RAW_DIR}")
    print()
    
    # Generate in dependency order
    print("--- Generating Cities ---")
    cities_df = generate_cities()
    print()
    
    print("--- Generating Reps ---")
    reps_df = generate_reps(cities_df)
    print()
    
    print("--- Generating HCPs ---")
    hcps_df = generate_hcps(cities_df)
    print()
    
    print("--- Generating Visit Logs (this may take a minute...) ---")
    visit_logs_df = generate_visit_logs(reps_df, hcps_df, cities_df)
    print()
    
    print("--- Generating Rx Volume (this may take a few minutes...) ---")
    rx_volume_df = generate_rx_volume(hcps_df, visit_logs_df, cities_df)
    print()
    
    # Summary statistics
    print("=" * 60)
    print("GENERATION COMPLETE — Summary")
    print("=" * 60)
    print(f"Cities:     {len(cities_df):>10,} rows")
    print(f"Reps:       {len(reps_df):>10,} rows")
    print(f"HCPs:       {len(hcps_df):>10,} rows")
    print(f"Visits:     {len(visit_logs_df):>10,} rows")
    print(f"Rx Volume:  {len(rx_volume_df):>10,} rows")
    
    # Verification: show embedded patterns
    print()
    print("--- Pattern Verification ---")
    
    # 1. Chandigarh rep over-deployment
    chandigarh_reps = reps_df[reps_df['city'] == 'Chandigarh']
    print(f"Chandigarh reps: {len(chandigarh_reps)} (Tier3 city with {cities_df[cities_df['city_name']=='Chandigarh']['specialist_count'].values[0]} specialists)")
    
    # 2. Under-deployed high-potential cities
    for city_name in ['Patna', 'Bhubaneswar', 'Indore']:
        city_reps = reps_df[reps_df['city'] == city_name]
        city_prev = cities_df[cities_df['city_name'] == city_name]['disease_prevalence_index'].values[0]
        print(f"{city_name}: {len(city_reps)} reps, prevalence index = {city_prev}")
    
    # 3. Loyalty-based Rx response
    print()
    print("--- Avg Rx by Loyalty Tier (should show Brand_Loyal > Switcher > Competitor_Loyal) ---")
    loyalty_rx = rx_volume_df.merge(hcps_df[['hcp_id', 'loyalty_tier']], on='hcp_id')
    print(loyalty_rx.groupby('loyalty_tier')['rx_count'].mean().round(2))
    
    # 4. Sample rows from each table
    print()
    print("=" * 60)
    print("SAMPLE DATA — First 5 rows of each table")
    print("=" * 60)
    
    for name, df in [('cities', cities_df), ('reps', reps_df), ('hcps', hcps_df),
                     ('visit_logs', visit_logs_df), ('rx_volume', rx_volume_df)]:
        print(f"\n--- {name}.csv ---")
        print(df.head().to_string(index=False))
