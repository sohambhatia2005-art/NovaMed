# NovaMed SFE — Tableau Public Dashboard Build Guide

> **Author:** Aditya  
> **Date:** April 2026  
> **Purpose:** Step-by-step instructions to build a professional 5-sheet Tableau Public dashboard from the exported CSV files. Follow this guide sequentially — every design choice is made for you, every reason is explained.

---

## Section 1 — Dashboard Overview

### The Story This Dashboard Tells

The dashboard answers one central question for NovaMed's VP of Sales:

> **"Where are our sales reps being wasted, and where should we redeploy them for maximum Rx growth?"**

A viewer should be able to conclude within **60 seconds**:
1. **Which reps** are working hard but getting poor results (Rep Quadrant)
2. **Which cities** are under-resourced vs over-resourced (Territory Map)
3. **Which HCPs** are being over-visited vs under-visited (Priority Buckets)
4. **How performance is trending** over time (Rx Trends)
5. **What the reallocation opportunity** looks like in numbers (Visit Distribution)

### Layout Logic

The dashboard flows **top-to-bottom, left-to-right** — mirroring how a consulting slide deck would be consumed:
- **Top row:** The strategic overview (Territory Map + Rep Quadrant)
- **Middle row:** The diagnostic deep-dive (HCP Buckets + KPI Heatmap)
- **Bottom row:** The temporal proof (Rx Trend Lines)

This layout follows the **"situation → complication → resolution"** narrative structure commonly used in consulting presentations.

### Sheet Count

5 analytical sheets + 1 dashboard title/annotation area = **5 sheets assembled into 1 dashboard**.

---

## Section 2 — Tableau Setup Instructions

### Data Source Connections

1. **Open Tableau Public** (or Tableau Desktop)
2. Click **"Connect" → "Text file"** (for CSV)
3. Connect to each of the 5 CSV files individually from the `outputs/tableau/` directory:
   - `tableau_rep_performance.csv`
   - `tableau_hcp_coverage.csv`
   - `tableau_territory_summary.csv`
   - `tableau_rx_trends.csv`
   - `tableau_visit_distribution.csv`

### Data Source Strategy

Use **separate data sources** (not a single joined source). Each CSV is already fully denormalized and self-contained. Joining them in Tableau would create unnecessary complexity and row multiplication.

**Do NOT define relationships between the files** — each sheet draws from one CSV only.

### Column Data Type Configuration

After connecting each file, verify these data types in Tableau's data source pane:

#### tableau_rep_performance.csv
| Column | Tableau Type | Dimension/Measure |
|--------|--------|-----|
| rep_id | Number (Whole) | **Dimension** (not a measure — it's an identifier) |
| rep_name | String | Dimension |
| city | String | Dimension |
| region | String | Dimension |
| drug_focus | String | Dimension |
| tenure_years | Number (Whole) | Measure |
| total_visits | Number (Whole) | Measure |
| total_rx_generated | Number (Whole) | Measure |
| visit_intensity | Number (Decimal) | Measure |
| efficiency_ratio | Number (Decimal) | Measure |
| performance_quadrant | String | Dimension |
| region_rank | Number (Whole) | Measure |
| overall_rank | Number (Whole) | Measure |
| mpi_score | Number (Decimal) | Measure |
| territory_cluster | String | Dimension |

#### tableau_hcp_coverage.csv
| Column | Tableau Type | Dimension/Measure |
|--------|--------|-----|
| hcp_id | Number (Whole) | **Dimension** |
| hcp_name | String | Dimension |
| city | String | Dimension |
| specialty | String | Dimension |
| loyalty_tier | String | Dimension |
| potential_score | Number (Whole) | Measure |
| visits_per_month | Number (Decimal) | Measure |
| post_visit_rx_lift_pct | Number (Decimal) | Measure |
| priority_bucket | String | Dimension |
| coverage_flag | String | Dimension |
| assigned_rep_id | Number (Whole) | **Dimension** |
| assigned_rep_name | String | Dimension |

#### tableau_territory_summary.csv
| Column | Tableau Type | Dimension/Measure |
|--------|--------|-----|
| city_name | String | Dimension |
| region | String | Dimension |
| tier | String | Dimension |
| population_millions | Number (Decimal) | Measure |
| specialist_count | Number (Whole) | Measure |
| disease_prevalence_index | Number (Whole) | Measure |
| mpi_score | Number (Decimal) | Measure |
| avg_visit_intensity | Number (Decimal) | Measure |
| avg_efficiency_ratio | Number (Decimal) | Measure |
| territory_cluster | String | Dimension |
| num_reps_assigned | Number (Whole) | Measure |
| total_rx_volume | Number (Whole) | Measure |
| rx_per_rep | Number (Decimal) | Measure |
| latitude | Number (Decimal) | Measure (geographic role: Latitude) |
| longitude | Number (Decimal) | Measure (geographic role: Longitude) |

#### tableau_rx_trends.csv
| Column | Tableau Type | Dimension/Measure |
|--------|--------|-----|
| rep_id | Number (Whole) | **Dimension** |
| rep_name | String | Dimension |
| region | String | Dimension |
| city | String | Dimension |
| month_year | String | **Dimension** (keep as string, not date — format is YYYY-MM) |
| monthly_rx | Number (Whole) | Measure |
| rolling_3m_avg_rx | Number (Decimal) | Measure |
| efficiency_ratio | Number (Decimal) | Measure |
| performance_quadrant | String | Dimension |

#### tableau_visit_distribution.csv
| Column | Tableau Type | Dimension/Measure |
|--------|--------|-----|
| priority_bucket | String | Dimension |
| state | String | Dimension |
| visit_share_pct | Number (Decimal) | Measure |
| rx_yield_per_visit | Number (Decimal) | Measure |
| wasted_effort_flag | Boolean | Dimension |

> **Important:** After setting types, right-click any ID columns (rep_id, hcp_id, assigned_rep_id) and select **"Convert to Dimension"** — Tableau often auto-classifies number columns as Measures.

---

## Section 3 — Sheet-by-Sheet Build Instructions

### Sheet 1: Rep Performance Quadrant

**Data source:** `tableau_rep_performance.csv`

**Business insight:** Immediately reveals which reps are high-effort/low-impact — the strongest candidates for territory reassignment.

**Build steps:**
1. Drag `visit_intensity` → **Columns**
2. Drag `efficiency_ratio` → **Rows**
3. Drag `performance_quadrant` → **Color** (Marks card)
4. Drag `rep_name` → **Detail** (Marks card)
5. Drag `city` → **Detail** (Marks card)
6. Chart type: Select **"Circle"** from the Marks dropdown (or use Shape)
7. Set colors:
   - High Effort, High Impact → `#2E86AB` (steel blue)
   - High Effort, Low Impact → `#F18F01` (amber)
   - Low Effort, High Impact → `#2D7D46` (green)
   - Low Effort, Low Impact → `#C73E1D` (rust red)
8. Set circle **Size** slightly smaller than default (about 40% of max)
9. **Tooltip:** Edit to show:
   ```
   Rep: <rep_name>
   City: <city> | Region: <region>
   Drug: <drug_focus>
   Visit Intensity: <visit_intensity> visits/HCP/month
   Efficiency Ratio: <efficiency_ratio>
   Quadrant: <performance_quadrant>
   ```
10. Add **reference lines**:
    - Right-click X-axis → "Add Reference Line" → Median of `visit_intensity` → Dashed gray line
    - Right-click Y-axis → "Add Reference Line" → Median of `efficiency_ratio` → Dashed gray line
    - Right-click Y-axis → "Add Reference Line" → Constant = 1.0 → Dotted thin gray line (expected performance)
11. **Title:** "Rep Performance Quadrant"
12. **Name the sheet:** `Rep Quadrant`

---

### Sheet 2: Territory Opportunity Map

**Data source:** `tableau_territory_summary.csv`

**Business insight:** Visualizes which cities are under-resourced (red) vs appropriately covered (green), with MPI and coverage intensity accessible via tooltip.

**Build steps:**
1. Drag `longitude` → **Columns**
2. Drag `latitude` → **Rows**
3. In the upper-right of the view, click **"Show Me"** → select **"Symbol Map"** (or "Filled Map" may not work well for Indian cities — use symbol map with lat/lon)
4. Drag `territory_cluster` → **Color** (Marks card)
5. Drag `mpi_score` → **Size** (Marks card) — larger circles = higher MPI
6. Drag `city_name` → **Label** (Marks card) — show city names on the map
7. Set colors:
   - Under-covered, High Potential → `#C73E1D` (red — urgent)
   - Over-covered, High Potential → `#2E86AB` (blue — review)
   - Over-covered, Low Potential → `#F18F01` (amber — consolidate)
   - Appropriately Covered → `#2D7D46` (green — maintain)
8. **Tooltip:** Edit to show:
   ```
   City: <city_name> (<tier>)
   Region: <region>
   MPI Score: <mpi_score>
   Coverage Intensity: <avg_visit_intensity>
   Reps Assigned: <num_reps_assigned>
   Cluster: <territory_cluster>
   ```
9. Adjust the map to center on India: double-click the map and pan/zoom to show all 15 cities clearly
10. **Title:** "Territory Opportunity Map"
11. **Name the sheet:** `Territory Map`

> **Note on geocoding:** Tableau may not perfectly geocode all Indian cities from names alone. That's why latitude and longitude columns are provided. If Tableau's auto-geocoding works, great. If not, use the latitude and longitude fields as continuous measures on Rows and Columns (as described above), which will plot cities as points on a blank map. To add a background map, go to **Map → Background Maps → Tableau** or **Map → Map Layers** and ensure the map layer is visible.

---

### Sheet 3: HCP Priority Bucket Breakdown

**Data source:** `tableau_visit_distribution.csv`

**Business insight:** Shows the stark gap between current visit allocation and the recommended allocation — the "wasted effort" story in one visual.

**Build steps:**
1. Drag `priority_bucket` → **Columns**
2. Drag `visit_share_pct` → **Rows**
3. Drag `state` → **Color** (Marks card)
4. Chart type: **Bar** (side-by-side grouped bars)
5. Set colors:
   - Current → `#CCCCCC` (light gray)
   - Recommended → Use the priority bucket color from the palette:
     - Since color is mapped to `state` (not bucket), use:
     - Current → `#BBBBBB` (gray)
     - Recommended → `#2E86AB` (blue)
6. Drag `visit_share_pct` → **Label** → Format as percentage (one decimal)
7. Add a **reference line** on the Rows axis:
   - Constant = 25 (approximate "fair share" per bucket if evenly distributed)
   - Style: thin dotted gray line
   - Label: "Even distribution"
8. **Tooltip:** Edit to show:
   ```
   Bucket: <priority_bucket>
   State: <state>
   Visit Share: <visit_share_pct>%
   Rx Yield per Visit: <rx_yield_per_visit>
   ```
9. Add an **annotation** (right-click → Annotate → Area):
   - Over the C+D current bars: "50.5% of visits go to low-value HCPs"
10. **Title:** "Visit Allocation: Current vs Recommended"
11. **Name the sheet:** `HCP Buckets`

---

### Sheet 4: Rx Performance Trend Lines

**Data source:** `tableau_rx_trends.csv`

**Business insight:** Shows diverging performance trajectories over time — top reps accelerate while bottom reps stagnate. Makes the case for early intervention.

**Build steps:**
1. First, create a **Set** to filter to top/bottom reps:
   - Right-click `rep_id` → Create → Set → Name it "Top Bottom 10 Reps"
   - In the Set dialog, select the **"Condition"** tab → By field → `efficiency_ratio` → keep top 5 and bottom 5
   - **Alternative (easier):** Create a calculated field:
     ```
     IF [efficiency_ratio] >= 1.9 OR [efficiency_ratio] <= 0.92
     THEN "Show"
     ELSE "Hide"
     END
     ```
     Then filter this field to "Show"
2. Drag `month_year` → **Columns** (keep as Dimension, Discrete)
3. Drag `rolling_3m_avg_rx` → **Rows**
4. Drag `rep_name` → **Color** (Marks card)
5. Drag `performance_quadrant` → **Detail** (Marks card)
6. Chart type: **Line**
7. Color the lines:
   - Top performers (high efficiency): shades of green (`#1a7a3a` to `#6acc8e`)
   - Bottom performers (low efficiency): shades of red (`#922b21` to `#ec917f`)
   - You can use `performance_quadrant` on Color instead of `rep_name` if simpler
8. **Tooltip:** Edit to show:
   ```
   Rep: <rep_name>
   City: <city> | Region: <region>
   Month: <month_year>
   Rolling 3M Avg Rx: <rolling_3m_avg_rx>
   Efficiency Ratio: <efficiency_ratio>
   ```
9. Right-click X-axis → Rotate labels 45°
10. **Title:** "Rx Trend Lines — Top 5 vs Bottom 5 Reps"
11. **Name the sheet:** `Rx Trends`

---

### Sheet 5: City-Level KPI Heatmap

**Data source:** `tableau_territory_summary.csv`

**Business insight:** A summary table that lets the viewer compare all key metrics across cities at a glance. Color-coding makes over/under-performance immediately visible.

**Build steps:**
1. Drag `city_name` → **Rows**
2. Sort `city_name` by `mpi_score` descending (right-click → Sort → Field → `mpi_score` → Descending)
3. Create **4 separate columns** by multi-selecting measures:
   - Drag `mpi_score` → **Columns** (Text table / Square mark)
   - Then also add `avg_visit_intensity`, `avg_efficiency_ratio` to **Columns** (use Measure Values)
   
   **Easier approach using Measure Names/Values:**
   - Drag `Measure Values` → **Text** (in Marks card)
   - Drag `Measure Names` → **Columns**
   - Filter `Measure Names` to show only: `mpi_score`, `avg_visit_intensity`, `avg_efficiency_ratio`
   - Drag `Measure Values` → **Color** as well
4. Chart type: **Square** (from Marks dropdown) or **Text** for a highlight table
5. Color: Use **diverging palette** (Red-Green or Red-Yellow-Green)
   - Edit color → choose "Red-Green Diverging" → Center = median value → check "Stepped Color" with 5 steps
6. Drag `territory_cluster` → **Detail** to include in tooltip
7. Drag `tier` → after `city_name` in **Rows** to show the tier next to each city
8. **Tooltip:** Edit to show:
   ```
   City: <city_name> (<tier>)
   MPI Score: <mpi_score>
   Visit Intensity: <avg_visit_intensity>
   Efficiency Ratio: <avg_efficiency_ratio>
   Cluster: <territory_cluster>
   Reps: <num_reps_assigned>
   ```
9. Format numbers: MPI to 1 decimal, Visit Intensity to 2 decimals, Efficiency to 3 decimals
10. **Title:** "City KPI Heatmap"
11. **Name the sheet:** `City Heatmap`

---

## Section 4 — Dashboard Assembly Instructions

### Create Dashboard

1. Click the **"New Dashboard"** tab (bottom of Tableau)
2. Set **Size:** `1400 × 900 pixels` (Fixed size — optimized for Tableau Public embedding and laptop screens)

### Layout Arrangement

Arrange the 5 sheets using this ASCII layout:

```
┌──────────────────────────────────────────────────────────────────┐
│                     DASHBOARD TITLE BAR                          │
│  "NovaMed Pharmaceuticals — Sales Force Effectiveness Dashboard" │
│  Subtitle: "Territory Optimization Analysis | April 2026"        │
├──────────────────────────────┬───────────────────────────────────┤
│                              │                                   │
│      Territory Map           │      Rep Performance Quadrant     │
│      (Sheet 2)               │      (Sheet 1)                   │
│      ~50% width              │      ~50% width                  │
│      ~45% height             │      ~45% height                 │
│                              │                                   │
├──────────────────────────────┼───────────────────────────────────┤
│                              │                                   │
│    HCP Priority Buckets      │      City KPI Heatmap            │
│    (Sheet 3)                 │      (Sheet 5)                   │
│    ~50% width                │      ~50% width                  │
│    ~30% height               │      ~30% height                 │
│                              │                                   │
├──────────────────────────────┴───────────────────────────────────┤
│                                                                  │
│              Rx Performance Trend Lines (Sheet 4)                │
│              Full width, ~25% height                             │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│ Key Recommendation: "Redeploy 4-5 reps from Chandigarh and      │
│ metros to Bhubaneswar, Patna, and Indore — estimated +15-20%    │
│ Rx growth in targeted territories at zero incremental cost."     │
└──────────────────────────────────────────────────────────────────┘
```

### Assembly Steps

1. Drag sheets from the left panel onto the canvas in this order:
   - First, add a **Horizontal container** for the top row → drag `Territory Map` and `Rep Quadrant` into it
   - Add another **Horizontal container** for the middle row → drag `HCP Buckets` and `City Heatmap` into it
   - Add `Rx Trends` as a full-width element below
2. Add a **Text** object at the top for the dashboard title:
   - Title: **"NovaMed Pharmaceuticals — Sales Force Effectiveness Dashboard"** (Bold, 18pt)
   - Subtitle: *"Territory Optimization Analysis | Prepared by Aditya | April 2026"* (Italic, 11pt, gray)
3. Add a **Text** object at the bottom for the key recommendation:
   - Text: *"Key Recommendation: Redeploy 4-5 reps from Chandigarh and metros to Bhubaneswar, Patna, and Indore — estimated +15-20% Rx growth in targeted territories at zero incremental cost."*
   - Style: 10pt, bold, dark red (`#C73E1D`)

### Filter Actions

Add interactivity so clicking a city on the map filters the other sheets:

1. Go to **Dashboard → Actions → Add Action → Filter**
   - **Source:** `Territory Map`
   - **Target:** `Rep Quadrant` and `Rx Trends`
   - Run action on: **Select**
   - Clearing the selection will: **Show all values**
   - Filter by: `city_name` = `city` (map the city field between sources)

This means: **clicking a city on the map will filter the Rep Quadrant to show only reps in that city, and the Rx Trends to show only those reps' trend lines.** This enables drill-down analysis during presentations.

### Publishing to Tableau Public

1. Go to **Server → Tableau Public → Save to Tableau Public**
2. Log in to your Tableau Public account
3. Title the workbook: **"NovaMed SFE — Territory Optimization Dashboard"**
4. Add tags: `pharma`, `sales force effectiveness`, `territory optimization`, `India`, `data analytics`
5. After publishing, copy the embed URL for your portfolio

---

## Section 5 — Design Decisions Explained

### Color Palette Choice

The four-color palette (`#2E86AB`, `#C73E1D`, `#F18F01`, `#2D7D46`) was chosen because:
- **Distinct hues** (blue, red, amber, green) are immediately distinguishable, even for colorblind viewers
- **Semantic meaning**: Red = urgent/problem, Green = good/maintain, Amber = caution, Blue = neutral/review
- **Professional feel**: These are muted, corporate-appropriate tones — not the saturated primary colors that feel like a school project
- This palette is consistent across all Python charts and the Tableau dashboard, creating visual cohesion

### Chart Type Decisions

| Sheet | Type | Why This Type |
|-------|------|---------------|
| Rep Quadrant | Scatter | The only chart type that shows **two continuous variables simultaneously**. The quadrant layout is the gold standard for performance-vs-effort analysis in consulting. |
| Territory Map | Symbol map | Maps are the **fastest way to communicate geographic patterns**. Symbol maps (vs filled) work better for India because state boundaries are less relevant than city-level data. |
| HCP Buckets | Grouped bar | Bars are the best for **comparing quantities across categories**. Grouped layout (current vs recommended) makes the gap immediately visible. A stacked bar would obscure the comparison. |
| Rx Trends | Line chart | Lines are the **only appropriate type for time series**. They show trajectory and direction, which is the key insight (diverging performance). |
| City Heatmap | Highlight table | Text tables with color encoding are the **most information-dense** format — they allow exact number comparison while using color for quick pattern detection. |

### Layout Order

The top-to-bottom flow follows consulting presentation logic:
1. **Top row (Map + Quadrant):** "Here's the big picture — where are the problems?" — answers the VP's first instinct to look at geography and people
2. **Middle row (Buckets + Heatmap):** "Here's WHY these problems exist" — the diagnostic layer explains visit misallocation and territory-level metrics
3. **Bottom row (Trends):** "Here's the PROOF over time" — the trend chart adds temporal credibility and urgency

This is the **"Pyramid Principle" (Minto)** applied to dashboard design: conclusion first, supporting evidence second, detailed proof third.

### Filter Interaction Design

City-level filtering (clicking the map filters other charts) was chosen because:
- The VP will naturally ask "What's happening in [city]?" after seeing the map
- Enabling this drill-down **in real-time during a presentation** is more powerful than switching slides
- It demonstrates Tableau interactivity skills, which is a key competency for data analyst roles

### Not Included (and Why)

- **No pie charts:** Pie charts make comparison difficult. The priority bucket breakdown uses bars instead.
- **No 3D effects:** They add visual noise without information value.
- **No dual-axis charts:** They confuse viewers about which scale to read. Each metric gets its own clear representation.
- **No default Tableau colors:** The default blue-orange palette is overused and doesn't carry semantic meaning. Custom colors signal intentional design.

---

*This guide was designed to be followed by someone who knows Tableau basics but shouldn't need to make any design decisions independently. Every choice has been made and justified. If you have questions during implementation, refer to the Design Decisions section for rationale.*
