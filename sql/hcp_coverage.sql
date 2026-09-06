/*
 * Query 3: HCP Coverage Gap Analysis
 * ====================================
 * Purpose: Calculate visit frequency per HCP (visits per month) and join
 *          with the HCP's potential_score. Flag HCPs in the TOP quartile
 *          of potential_score but BOTTOM quartile of visit frequency as
 *          "under-covered" — these are the biggest missed opportunities.
 *
 * Business context: A high-potential HCP who isn't being visited frequently
 * is a direct revenue leak. This query identifies exactly where rep effort
 * should be redirected. The quartile approach avoids arbitrary thresholds
 * and adapts to the actual data distribution.
 *
 * Logic:
 *   - NTILE(4) on potential_score → top quartile = Q4 = highest potential
 *   - NTILE(4) on visits_per_month → bottom quartile = Q1 = least visited
 *   - Flag: potential_quartile = 4 AND visit_quartile = 1 → "Under-covered"
 *
 * Output columns: hcp_id, hcp_name, city_name, specialty, loyalty_tier,
 *                 potential_score, total_visits, active_months,
 *                 visits_per_month, potential_quartile, visit_quartile,
 *                 coverage_flag
 */

WITH hcp_visit_stats AS (
    -- Calculate total visits and active months per HCP
    SELECT
        h.hcp_id,
        h.hcp_name,
        c.city_name,
        h.specialty,
        h.loyalty_tier,
        h.potential_score,
        COUNT(vl.visit_id) AS total_visits,
        -- Number of distinct months with visits (for per-month calculation)
        COUNT(DISTINCT strftime('%Y-%m', vl.visit_date)) AS active_months
    FROM hcps h
    LEFT JOIN visit_logs vl ON h.hcp_id = vl.hcp_id
    LEFT JOIN cities c ON h.city_id = c.city_id
    GROUP BY h.hcp_id, h.hcp_name, c.city_name, h.specialty, h.loyalty_tier, h.potential_score
),
with_frequency AS (
    -- Calculate visits per month (using 18 as total months in study period)
    SELECT
        *,
        ROUND(CAST(total_visits AS FLOAT) / 18.0, 2) AS visits_per_month
    FROM hcp_visit_stats
),
with_quartiles AS (
    -- Assign quartiles using NTILE window function
    SELECT
        *,
        NTILE(4) OVER (ORDER BY potential_score ASC) AS potential_quartile,
        NTILE(4) OVER (ORDER BY visits_per_month ASC) AS visit_quartile
    FROM with_frequency
)
SELECT
    hcp_id,
    hcp_name,
    city_name,
    specialty,
    loyalty_tier,
    potential_score,
    total_visits,
    active_months,
    visits_per_month,
    potential_quartile,
    visit_quartile,
    CASE
        -- Top quartile potential (Q4) AND bottom quartile visits (Q1) = Under-covered
        WHEN potential_quartile = 4 AND visit_quartile = 1 THEN 'Under-covered'
        -- Bottom quartile potential (Q1) AND top quartile visits (Q4) = Over-covered
        WHEN potential_quartile = 1 AND visit_quartile = 4 THEN 'Over-covered'
        ELSE 'Appropriately-covered'
    END AS coverage_flag
FROM with_quartiles
ORDER BY
    CASE WHEN potential_quartile = 4 AND visit_quartile = 1 THEN 0 ELSE 1 END,
    potential_score DESC;
