"""
NovaMed SFE — Tableau Workbook (.twbx) Generator
=================================================
Generates a packaged Tableau workbook (.twbx) bundling all 5 dashboard CSVs as
pre-configured data sources. Each data source has correct datatypes and
dimension/measure roles per the TABLEAU_BUILD_GUIDE.md spec.

Output: outputs/tableau/novamed_sfe.twbx

What this gives you when you open it in Tableau Desktop:
  - 5 connected data sources, all columns correctly typed
  - IDs (rep_id, hcp_id, etc.) classified as Dimensions, not Measures
  - latitude/longitude on the territory_summary source flagged with geographic roles
  - 5 empty starter worksheets (one per data source) to build into

What's still on you (~30-45 min in Tableau Desktop):
  - Build the actual viz on each sheet following TABLEAU_BUILD_GUIDE.md
  - Assemble the dashboard
  - Server -> Tableau Public -> Save to publish

Why empty sheets and not pre-built ones:
  Tableau's worksheet XML schema is undocumented and version-sensitive.
  Hand-authoring complex sheets (scatter with reference lines, symbol map with
  custom geocoding, highlight tables) from scratch reliably across Tableau
  versions is a losing battle. Pre-typed data sources are the high-value,
  reliable part. Sheets should be built interactively.

Usage:
    python analysis/build_twbx.py
"""

import os
import shutil
import tempfile
import zipfile
from xml.dom import minidom
from xml.etree import ElementTree as ET

# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLEAU_DIR = os.path.join(BASE_DIR, "outputs", "tableau")
OUTPUT_TWBX = os.path.join(TABLEAU_DIR, "novamed_sfe.twbx")

# ============================================================================
# DATA SOURCE SPECIFICATIONS
# ----------------------------------------------------------------------------
# Per TABLEAU_BUILD_GUIDE.md Section 2 — Column Data Type Configuration.
# Each tuple: (column_name, datatype, role, [optional geographic_role])
#   datatype: 'integer' | 'real' | 'string' | 'boolean'
#   role:     'dimension' | 'measure'
# ============================================================================

DATASOURCES = [
    {
        "id": "rep_performance",
        "caption": "Rep Performance",
        "file": "tableau_rep_performance.csv",
        "columns": [
            ("rep_id", "integer", "dimension"),
            ("rep_name", "string", "dimension"),
            ("city", "string", "dimension"),
            ("region", "string", "dimension"),
            ("drug_focus", "string", "dimension"),
            ("tenure_years", "integer", "measure"),
            ("total_visits", "integer", "measure"),
            ("total_rx_generated", "integer", "measure"),
            ("visit_intensity", "real", "measure"),
            ("efficiency_ratio", "real", "measure"),
            ("performance_quadrant", "string", "dimension"),
            ("region_rank", "integer", "measure"),
            ("overall_rank", "integer", "measure"),
            ("mpi_score", "real", "measure"),
            ("territory_cluster", "string", "dimension"),
        ],
    },
    {
        "id": "hcp_coverage",
        "caption": "HCP Coverage",
        "file": "tableau_hcp_coverage.csv",
        "columns": [
            ("hcp_id", "integer", "dimension"),
            ("hcp_name", "string", "dimension"),
            ("city", "string", "dimension"),
            ("specialty", "string", "dimension"),
            ("loyalty_tier", "string", "dimension"),
            ("potential_score", "integer", "measure"),
            ("visits_per_month", "real", "measure"),
            ("post_visit_rx_lift_pct", "real", "measure"),
            ("priority_bucket", "string", "dimension"),
            ("coverage_flag", "string", "dimension"),
            ("assigned_rep_id", "integer", "dimension"),
            ("assigned_rep_name", "string", "dimension"),
        ],
    },
    {
        "id": "territory_summary",
        "caption": "Territory Summary",
        "file": "tableau_territory_summary.csv",
        "columns": [
            ("city_name", "string", "dimension"),
            ("region", "string", "dimension"),
            ("tier", "string", "dimension"),
            ("population_millions", "real", "measure"),
            ("specialist_count", "integer", "measure"),
            ("disease_prevalence_index", "integer", "measure"),
            ("mpi_score", "real", "measure"),
            ("avg_visit_intensity", "real", "measure"),
            ("avg_efficiency_ratio", "real", "measure"),
            ("territory_cluster", "string", "dimension"),
            ("num_reps_assigned", "integer", "measure"),
            ("total_rx_volume", "integer", "measure"),
            ("rx_per_rep", "real", "measure"),
            ("latitude", "real", "measure", "Latitude"),
            ("longitude", "real", "measure", "Longitude"),
        ],
    },
    {
        "id": "rx_trends",
        "caption": "Rx Trends",
        "file": "tableau_rx_trends.csv",
        "columns": [
            ("rep_id", "integer", "dimension"),
            ("rep_name", "string", "dimension"),
            ("region", "string", "dimension"),
            ("city", "string", "dimension"),
            ("month_year", "string", "dimension"),
            ("monthly_rx", "integer", "measure"),
            ("rolling_3m_avg_rx", "real", "measure"),
            ("efficiency_ratio", "real", "measure"),
            ("performance_quadrant", "string", "dimension"),
        ],
    },
    {
        "id": "visit_distribution",
        "caption": "Visit Distribution",
        "file": "tableau_visit_distribution.csv",
        "columns": [
            ("priority_bucket", "string", "dimension"),
            ("state", "string", "dimension"),
            ("visit_share_pct", "real", "measure"),
            ("rx_yield_per_visit", "real", "measure"),
            ("wasted_effort_flag", "boolean", "dimension"),
        ],
    },
]

# Mapping from our datatype labels to the local-type that Tableau uses on
# <column> elements at the datasource level. (At the relation/columns level,
# the "datatype" attribute is used directly.)
LOCAL_TYPE = {
    "integer": "integer",
    "real": "real",
    "string": "string",
    "boolean": "boolean",
}

# Aggregation default for measures
AGG_DEFAULT = {
    "integer": "sum",
    "real": "sum",
    "string": "count",
    "boolean": "count",
}


# ============================================================================
# XML BUILDERS
# ============================================================================

def build_datasource_element(spec, conn_index):
    """
    Build a single <datasource> element for one CSV.
    Uses class='textscan' (Tableau's CSV connector).
    """
    ds_name = f"federated.{spec['id']}"
    text_conn_name = f"textscan.{spec['id']}"

    ds = ET.Element("datasource", {
        "caption": spec["caption"],
        "inline": "true",
        "name": ds_name,
        "version": "18.1",
    })

    # ---- <connection class='federated'>
    conn = ET.SubElement(ds, "connection", {"class": "federated"})

    named_conns = ET.SubElement(conn, "named-connections")
    nc = ET.SubElement(named_conns, "named-connection", {
        "caption": spec["file"].replace(".csv", ""),
        "name": text_conn_name,
    })
    ET.SubElement(nc, "connection", {
        "class": "textscan",
        "directory": "Data/Datasources",
        "filename": spec["file"],
        "password": "",
        "server": "",
    })

    # ---- <relation> describing the table
    table_token = f"[{spec['file'].replace('.csv', '')}#csv]"
    relation = ET.SubElement(conn, "relation", {
        "connection": text_conn_name,
        "name": spec["file"],
        "table": table_token,
        "type": "table",
    })
    cols_el = ET.SubElement(relation, "columns", {
        "header": "yes",
        "outcome": "6",  # 6 = headers parsed
    })
    for ordinal, col in enumerate(spec["columns"]):
        name, dtype = col[0], col[1]
        ET.SubElement(cols_el, "column", {
            "datatype": dtype,
            "name": name,
            "ordinal": str(ordinal),
        })

    # ---- <aliases enabled='yes'/>
    ET.SubElement(ds, "aliases", {"enabled": "yes"})

    # ---- <column> elements at datasource level (where role + geo role live)
    for col in spec["columns"]:
        name, dtype, role = col[0], col[1], col[2]
        geo_role = col[3] if len(col) > 3 else None

        attrs = {
            "datatype": dtype,
            "name": f"[{name}]",
            "role": role,
            "type": "nominal" if role == "dimension" else "quantitative",
        }
        if role == "measure" and dtype in ("integer", "real"):
            attrs["aggregation"] = "Sum"

        col_el = ET.SubElement(ds, "column", attrs)

        if geo_role:
            # Tableau encodes geo role via a semantic-role attribute on the
            # column. The exact encoding is `[Country].[<Role>]` for built-in
            # roles like Latitude/Longitude.
            col_el.set("semantic-role", f"[Country].[{geo_role}]")

    return ds


def build_worksheet_element(spec):
    """
    Build a minimal empty <worksheet> bound to one data source.
    This gives the user a starter sheet per source rather than a blank workbook.
    """
    ws_name = spec["caption"]
    ds_name = f"federated.{spec['id']}"

    ws = ET.Element("worksheet", {"name": ws_name})
    table = ET.SubElement(ws, "table")
    view = ET.SubElement(table, "view")

    datasources = ET.SubElement(view, "datasources")
    ET.SubElement(datasources, "datasource", {
        "caption": spec["caption"],
        "name": ds_name,
    })

    ET.SubElement(view, "aggregation", {"value": "true"})

    ET.SubElement(table, "style")
    panes = ET.SubElement(table, "panes")
    pane = ET.SubElement(panes, "pane")
    ET.SubElement(pane, "view")
    ET.SubElement(pane, "mark", {"class": "Automatic"})

    ET.SubElement(table, "rows")
    ET.SubElement(table, "cols")
    return ws


def build_workbook_xml():
    """Build the full <workbook> XML tree."""
    wb = ET.Element("workbook", {
        "source-build": "2026.1.1",
        "source-platform": "mac",
        "version": "18.1",
    })
    # The xmlns:user="..." attribute is injected as a string post-serialize
    # in prettify() — ElementTree's namespace handling is too painful here.

    prefs = ET.SubElement(wb, "preferences")
    ET.SubElement(prefs, "preference", {
        "name": "ui.encoding.shelf.height",
        "value": "250",
    })

    datasources = ET.SubElement(wb, "datasources")
    for i, spec in enumerate(DATASOURCES):
        datasources.append(build_datasource_element(spec, i))

    worksheets = ET.SubElement(wb, "worksheets")
    for spec in DATASOURCES:
        worksheets.append(build_worksheet_element(spec))

    # <windows> block — Tableau wants at least a minimal one
    windows = ET.SubElement(wb, "windows", {"source-height": "30"})
    for spec in DATASOURCES:
        win = ET.SubElement(windows, "window", {
            "class": "worksheet",
            "maximized": "true",
            "name": spec["caption"],
        })
        ET.SubElement(win, "viewpoint")

    return wb


def prettify(elem):
    """Return a pretty-printed XML string with declaration + xmlns fix."""
    rough = ET.tostring(elem, encoding="utf-8")
    parsed = minidom.parseString(rough)
    pretty = parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")

    # Fix the user xmlns: ElementTree mangles it. Inject it cleanly on root.
    pretty = pretty.replace(
        '<workbook ',
        '<workbook xmlns:user="http://www.tableausoftware.com/xml/user" ',
        1,
    )
    # Strip the namespaced attribute artifact ElementTree may have added
    pretty = pretty.replace(
        ' xmlns:ns0="http://www.w3.org/2000/xmlns/" ns0:user="http://www.tableausoftware.com/xml/user"',
        "",
    )
    return pretty


# ============================================================================
# PACKAGING
# ============================================================================

def build_twbx():
    if not os.path.isdir(TABLEAU_DIR):
        raise SystemExit(f"Tableau dir not found: {TABLEAU_DIR}")

    # Verify all CSVs present
    for spec in DATASOURCES:
        csv_path = os.path.join(TABLEAU_DIR, spec["file"])
        if not os.path.isfile(csv_path):
            raise SystemExit(f"Missing CSV: {csv_path}")

    # Build XML
    wb_root = build_workbook_xml()
    twb_xml = prettify(wb_root)

    # Stage in a temp dir
    with tempfile.TemporaryDirectory() as tmp:
        twb_path = os.path.join(tmp, "novamed_sfe.twb")
        data_dir = os.path.join(tmp, "Data", "Datasources")
        os.makedirs(data_dir, exist_ok=True)

        with open(twb_path, "w", encoding="utf-8") as f:
            f.write(twb_xml)

        for spec in DATASOURCES:
            src = os.path.join(TABLEAU_DIR, spec["file"])
            dst = os.path.join(data_dir, spec["file"])
            shutil.copyfile(src, dst)

        # Zip into .twbx (just a zip file with a specific layout)
        if os.path.exists(OUTPUT_TWBX):
            os.remove(OUTPUT_TWBX)

        with zipfile.ZipFile(OUTPUT_TWBX, "w", zipfile.ZIP_DEFLATED) as zf:
            # .twb at root
            zf.write(twb_path, arcname="novamed_sfe.twb")
            # Data files
            for spec in DATASOURCES:
                arcname = os.path.join("Data", "Datasources", spec["file"])
                zf.write(os.path.join(data_dir, spec["file"]), arcname=arcname)

    size_kb = os.path.getsize(OUTPUT_TWBX) / 1024
    print(f"[OK] Wrote {OUTPUT_TWBX} ({size_kb:.1f} KB)")
    print(f"     - {len(DATASOURCES)} data sources, "
          f"{sum(len(d['columns']) for d in DATASOURCES)} columns total")
    print(f"     - {len(DATASOURCES)} starter worksheets")
    print()
    print("Next steps:")
    print("  1. Double-click novamed_sfe.twbx to open in Tableau Desktop 2026.1")
    print("  2. Verify the 5 data sources appear in the Data pane")
    print("  3. Build sheets following outputs/tableau/TABLEAU_BUILD_GUIDE.md")
    print("  4. Server -> Tableau Public -> Save to Tableau Public")


if __name__ == "__main__":
    build_twbx()
