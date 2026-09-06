/*
 * Query 1: Rep Ranking by Rx Volume (Regional & Overall)
 * ======================================================
 * Purpose: Rank all 120 reps by total Rx volume they've generated,
 *          partitioned by region. This powers the rep leaderboard
 *          and identifies top/bottom performers within each geography.
 *
 * Business context: Regional partitioning is critical because comparing
 * a Delhi rep (Tier1, high baseline Rx) directly to a Bhubaneswar rep
 * (Tier3, lower baseline) would be misleading. Region-level ranking
 * provides fairer peer comparison.
 *
 * Window functions used:
 *   - RANK() OVER (PARTITION BY region) for regional rank
 *   - RANK() OVER () for overall rank
 *
 * Output columns: rep_id, rep_name, city, region, drug_focus,
 *                 total_rx, region_rank, overall_rank
 */

WITH rep_rx AS (
    -- Aggregate total Rx volume per rep by joining reps → HCPs they visit → Rx records
    -- A rep "generates" Rx from HCPs they visit (attribution model: any visited HCP's Rx
    -- counts toward the visiting rep)
    SELECT
        r.rep_id,
        r.rep_name,
        r.city,
        r.region,
        r.drug_focus,
        COALESCE(SUM(rx.rx_count), 0) AS total_rx
    FROM reps r
    -- Join to get distinct HCPs each rep visits
    LEFT JOIN (
        SELECT DISTINCT rep_id, hcp_id
        FROM visit_logs
    ) vl ON r.rep_id = vl.rep_id
    -- Join to get Rx volume for those HCPs (matching the drug the rep promotes)
    LEFT JOIN rx_volume rx ON vl.hcp_id = rx.hcp_id AND rx.drug_name = r.drug_focus
    GROUP BY r.rep_id, r.rep_name, r.city, r.region, r.drug_focus
)
SELECT
    rep_id,
    rep_name,
    city,
    region,
    drug_focus,
    total_rx,
    RANK() OVER (PARTITION BY region ORDER BY total_rx DESC) AS region_rank,
    RANK() OVER (ORDER BY total_rx DESC) AS overall_rank
FROM rep_rx
ORDER BY overall_rank;
