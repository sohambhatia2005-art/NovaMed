"""
NovaMed SFE — SQLite Database Loader & SQL Query Executor
==========================================================
Creates a SQLite database from the raw CSV files and executes all 4 SQL
query files, saving results as processed CSVs.

Workflow:
1. Load all 5 CSV tables into a SQLite database
2. Execute each .sql file from the sql/ directory
3. Save query results to data/processed/
4. Print first 10 rows of each result for verification

Author: Aditya (NovaMed SFE Portfolio Project)
"""

import os
import sqlite3
import pandas as pd

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
PROCESSED_DIR = os.path.join(BASE_DIR, 'data', 'processed')
SQL_DIR = os.path.join(BASE_DIR, 'sql')
DB_PATH = os.path.join(BASE_DIR, 'data', 'novamed.db')

os.makedirs(PROCESSED_DIR, exist_ok=True)


# ============================================================================
# 1. CREATE SQLITE DATABASE FROM RAW CSVs
# ============================================================================

def create_database():
    """
    Loads all raw CSVs into a persistent SQLite database.
    Using a file-based DB (not in-memory) so the database can be inspected
    independently if needed for debugging or ad-hoc queries.
    """
    # Remove existing DB to ensure clean state
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    
    # Table definitions with proper types for SQLite
    tables = {
        'cities': 'cities.csv',
        'reps': 'reps.csv',
        'hcps': 'hcps.csv',
        'visit_logs': 'visit_logs.csv',
        'rx_volume': 'rx_volume.csv'
    }
    
    for table_name, csv_file in tables.items():
        csv_path = os.path.join(RAW_DIR, csv_file)
        df = pd.read_csv(csv_path)
        df.to_sql(table_name, conn, index=False, if_exists='replace')
        print(f"  Loaded {table_name}: {len(df):,} rows, {len(df.columns)} columns")
    
    # Create indexes for query performance
    # These indexes target the JOIN and GROUP BY columns used in our queries
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_visit_rep ON visit_logs(rep_id)",
        "CREATE INDEX IF NOT EXISTS idx_visit_hcp ON visit_logs(hcp_id)",
        "CREATE INDEX IF NOT EXISTS idx_visit_date ON visit_logs(visit_date)",
        "CREATE INDEX IF NOT EXISTS idx_rx_hcp ON rx_volume(hcp_id)",
        "CREATE INDEX IF NOT EXISTS idx_rx_month ON rx_volume(month_year)",
        "CREATE INDEX IF NOT EXISTS idx_rx_drug ON rx_volume(drug_name)",
        "CREATE INDEX IF NOT EXISTS idx_hcp_city ON hcps(city_id)",
    ]
    
    cursor = conn.cursor()
    for idx_sql in indexes:
        cursor.execute(idx_sql)
    conn.commit()
    
    print(f"\n  Database created at: {DB_PATH}")
    print(f"  Indexes created: {len(indexes)}")
    
    return conn


# ============================================================================
# 2. EXECUTE SQL QUERIES AND SAVE RESULTS
# ============================================================================

def execute_query(conn, sql_filename, output_csv_name):
    """
    Reads a .sql file, executes it against the SQLite database,
    saves the result as a CSV, and prints the first 10 rows.
    """
    sql_path = os.path.join(SQL_DIR, sql_filename)
    output_path = os.path.join(PROCESSED_DIR, output_csv_name)
    
    # Read SQL
    with open(sql_path, 'r') as f:
        sql_query = f.read()
    
    # Execute and fetch results into a DataFrame
    df = pd.read_sql_query(sql_query, conn)
    
    # Save to CSV
    df.to_csv(output_path, index=False)
    
    # Report
    print(f"  Result: {len(df):,} rows × {len(df.columns)} columns")
    print(f"  Saved to: {output_csv_name}")
    print(f"\n  First 10 rows:")
    print(df.head(10).to_string(index=False))
    
    return df


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("NovaMed SFE — SQL Analysis Pipeline")
    print("=" * 70)
    
    # Step 1: Create database
    print("\n--- Step 1: Loading data into SQLite ---")
    conn = create_database()
    
    # Step 2: Execute each query
    queries = [
        {
            'sql_file': 'rep_ranking.sql',
            'output_csv': 'rep_ranking.csv',
            'description': 'Query 1: Rep Ranking by Rx Volume (Regional & Overall)'
        },
        {
            'sql_file': 'visit_rx_lag.sql',
            'output_csv': 'visit_rx_lag.csv',
            'description': 'Query 2: Post-Visit Rx Lift Analysis'
        },
        {
            'sql_file': 'hcp_coverage.sql',
            'output_csv': 'hcp_coverage.csv',
            'description': 'Query 3: HCP Coverage Gap Analysis'
        },
        {
            'sql_file': 'rolling_rx_trend.sql',
            'output_csv': 'rolling_rx_trend.csv',
            'description': 'Query 4: 3-Month Rolling Rx Trend'
        }
    ]
    
    results = {}
    for i, q in enumerate(queries, 1):
        print(f"\n{'─' * 70}")
        print(f"--- {q['description']} ---")
        print(f"{'─' * 70}")
        results[q['output_csv']] = execute_query(conn, q['sql_file'], q['output_csv'])
    
    # Step 3: Summary statistics
    print(f"\n{'=' * 70}")
    print("SQL ANALYSIS COMPLETE — Summary")
    print(f"{'=' * 70}")
    
    for csv_name, df in results.items():
        print(f"  {csv_name:35s} → {len(df):>6,} rows × {len(df.columns):>2} columns")
    
    # Quick validation checks
    print(f"\n--- Validation Checks ---")
    
    # Check 1: Rep ranking should have 120 reps
    rep_count = len(results['rep_ranking.csv'])
    print(f"  Rep ranking rows: {rep_count} (expected 120) {'✓' if rep_count == 120 else '✗'}")
    
    # Check 2: HCP coverage should have 2000 HCPs
    hcp_count = len(results['hcp_coverage.csv'])
    print(f"  HCP coverage rows: {hcp_count} (expected 2000) {'✓' if hcp_count == 2000 else '✗'}")
    
    # Check 3: Under-covered HCPs should exist
    under_covered = results['hcp_coverage.csv'][
        results['hcp_coverage.csv']['coverage_flag'] == 'Under-covered'
    ]
    print(f"  Under-covered HCPs (top potential, low visits): {len(under_covered)}")
    
    # Check 4: Over-covered HCPs should exist
    over_covered = results['hcp_coverage.csv'][
        results['hcp_coverage.csv']['coverage_flag'] == 'Over-covered'
    ]
    print(f"  Over-covered HCPs (low potential, high visits): {len(over_covered)}")
    
    # Check 5: Rx lift by loyalty tier
    lag_df = results['visit_rx_lag.csv']
    print(f"\n  Avg Rx lift % by loyalty tier:")
    loyalty_lift = lag_df.groupby('loyalty_tier')['rx_lift_pct'].mean()
    for tier, lift in loyalty_lift.items():
        print(f"    {tier:20s}: {lift:+.2f}%")
    
    conn.close()
    print(f"\n  Database connection closed.")
