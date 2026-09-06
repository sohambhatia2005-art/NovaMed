/*
 * Query 2: Post-Visit Rx Lift Analysis
 * =====================================
 * Purpose: For each rep-HCP pair, measure the average Rx count in the
 *          30 days AFTER a visit vs the 30 days BEFORE a visit. The
 *          difference is the "post-visit Rx lift" — a direct measure
 *          of whether rep visits are driving incremental prescriptions.
 *
 * Business context: This is the core SFE metric. If a rep visits an HCP
 * and Rx volume doesn't change, the visit is not generating ROI. The
 * 30-day window is industry standard — long enough to capture delayed
 * prescribing behavior shifts, short enough to attribute to a specific visit.
 *
 * Approach: Self-join on visit_logs + rx_volume. For each visit event,
 * look up Rx in the month containing (visit_date - 30d) and the month
 * containing (visit_date + 30d). Compare averages.
 *
 * Output columns: rep_id, rep_name, hcp_id, hcp_name, loyalty_tier,
 *                 avg_rx_before, avg_rx_after, rx_lift, rx_lift_pct
 */

WITH visit_months AS (
    -- For each visit, determine the "before" month and "after" month
    -- SQLite date functions: date(visit_date, '-30 days') and date(visit_date, '+30 days')
    SELECT
        vl.rep_id,
        vl.hcp_id,
        vl.visit_date,
        -- The month 30 days before the visit (format: YYYY-MM to match rx_volume.month_year)
        strftime('%Y-%m', date(vl.visit_date, '-30 days')) AS before_month,
        -- The month 30 days after the visit
        strftime('%Y-%m', date(vl.visit_date, '+30 days')) AS after_month
    FROM visit_logs vl
),
rx_before_after AS (
    -- Join each visit's before/after months to actual Rx data
    SELECT
        vm.rep_id,
        vm.hcp_id,
        -- Rx in the "before" month
        COALESCE(rx_before.rx_count, 0) AS rx_before,
        -- Rx in the "after" month
        COALESCE(rx_after.rx_count, 0) AS rx_after
    FROM visit_months vm
    LEFT JOIN rx_volume rx_before
        ON vm.hcp_id = rx_before.hcp_id
        AND vm.before_month = rx_before.month_year
    LEFT JOIN rx_volume rx_after
        ON vm.hcp_id = rx_after.hcp_id
        AND vm.after_month = rx_after.month_year
)
SELECT
    rba.rep_id,
    r.rep_name,
    rba.hcp_id,
    h.hcp_name,
    h.loyalty_tier,
    ROUND(AVG(rba.rx_before), 2) AS avg_rx_before,
    ROUND(AVG(rba.rx_after), 2) AS avg_rx_after,
    ROUND(AVG(rba.rx_after) - AVG(rba.rx_before), 2) AS rx_lift,
    -- Percentage lift: avoid division by zero
    CASE
        WHEN AVG(rba.rx_before) > 0
        THEN ROUND((AVG(rba.rx_after) - AVG(rba.rx_before)) / AVG(rba.rx_before) * 100, 2)
        ELSE NULL
    END AS rx_lift_pct
FROM rx_before_after rba
JOIN reps r ON rba.rep_id = r.rep_id
JOIN hcps h ON rba.hcp_id = h.hcp_id
GROUP BY rba.rep_id, r.rep_name, rba.hcp_id, h.hcp_name, h.loyalty_tier
ORDER BY rx_lift_pct DESC;
