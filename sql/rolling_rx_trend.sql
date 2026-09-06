/*
 * Query 4: 3-Month Rolling Average Rx Trend per Rep
 * ===================================================
 * Purpose: Compute a 3-month rolling average of Rx volume per rep to
 *          smooth out monthly noise and identify reps with consistently
 *          declining vs growing prescription trends.
 *
 * Business context: Monthly Rx data is noisy (seasonal effects, random
 * variation). A 3-month rolling average reveals the underlying trajectory.
 * Reps with declining trajectories need intervention BEFORE they fall
 * further. Reps with growing trajectories should be studied for best
 * practices to replicate.
 *
 * Window function: AVG() OVER (PARTITION BY rep_id ORDER BY month_year
 *                  ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
 * This gives us a trailing 3-month average for each rep-month combination.
 *
 * Output columns: rep_id, rep_name, city, region, month_year,
 *                 monthly_rx, rolling_3m_avg_rx
 */

WITH rep_monthly_rx AS (
    -- Aggregate total Rx per rep per month
    -- Attribution: Rx from HCPs the rep visited in any month counts toward that rep
    SELECT
        r.rep_id,
        r.rep_name,
        r.city,
        r.region,
        rx.month_year,
        SUM(rx.rx_count) AS monthly_rx
    FROM reps r
    -- Get distinct HCPs each rep visits
    JOIN (
        SELECT DISTINCT rep_id, hcp_id
        FROM visit_logs
    ) vl ON r.rep_id = vl.rep_id
    -- Get Rx volume for those HCPs (for the drug the rep promotes)
    JOIN rx_volume rx ON vl.hcp_id = rx.hcp_id AND rx.drug_name = r.drug_focus
    GROUP BY r.rep_id, r.rep_name, r.city, r.region, rx.month_year
)
SELECT
    rep_id,
    rep_name,
    city,
    region,
    month_year,
    monthly_rx,
    -- 3-month trailing rolling average using window function
    -- ROWS BETWEEN 2 PRECEDING AND CURRENT ROW = current month + 2 prior months
    ROUND(
        AVG(monthly_rx) OVER (
            PARTITION BY rep_id
            ORDER BY month_year
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ), 2
    ) AS rolling_3m_avg_rx
FROM rep_monthly_rx
ORDER BY rep_id, month_year;
