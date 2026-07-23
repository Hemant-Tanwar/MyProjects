"""
Celonis Knowledge Base
========================
Comprehensive reference of:
  - All valid Celonis Analysis SHEET TEMPLATE TYPES (Case Explorer, Process Explorer, etc.)
  - All valid Celonis Analysis COMPONENT TYPES (pql-table, single-kpi, dropdown, etc.)
  - PQL formula templates, KPI definitions, layout patterns, and component builders.
  - build_3_sheet_analysis() — creates a beautiful 3-sheet analysis automatically.

Referenced by the Analysis Agent when generating analysis configurations.
"""

# ============================================================
# SECTION 1: VALID CELONIS ANALYSIS COMPONENT TYPES
# ============================================================
# These are the valid type strings accepted by the Celonis Analysis API
# (stored in the serialized_content.draft.document.components list).
#
# pycelonis ComponentFactory handles dispatch for typed classes:
#   pql-table   -> PQLTable      (axis0, axis1, axis2)
#   single-kpi  -> SingleKPI     (formula)
#   pivot       -> PivotTable    (axis0, axis1, axis2)
#   boxplot     -> Boxplot       (dimension, distribution)
#   world-map   -> WorldMap      (formula, kpiFormula, tooltipFormula)
#
# All others (including "process-explorer", "dropdown") are handled as
# generic AnalysisComponent (Extra.allow) — they are stored verbatim in
# the JSON document. The Celonis frontend renders them if the JSON
# structure matches what it expects.
#
# PROCESS EXPLORER NOTES:
#   - type: "process-explorer"
#   - Must include: eventLogs: [{"eventLog": "<event_log_table_name>"}]
#   - The event_log_table_name must match an event log defined in the
#     Knowledge Model's eventLogsMetadata section.
#   - Recommended size: w=12, h=8 (full width, tall)
#
VALID_CELONIS_COMPONENT_TYPES = {
    "process-explorer": {
        "description": "Celonis Process Explorer — visualizes process variant flows, happy paths, and bottlenecks. ALWAYS include this as the main centerpiece of an analysis.",
        "required_fields": ["eventLogs"],
        "optional_fields": ["title", "x", "y", "w", "h"],
        "event_logs_format": [{"eventLog": "<event_log_table_name_from_KM>"}],
        "recommended_size": {"w": 12, "h": 8},
        "placement": "Center section — below KPI cards, full width",
        "notes": "event_log_table_name must match eventLogsMetadata.eventLogs[].id in the Knowledge Model",
        "example_json": {
            "id": "process-explorer-main",
            "type": "process-explorer",
            "title": "Process Variant Flow",
            "eventLogs": [{"eventLog": "TEMP_P2P_EVENT_LOG"}],
            "x": 0, "y": 3, "w": 12, "h": 8,
            "width": 12, "height": 8,
            "layout": {"x": 0, "y": 3, "w": 12, "h": 8, "width": 12, "height": 8},
            "position": {"x": 0, "y": 3, "w": 12, "h": 8, "width": 12, "height": 8}
        }
    },
    "pql-table": {
        "description": "OLAP Table, Column Chart, Line Chart, Pie Chart, Bar Chart — any PQL-driven data visualization with rows and columns",
        "required_fields": ["axis0", "axis1", "axis2"],
        "optional_fields": ["distinct", "title", "componentFilter", "limitMode", "showOthers"],
        "axis_description": {
            "axis0": "Dimensions/rows (e.g., case attributes, activity names) — each entry: {name, text, sorting, sortingIndex}",
            "axis1": "KPI measure columns (e.g., COUNT, SUM, AVG) — each entry: {name, text, sorting, sortingIndex}",
            "axis2": "Secondary grouping / color dimension — each entry: {name, text}"
        },
        "recommended_size": {"w": 12, "h": 6},
        "placement": "Below process-explorer or as secondary analysis sheets",
        "example_json": {
            "id": "table-activity-frequency",
            "type": "pql-table",
            "title": "Activity Frequency",
            "distinct": False,
            "limitMode": "LIMIT",
            "showOthers": False,
            "axis0": [{"name": "Activity", "text": "TEMP_P2P_EVENT_LOG.ACTIVITY", "sorting": None, "sortingIndex": None}],
            "axis1": [
                {"name": "Occurrence Count", "text": "COUNT(TEMP_P2P_EVENT_LOG.ACTIVITY)", "sorting": "DESC", "sortingIndex": 0},
                {"name": "Affected Cases", "text": "COUNT_DISTINCT(TEMP_P2P_EVENT_LOG.CASE_KEY)", "sorting": None, "sortingIndex": None}
            ],
            "axis2": []
        }
    },
    "single-kpi": {
        "description": "Single KPI metric card — displays a single aggregated scalar (number, fill bar, radial gauge, tile)",
        "required_fields": ["formula"],
        "optional_fields": ["title", "componentFilter", "version"],
        "formula_description": {
            "name": "Display name shown in the KPI card",
            "text": "PQL formula returning a single scalar value (AVG, SUM, COUNT, CALC_THROUGHPUT, etc.)"
        },
        "recommended_size": {"w": 4, "h": 3},
        "placement": "Top strip — 3 per row in the 12-column grid (x=0,4,8)",
        "notes": "Use h=3 for large KPI tiles that are easy to read at a glance",
        "example_json": {
            "id": "kpi-throughput",
            "type": "single-kpi",
            "title": "Avg Throughput Time",
            "version": 1,
            "formula": {
                "name": "Avg Throughput Time",
                "text": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Create PO Item'] TO LAST_OCCURRENCE['Receive Goods'], EVENTTIME('_cel_event_log')))"
            }
        }
    },
    "pivot": {
        "description": "Pivot Table — cross-tabulation of dimensions (rows) and KPIs (columns) with optional color grouping",
        "required_fields": ["axis0", "axis1", "axis2"],
        "recommended_size": {"w": 12, "h": 6},
        "example_json": {
            "id": "pivot-vendor-summary",
            "type": "pivot",
            "title": "Vendor Spend Summary",
            "axis0": [{"name": "Vendor Country", "text": "LFA1.LAND1"}],
            "axis1": [{"name": "Total Spend", "text": "SUM(TEMP_P2P_CASES.PO_AMOUNT)"}],
            "axis2": [{"name": "Year", "text": "YEAR(EKKO.BEDAT)"}]
        }
    },
    "boxplot": {
        "description": "Box Plot Chart — statistical distribution visualization (min, Q1, median, Q3, max)",
        "required_fields": ["dimension", "distribution"],
        "recommended_size": {"w": 6, "h": 6},
        "example_json": {
            "id": "boxplot-throughput-dist",
            "type": "boxplot",
            "title": "Throughput Time Distribution by Vendor",
            "dimension": {"name": "Vendor Country", "text": "LFA1.LAND1"},
            "distribution": {"name": "Throughput Days", "text": "CALC_THROUGHPUT(FIRST_OCCURRENCE['Create PO Item'] TO LAST_OCCURRENCE['Receive Goods'], REMAP_TIMESTAMPS(TEMP_P2P_EVENT_LOG.EVENTTIME, DAYS))"}
        }
    },
    "world-map": {
        "description": "World Map Chart — geographic distribution using country codes. Great for vendor/customer geographic analysis.",
        "required_fields": ["formula", "kpiFormula", "tooltipFormula"],
        "recommended_size": {"w": 6, "h": 6},
        "example_json": {
            "id": "worldmap-vendor-spend",
            "type": "world-map",
            "title": "PO Spend by Country",
            "formula": {"name": "Vendor Country", "text": "LFA1.LAND1"},
            "kpiFormula": {"name": "Total Spend", "text": "SUM(TEMP_P2P_CASES.PO_AMOUNT)"},
            "tooltipFormula": {"name": "PO Count", "text": "COUNT(TEMP_P2P_CASES.CASE_KEY)"}
        }
    },
    "dropdown": {
        "description": "Filter Dropdown — user-controlled filter bar component using PQL FILTER statements",
        "required_fields": ["filter"],
        "optional_fields": ["title"],
        "filter_description": {
            "name": "Display name for the filter",
            "text": "PQL FILTER statement (must end with semicolon)"
        },
        "recommended_size": {"w": 4, "h": 1},
        "placement": "Top strip — up to 3 per row as a filter bar, or bottom of sheet",
        "example_json": {
            "id": "filter-maverick-buying",
            "type": "dropdown",
            "title": "Maverick Buying Cases",
            "filter": {
                "name": "Maverick Buying Cases",
                "text": "FILTER PROCESS OCCURRENCE 'Receive Invoice' BEFORE 'Create Purchase Order Item';"
            }
        }
    }
}


# ============================================================
# SECTION 2: RECOMMENDED ANALYSIS LAYOUT TEMPLATES
# ============================================================
# Celonis uses a 12-column grid layout. All components need x, y, w, h.
#
# BEAUTIFUL LAYOUT PATTERN (Celonis Studio Style):
# ┌─────────────────────────────────────────────────────────────────┐
# │ Filter Bar    [Dropdown 1] [Dropdown 2] [Dropdown 3]    Row y=0 │  h=1
# ├──────────────────┬──────────────────┬──────────────────────────-┤
# │  KPI Card 1      │  KPI Card 2      │  KPI Card 3       Row y=1 │  h=3
# │  w=4             │  w=4             │  w=4                       │
# ├──────────────────┴──────────────────┴────────────────────────---┤
# │  Process Explorer (full width)                          Row y=4 │  h=8
# │  w=12                                                           │
# ├─────────────────────────────────────────────────────────────────┤
# │  Activity Frequency Table (full width)                 Row y=12 │  h=6
# │  w=12                                                           │
# └─────────────────────────────────────────────────────────────────┘
#
# GRID RULES:
#   - 12 columns total
#   - x: column start (0=leftmost)
#   - y: row start (0=topmost)
#   - w: width in columns
#   - h: height in grid units

GRID_LAYOUT_SCHEMA = {
    "total_columns": 12,
    "recommended_row_heights": {
        "filter_bar": 1,
        "kpi_card": 3,
        "process_explorer": 8,
        "analysis_table": 6,
        "chart_half_width": 6
    },
    "layout_template": {
        "row_0_filters": "y=0, h=1 — Filter dropdowns (w=4 each, up to 3 per row)",
        "row_1_kpis":    "y=1, h=3 — KPI tiles (w=4 each, 3 per row for 12-col grid)",
        "row_4_process_explorer": "y=4, h=8 — Process Explorer full width (w=12)",
        "row_12_table":  "y=12, h=6 — Activity/data tables (w=12)"
    }
}


# ============================================================
# SECTION 3: PQL FORMULA REFERENCE
# ============================================================

PQL_FUNCTIONS = {
    # --- Aggregation ---
    "COUNT":            {"syntax": "COUNT(table.column)",               "example": "COUNT(TEMP_P2P_CASES.CASE_KEY)"},
    "COUNT_DISTINCT":   {"syntax": "COUNT_DISTINCT(table.column)",      "example": "COUNT_DISTINCT(TEMP_P2P_EVENT_LOG.CASE_KEY)"},
    "COUNT_TABLE":      {"syntax": "COUNT_TABLE(table)",                "example": "COUNT_TABLE(TEMP_P2P_CASES)"},
    "SUM":              {"syntax": "SUM(table.column)",                 "example": "SUM(TEMP_P2P_CASES.PO_AMOUNT)"},
    "AVG":              {"syntax": "AVG(table.column)",                 "example": "AVG(TEMP_P2P_CASES.PO_AMOUNT)"},
    "MIN":              {"syntax": "MIN(table.column)",                 "example": "MIN(TEMP_P2P_CASES.PO_AMOUNT)"},
    "MAX":              {"syntax": "MAX(table.column)",                 "example": "MAX(TEMP_P2P_CASES.PO_AMOUNT)"},
    "MEDIAN":           {"syntax": "MEDIAN(table.column)",              "example": "MEDIAN(TEMP_P2P_CASES.PO_AMOUNT)"},
    # --- Process Time ---
    "CALC_THROUGHPUT":  {
        "syntax": "CALC_THROUGHPUT(FIRST_OCCURRENCE['A'] TO LAST_OCCURRENCE['B'], EVENTTIME('_cel_event_log'))",
        "example": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Create PO Item'] TO LAST_OCCURRENCE['Receive Goods'], EVENTTIME('_cel_event_log')))",
        "units": ["DAYS", "HOURS", "MINUTES"],
        "note": "Also works with REMAP_TIMESTAMPS(event_log.EVENTTIME, DAYS)"
    },
    "REMAP_TIMESTAMPS": {"syntax": "REMAP_TIMESTAMPS(table.timestamp_col, DAYS)", "example": "REMAP_TIMESTAMPS(TEMP_P2P_EVENT_LOG.EVENTTIME, DAYS)"},
    "EVENTTIME":        {"syntax": "EVENTTIME('_cel_event_log')",       "example": "CALC_THROUGHPUT(... , EVENTTIME('_cel_event_log'))"},
    "FIRST_OCCURRENCE": {"syntax": "FIRST_OCCURRENCE['Activity Name']", "example": "FIRST_OCCURRENCE['Create Purchase Order Item']"},
    "LAST_OCCURRENCE":  {"syntax": "LAST_OCCURRENCE['Activity Name']",  "example": "LAST_OCCURRENCE['Receive Goods']"},
    "OCCURRENCE_COUNT": {"syntax": "OCCURRENCE_COUNT('Activity Name')", "example": "AVG(OCCURRENCE_COUNT('Approve Purchase Order'))"},
    # --- Pull-Up ---
    "PU_COUNT":         {"syntax": "PU_COUNT(target_table, source.col)",          "example": "PU_COUNT(EKKO, EKPO.EBELP)"},
    "PU_COUNT_DISTINCT":{"syntax": "PU_COUNT_DISTINCT(target_table, source.col)", "example": "PU_COUNT_DISTINCT(EKKO, EKPO.WERKS)"},
    "PU_SUM":           {"syntax": "PU_SUM(target_table, source.numeric_col)",    "example": "PU_SUM(EKKO, EKPO.NETPR)"},
    "PU_AVG":           {"syntax": "PU_AVG(target_table, source.numeric_col)",    "example": "PU_AVG(EKKO, EKPO.NETPR)"},
    "PU_MAX":           {"syntax": "PU_MAX(target_table, source.numeric_col)",    "example": "PU_MAX(EKKO, EKPO.NETPR)"},
    "PU_MIN":           {"syntax": "PU_MIN(target_table, source.numeric_col)",    "example": "PU_MIN(EKKO, EKPO.NETPR)"},
    # --- Conditional ---
    "CASE_WHEN":        {"syntax": "CASE WHEN cond THEN val [ELSE default] END",  "example": "CASE WHEN PO_AMOUNT > 10000 THEN 'High' ELSE 'Standard' END"},
    # --- Date/Time ---
    "YEAR":             {"syntax": "YEAR(table.date_col)",  "example": "YEAR(EKKO.BEDAT)"},
    "MONTH":            {"syntax": "MONTH(table.date_col)", "example": "MONTH(EKKO.BEDAT)"},
    "QUARTER":          {"syntax": "QUARTER(table.date_col)", "example": "QUARTER(EKKO.BEDAT)"},
    # --- String ---
    "CONCAT":           {"syntax": "CONCAT(val1, val2, ...)", "example": "CONCAT(EKKO.EBELN, '-', EKPO.EBELP)"},
    "UPPER":            {"syntax": "UPPER(table.col)", "example": "UPPER(LFA1.LAND1)"},
}


# ============================================================
# SECTION 4: FILTER EXPRESSION TEMPLATES
# ============================================================

PROCESS_FILTER_TEMPLATES = {
    "P2P": {
        "MAVERICK_BUYING":            "FILTER PROCESS OCCURRENCE 'Receive Invoice' BEFORE 'Create Purchase Order Item';",
        "GOODS_RECEIPT_BEFORE_INVOICE":"FILTER PROCESS OCCURRENCE 'Receive Goods' BEFORE 'Receive Invoice';",
        "SKIP_GR":                    "FILTER NOT PROCESS OCCURRENCE['Receive Goods'];",
        "LATE_GR_OVER_30_DAYS":       "FILTER CALC_THROUGHPUT(FIRST_OCCURRENCE['Create Purchase Order Item'] TO FIRST_OCCURRENCE['Receive Goods'], REMAP_TIMESTAMPS({event_log_table}.EVENTTIME, DAYS)) > 30;",
        "AUTOMATED_CASES":            "FILTER PU_COUNT({case_table}, {event_log_table}.ACTIVITY, {event_log_table}.USER_NAME = 'SYSTEM') = PU_COUNT({case_table}, {event_log_table}.ACTIVITY);",
        "HIGH_VALUE_PO":              "FILTER {case_table}.PO_AMOUNT > 10000;",
        "PROCESS_VIOLATIONS":         "FILTER PROCESS OCCURRENCE 'Approve Purchase Order' BEFORE 'Create Purchase Order Item';",
        "REWORK_CASES":               "FILTER PU_COUNT({case_table}, {event_log_table}.ACTIVITY) > PU_COUNT_DISTINCT({case_table}, {event_log_table}.ACTIVITY);"
    },
    "O2C": {
        "LATE_DELIVERY":              "FILTER PROCESS OCCURRENCE 'Ship Goods' AFTER 'Create Invoice';",
        "BLOCKED_ORDERS":             "FILTER PROCESS OCCURRENCE['Credit Block Delivery'];",
        "RETURNS":                    "FILTER PROCESS OCCURRENCE['Create Returns Order'];",
        "TOUCHLESS_ORDERS":           "FILTER PU_COUNT({case_table}, {event_log_table}.ACTIVITY, {event_log_table}.USER_NAME = 'SYSTEM') = PU_COUNT({case_table}, {event_log_table}.ACTIVITY);",
        "HIGH_VALUE_SO":              "FILTER {case_table}.SO_AMOUNT > 20000;",
        "REWORK_CASES":               "FILTER PU_COUNT({case_table}, {event_log_table}.ACTIVITY) > PU_COUNT_DISTINCT({case_table}, {event_log_table}.ACTIVITY);"
    },
    "GENERIC": {
        "REWORK_CASES":               "FILTER PU_COUNT({case_table}, {event_log_table}.ACTIVITY) > PU_COUNT_DISTINCT({case_table}, {event_log_table}.ACTIVITY);",
        "AUTOMATED_CASES":            "FILTER PU_COUNT({case_table}, {event_log_table}.ACTIVITY, {event_log_table}.USER_NAME = 'SYSTEM') = PU_COUNT({case_table}, {event_log_table}.ACTIVITY);"
    }
}


# ============================================================
# SECTION 5: KPI CATALOG BY PROCESS TYPE
# ============================================================

KPI_CATALOG = {
    "P2P": [
        {
            "id": "THROUGHPUT_TIME_PO_TO_GR",
            "name": "PO to Goods Receipt Throughput",
            "description": "Average elapsed time from PO item creation to goods receipt",
            "unit": "Days",
            "formula": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Create Purchase Order Item'] TO LAST_OCCURRENCE['Receive Goods'], EVENTTIME('_cel_event_log')))",
            "component_type": "single-kpi",
            "good_value": "lower is better"
        },
        {
            "id": "AUTOMATION_RATE",
            "name": "Automation Rate (Touchless PO)",
            "description": "% of PO items processed fully automatically (SYSTEM user only)",
            "unit": "%",
            "formula": "COUNT(CASE WHEN PU_COUNT({case_table}, {event_log_table}.ACTIVITY, {event_log_table}.USER_NAME = 'SYSTEM') = PU_COUNT({case_table}, {event_log_table}.ACTIVITY) THEN {case_table}.{case_col} END) / COUNT({case_table}.{case_col}) * 100.0",
            "component_type": "single-kpi",
            "good_value": "higher is better"
        },
        {
            "id": "TOTAL_PO_VALUE",
            "name": "Total PO Spend",
            "description": "Total net value of all purchase orders",
            "unit": "EUR",
            "formula": "SUM({case_table}.PO_AMOUNT)",
            "component_type": "single-kpi",
            "good_value": "informational"
        },
        {
            "id": "CASE_COUNT",
            "name": "Number of PO Cases",
            "description": "Total count of PO items in scope",
            "unit": "Count",
            "formula": "COUNT({case_table}.{case_col})",
            "component_type": "single-kpi",
            "good_value": "informational"
        },
        {
            "id": "MAVERICK_BUYING_RATE",
            "name": "Maverick Buying Rate",
            "description": "% of cases where invoice received before PO creation",
            "unit": "%",
            "formula": "COUNT(CASE WHEN PROCESS OCCURRENCE 'Receive Invoice' BEFORE 'Create Purchase Order Item' THEN {case_table}.{case_col} END) / COUNT({case_table}.{case_col}) * 100.0",
            "component_type": "single-kpi",
            "good_value": "lower is better"
        },
        {
            "id": "THREE_WAY_MATCH_RATE",
            "name": "3-Way Match Rate",
            "description": "% of POs with PO + GR + Invoice all matched",
            "unit": "%",
            "formula": "COUNT(CASE WHEN PROCESS OCCURRENCE['Create Purchase Order Item'] AND PROCESS OCCURRENCE['Receive Goods'] AND PROCESS OCCURRENCE['Receive Invoice'] THEN {case_table}.{case_col} END) / COUNT({case_table}.{case_col}) * 100.0",
            "component_type": "single-kpi",
            "good_value": "higher is better"
        },
        {
            "id": "AVG_PO_VALUE",
            "name": "Avg PO Item Value",
            "description": "Average net value per PO line item",
            "unit": "EUR",
            "formula": "AVG({case_table}.PO_AMOUNT)",
            "component_type": "single-kpi",
            "good_value": "informational"
        },
        {
            "id": "ACTIVITY_FREQUENCY_TABLE",
            "name": "Process Activity Frequency",
            "description": "Table showing activity occurrences and impacted cases — the process footprint",
            "unit": "Table",
            "axis0_columns": [{"name": "Activity", "text": "{event_log_table}.ACTIVITY"}],
            "axis1_columns": [
                {"name": "Occurrence Count", "text": "COUNT({event_log_table}.ACTIVITY)", "sorting": "DESC", "sortingIndex": 0},
                {"name": "Affected Cases", "text": "COUNT_DISTINCT({event_log_table}.{case_col})"}
            ],
            "component_type": "pql-table"
        },
        {
            "id": "VENDOR_SPEND_TABLE",
            "name": "Vendor Spend Summary",
            "description": "Vendor breakdown with spend and order volumes",
            "unit": "Table",
            "axis0_columns": [
                {"name": "Vendor Country", "text": "LFA1.LAND1"},
                {"name": "Vendor Name", "text": "LFA1.NAME1"}
            ],
            "axis1_columns": [
                {"name": "Total Spend", "text": "SUM({case_table}.PO_AMOUNT)"},
                {"name": "PO Count", "text": "COUNT({case_table}.{case_col})"},
                {"name": "Avg PO Value", "text": "AVG({case_table}.PO_AMOUNT)"}
            ],
            "component_type": "pql-table"
        }
    ],
    "O2C": [
        {
            "id": "THROUGHPUT_TIME_SO_TO_SHIP",
            "name": "SO to Shipment Throughput",
            "description": "Average elapsed time from SO creation to goods shipment",
            "unit": "Days",
            "formula": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Create Sales Order Item'] TO LAST_OCCURRENCE['Ship Goods'], EVENTTIME('_cel_event_log')))",
            "component_type": "single-kpi",
            "good_value": "lower is better"
        },
        {
            "id": "TOUCHLESS_ORDER_RATE",
            "name": "Touchless Order Rate",
            "description": "% of sales orders processed fully automatically",
            "unit": "%",
            "formula": "COUNT(CASE WHEN PU_COUNT({case_table}, {event_log_table}.ACTIVITY, {event_log_table}.USER_NAME = 'SYSTEM') = PU_COUNT({case_table}, {event_log_table}.ACTIVITY) THEN {case_table}.{case_col} END) / COUNT({case_table}.{case_col}) * 100.0",
            "component_type": "single-kpi",
            "good_value": "higher is better"
        },
        {
            "id": "TOTAL_SO_VALUE",
            "name": "Total SO Revenue",
            "description": "Sum of all sales order line item net values",
            "unit": "EUR",
            "formula": "SUM({case_table}.SO_AMOUNT)",
            "component_type": "single-kpi",
            "good_value": "informational"
        },
        {
            "id": "SO_CASE_COUNT",
            "name": "Number of SO Cases",
            "description": "Total count of sales order items in scope",
            "unit": "Count",
            "formula": "COUNT({case_table}.{case_col})",
            "component_type": "single-kpi",
            "good_value": "informational"
        },
        {
            "id": "LATE_DELIVERY_RATE",
            "name": "Late Delivery Rate",
            "description": "% of cases where shipment occurred after invoice creation",
            "unit": "%",
            "formula": "COUNT(CASE WHEN PROCESS OCCURRENCE 'Ship Goods' AFTER 'Create Invoice' THEN {case_table}.{case_col} END) / COUNT({case_table}.{case_col}) * 100.0",
            "component_type": "single-kpi",
            "good_value": "lower is better"
        },
        {
            "id": "AVG_SO_VALUE",
            "name": "Avg SO Item Value",
            "description": "Average net value per sales order line item",
            "unit": "EUR",
            "formula": "AVG({case_table}.SO_AMOUNT)",
            "component_type": "single-kpi",
            "good_value": "informational"
        },
        {
            "id": "O2C_ACTIVITY_TABLE",
            "name": "O2C Activity Frequency",
            "description": "Table showing O2C process activity occurrences",
            "unit": "Table",
            "axis0_columns": [{"name": "Activity", "text": "{event_log_table}.ACTIVITY"}],
            "axis1_columns": [
                {"name": "Occurrence Count", "text": "COUNT({event_log_table}.ACTIVITY)", "sorting": "DESC", "sortingIndex": 0},
                {"name": "Affected Cases", "text": "COUNT_DISTINCT({event_log_table}.{case_col})"}
            ],
            "component_type": "pql-table"
        }
    ],
    "GENERIC": [
        {
            "id": "REWORK_RATE",
            "name": "Rework Rate",
            "description": "% of cases with any activity repeated more than once",
            "unit": "%",
            "formula": "COUNT(CASE WHEN PU_MAX({case_table}, PU_COUNT({case_table}, {event_log_table}.ACTIVITY)) > 1 THEN {case_table}.{case_col} END) / COUNT({case_table}.{case_col}) * 100.0",
            "component_type": "single-kpi",
            "note": "Generic rework rate formula",
            "good_value": "lower is better"
        }
    ]
}


# ============================================================
# SECTION 6: COMPONENT BUILDER HELPERS
# ============================================================

def _make_layout(x: int, y: int, w: int, h: int) -> dict:
    """Build the standard Celonis layout/position sub-dict."""
    return {"x": x, "y": y, "w": w, "h": h, "width": w, "height": h}


def build_process_explorer_component(
    component_id: str,
    event_log_table: str,
    x: int = 0,
    y: int = 4,
    w: int = 12,
    h: int = 8,
    title: str = "Process Variant Flow"
) -> dict:
    """
    Build a Celonis Process Explorer component.
    
    ALWAYS include this in every analysis — it is the core process mining visualization.
    
    Args:
        component_id: Unique ID for the component
        event_log_table: Name of the event log table (must match KM eventLogsMetadata event log ID)
        x, y: Grid position (y=4 recommended to be below KPI cards)
        w, h: Grid size (w=12, h=8 recommended for full-width, tall display)
        title: Display title shown above the component
    """
    layout = _make_layout(x, y, w, h)
    return {
        "id": component_id,
        "type": "process-explorer",
        "title": title,
        "eventLogs": [{"eventLog": event_log_table}],
        "x": x, "y": y, "w": w, "h": h,
        "width": w, "height": h,
        "layout": layout.copy(),
        "position": layout.copy()
    }


def build_single_kpi_component(
    component_id: str,
    title: str,
    formula_pql: str,
    x: int,
    y: int,
    w: int = 4,
    h: int = 3
) -> dict:
    """
    Build a Celonis single-kpi metric card component.
    Recommended: h=3 for large readable tiles, 3 per row (w=4 each).
    """
    layout = _make_layout(x, y, w, h)
    return {
        "id": component_id,
        "type": "single-kpi",
        "title": title,
        "formula": {"name": title, "text": formula_pql},
        "version": 1,
        "x": x, "y": y, "w": w, "h": h,
        "width": w, "height": h,
        "layout": layout.copy(),
        "position": layout.copy()
    }


def build_pql_table_component(
    component_id: str,
    title: str,
    axis0_cols: list,
    axis1_cols: list,
    x: int,
    y: int,
    w: int = 12,
    h: int = 6,
    axis2_cols: list = None
) -> dict:
    """
    Build a Celonis pql-table (OLAP Table / Chart) component.
    
    axis0_cols: list of {"name": str, "text": str, "sorting": None, "sortingIndex": None}
    axis1_cols: list of {"name": str, "text": str, "sorting": "DESC"|"ASC"|None, "sortingIndex": int|None}
    """
    layout = _make_layout(x, y, w, h)
    axis2_cols = axis2_cols or []
    return {
        "id": component_id,
        "type": "pql-table",
        "title": title,
        "distinct": False,
        "limitMode": "LIMIT",
        "showOthers": False,
        "axis0": axis0_cols,
        "axis1": axis1_cols,
        "axis2": axis2_cols,
        "x": x, "y": y, "w": w, "h": h,
        "width": w, "height": h,
        "layout": layout.copy(),
        "position": layout.copy()
    }


def build_dropdown_filter_component(
    component_id: str,
    title: str,
    filter_pql: str,
    x: int,
    y: int,
    w: int = 4,
    h: int = 1
) -> dict:
    """Build a Celonis dropdown filter component."""
    layout = _make_layout(x, y, w, h)
    return {
        "id": component_id,
        "type": "dropdown",
        "title": title,
        "filter": {"name": title, "text": filter_pql},
        "x": x, "y": y, "w": w, "h": h,
        "width": w, "height": h,
        "layout": layout.copy(),
        "position": layout.copy()
    }


# ============================================================
# SECTION 7: CELONIS SHEET TEMPLATE TYPES
# ============================================================
# Celonis Analysis supports multiple SHEET-LEVEL templates.
# These are set via the 'type' field on the sheet object itself
# (different from component types inside a sheet).
#
# The user-facing "Add new sheet" dialog shows these as tiles.
# Each sheet template auto-configures the expected visual components.
#
# VERIFIED SHEET TYPE STRINGS (tested against live Celonis API):
#
#  "case-explorer"      -> Case Explorer sheet: Inspect individual cases,
#                          drill into case timeline and attributes
#  "process-explorer"   -> Process Explorer sheet: Visualize process variant
#                          flows, frequencies, and happy paths
#  "process-overview"   -> Process Overview sheet: Main KPI insights
#                          overview (throughput, automation, etc.)
#  (no type / omit key) -> New Sheet: blank custom sheet for manual layout
#
# PREMIUM-ONLY (requires Process Intelligence license — do NOT create):
#  "process-ai"         -> Process AI: Deviations from most common path
#  "conformance"        -> Conformance: Compare against BPMN target model
#  "social"             -> Social: Team collaboration analysis
#
# 4-SHEET LAYOUT (user requirement):
#   Sheet 1: Case Explorer     (type="case-explorer")     -> browse cases
#   Sheet 2: Process Explorer  (type="process-explorer")  -> variant flow
#   Sheet 3: Process Overview  (type="process-overview")  -> process KPIs
#   Sheet 4: KPI & Analytics   (no type)                  -> custom KPIs, filters, tables
#
CELONIS_SHEET_TEMPLATE_TYPES = {
    "case-explorer": {
        "display_name": "Case Explorer",
        "description": "Inspect individual cases — browse case timelines, attributes, and activity sequences",
        "sheet_type_string": "case-explorer",
        "internal_components": "Celonis auto-populates with case drill-down components. No manual components needed.",
        "sheet_position": 1,
        "example_sheet_json": {
            "id": "sheet-case-explorer",
            "name": "Case Explorer",
            "type": "case-explorer",
            "format": "FULLSCREEN",
            "sheetFilter": {},
            "position": {"top": 0, "left": 0, "width": 1200, "height": 800},
            "components": []
        }
    },
    "process-explorer": {
        "display_name": "Process Explorer",
        "description": "Visualize process variant flows, frequencies, and happy paths — the core process mining view",
        "sheet_type_string": "process-explorer",
        "internal_components": "Include a process-explorer component (full width w=12, h=12) referencing the event log.",
        "sheet_position": 2,
        "example_sheet_json": {
            "id": "sheet-process-explorer",
            "name": "Process Explorer",
            "type": "process-explorer",
            "format": "FULLSCREEN",
            "sheetFilter": {},
            "position": {"top": 0, "left": 0, "width": 1200, "height": 800},
            "components": [
                {
                    "id": "pe-main",
                    "type": "process-explorer",
                    "title": "Process Variant Flow",
                    "eventLogs": [{"eventLog": "<EVENT_LOG_TABLE_NAME>"}],
                    "x": 0, "y": 0, "w": 12, "h": 12,
                    "width": 12, "height": 12,
                    "layout": {"x": 0, "y": 0, "w": 12, "h": 12, "width": 12, "height": 12},
                    "position": {"x": 0, "y": 0, "w": 12, "h": 12, "width": 12, "height": 12}
                }
            ]
        }
    },
    "process-overview": {
        "display_name": "Process Overview",
        "description": "Main process insights — KPI cards, throughput metrics, automation rates, and bottleneck indicators",
        "sheet_type_string": "process-overview",
        "internal_components": "Include KPI single-kpi cards and pql-table components for process metrics.",
        "sheet_position": 3,
        "example_sheet_json": {
            "id": "sheet-process-overview",
            "name": "Process Overview",
            "type": "process-overview",
            "format": "FULLSCREEN",
            "sheetFilter": {},
            "position": {"top": 0, "left": 0, "width": 1200, "height": 800},
            "components": ["<single-kpi and pql-table components here>"]
        }
    },
    "custom": {
        "display_name": "KPI & Analytics (New Sheet)",
        "description": "Custom analytics sheet — KPI tiles, dropdown filters, OLAP tables, charts, and pivot tables",
        "sheet_type_string": None,
        "internal_components": "Manually place single-kpi, pql-table, dropdown, pivot, boxplot, world-map components.",
        "sheet_position": 4,
        "example_sheet_json": {
            "id": "sheet-kpi-analytics",
            "name": "KPI & Analytics",
            "format": "FULLSCREEN",
            "sheetFilter": {},
            "position": {"top": 0, "left": 0, "width": 1200, "height": 800},
            "components": ["<any valid component types>"]
        }
    }
}


def _make_sheet(
    sheet_id: str,
    sheet_name: str,
    components: list,
    content_type: str = None,
    extra_fields: dict = None
) -> dict:
    """
    Build a Celonis Analysis sheet dict matching the real Celonis API structure.

    CRITICAL: Celonis uses 'contentType' (NOT 'type') for sheet template types.
    This was verified from a working Celonis analysis serialized_content.

    Args:
        sheet_id: Unique identifier for the sheet
        sheet_name: Display name shown as tab label in Celonis UI
        components: List of component dicts to place inside this sheet
        content_type: Celonis sheet template string:
                      'case-explorer', 'process-explorer', 'process-overview',
                      or None for a blank custom sheet
        extra_fields: Additional top-level fields to merge into the sheet dict
    """
    sheet = {
        "id": sheet_id,
        "name": sheet_name,
        "format": "FULLSCREEN",
        "position": {"top": 0, "left": 0, "width": 1200, "height": 800},
        "components": components,
        "sheetFilter": {"text": ""}
    }
    if content_type:
        sheet["contentType"] = content_type
    if extra_fields:
        sheet.update(extra_fields)
    return sheet


def build_3_sheet_analysis(
    kpi_items: list,
    filter_items: list,
    event_log_table: str,
    case_table: str,
    process_name: str = "Process",
    case_col: str = "CASE_ID"
) -> list:
    """
    Build the complete 3-sheet Celonis Analysis document.
    Structure:
      1. Case Explorer (contentType='case-explorer')
      2. Process Explorer (contentType='process-explorer')
      3. KPI & Analytics (custom sheet with widgets)
    """
    import uuid

    # ─── SHEET 1: Case Explorer ─────────────────────────────────
    sheet1 = _make_sheet(
        sheet_id=str(uuid.uuid4()),
        sheet_name="Case Explorer 1",
        components=[],
        content_type="case-explorer"
    )

    # ─── SHEET 2: Process Explorer ──────────────────────────────
    pe_extra = {
        "processExplorerComponent": {
            "id": "PROCESS_EXPLORER",
            "type": "simple_process",
            "kpiView": {
                "id": "FREQUENCY",
                "icon": "https://static.celonis.cloud/static/analysis-widget/20260528-085837-RC0/assets/widgets/analysis-widget/icons/icon-frequency.svg",
                "title": "frequency",
                "inlineKpi": "caseCount",
                "isDefaultKpi": True,
                "connectionKpi": {
                    "id": "FREQUENCY",
                    "name": "frequency",
                    "text": "",
                    "units": "",
                    "colorEnd": "#1190b6",
                    "colorStart": "#40c6ed",
                    "valueFormat": ",f"
                },
                "connectionKpis": [
                    {
                        "id": "FREQUENCY",
                        "name": "frequency",
                        "text": "",
                        "units": "",
                        "colorEnd": "#1190b6",
                        "colorStart": "#40c6ed",
                        "valueFormat": ",f"
                    }
                ]
            },
            "version": 2,
            "fullDotLayout": True,
            "preventResize": True,
            "edgeSliderState": 0,
            "nodeSliderState": 0,
            "hiddenActivities": {},
            "activityColumnRef": f"\"{event_log_table}\".\"ACTIVITY\"",
            "groupsConfigurations": [],
            "activityConfigurations": []
        }
    }
    sheet2 = _make_sheet(
        sheet_id=str(uuid.uuid4()),
        sheet_name="Process Explorer 2",
        components=[],
        content_type="process-explorer",
        extra_fields=pe_extra
    )

    # ─── SHEET 3: KPI & Analytics (Custom Sheet) ────────────────
    analytics_components = []

    # Row y=0 h=1: Filter dropdown bar (up to 3 filters)
    for i, f_item in enumerate(filter_items[:3]):
        analytics_components.append(build_dropdown_filter_component(
            component_id=f"analytics-filter-{f_item.get('id', i)}",
            title=f_item.get("displayName", f"Filter {i+1}"),
            filter_pql=f_item.get("pql", ""),
            x=(i % 3) * 4, y=0, w=4, h=1
        ))

    # Row y=1 h=3: All KPI tiles (up to 6, 3 per row)
    for i, kpi_item in enumerate(kpi_items[:6]):
        kx = (i % 3) * 4
        ky = 1 + (i // 3) * 3
        analytics_components.append(build_single_kpi_component(
            component_id=f"analytics-kpi-{kpi_item.get('id', i)}",
            title=kpi_item.get("displayName", f"KPI {i+1}"),
            formula_pql=kpi_item.get("pql", ""),
            x=kx, y=ky, w=4, h=3
        ))

    kpi_rows_4 = 1 if len(kpi_items) <= 3 else 2
    tables_start_y = 1 + kpi_rows_4 * 3

    # Activity Frequency Table (full width)
    analytics_components.append(build_pql_table_component(
        component_id="analytics-activity-table",
        title="Process Activity Frequency",
        axis0_cols=[
            {"name": "Activity", "text": f"{event_log_table}.ACTIVITY",
             "sorting": None, "sortingIndex": None}
        ],
        axis1_cols=[
            {"name": "Occurrence Count", "text": f"COUNT({event_log_table}.ACTIVITY)",
             "sorting": "DESC", "sortingIndex": 0},
            {"name": "Affected Cases",   "text": f"COUNT_DISTINCT({event_log_table}.{case_col})",
             "sorting": None, "sortingIndex": None}
        ],
        x=0, y=tables_start_y, w=12, h=6
    ))

    # Case Detail Table
    case_table_y = tables_start_y + 6
    analytics_components.append(build_pql_table_component(
        component_id="analytics-case-table",
        title="Case Detail Overview",
        axis0_cols=[
            {"name": "Case ID", "text": f"{case_table}.{case_col}",
             "sorting": None, "sortingIndex": None}
        ],
        axis1_cols=[
            {"name": "Activity Count",   "text": f"PU_COUNT({case_table}, {event_log_table}.ACTIVITY)",
             "sorting": "DESC", "sortingIndex": 0},
            {"name": "Unique Activities","text": f"PU_COUNT_DISTINCT({case_table}, {event_log_table}.ACTIVITY)",
             "sorting": None, "sortingIndex": None}
        ],
        x=0, y=case_table_y, w=6, h=6
    ))

    # Additional filters (extra filters beyond first 3)
    extra_filters = filter_items[3:]
    extra_y = case_table_y
    for i, f_item in enumerate(extra_filters):
        analytics_components.append(build_dropdown_filter_component(
            component_id=f"analytics-extra-filter-{i}",
            title=f_item.get("displayName", f"Filter {i+4}"),
            filter_pql=f_item.get("pql", ""),
            x=6 + (i % 2) * 3, y=extra_y + (i // 2), w=3, h=1
        ))

    sheet3 = _make_sheet(
        sheet_id=str(uuid.uuid4()),
        sheet_name="KPI & Analytics",
        components=analytics_components,
        content_type=None
    )

    return [sheet1, sheet2, sheet3]


def build_analysis_layout(
    kpi_items: list,
    filter_items: list,
    event_log_table: str,
    process_name: str = "Process"
) -> list:
    """
    [Legacy single-sheet layout — use build_3_sheet_analysis() instead for new analyses.]
    Build a single-sheet component list (Process Explorer + KPIs + filters + table).
    """
    components = []
    for i, f_item in enumerate(filter_items[:3]):
        components.append(build_dropdown_filter_component(
            component_id=f"filter-{f_item.get('id', f'filter-{i}')}",
            title=f_item.get("displayName", f"Filter {i+1}"),
            filter_pql=f_item.get("pql", ""),
            x=(i % 3) * 4, y=0, w=4, h=1
        ))
    extra_filters = filter_items[3:]
    kpi_row_start_y = 1
    for i, kpi_item in enumerate(kpi_items[:6]):
        kx = (i % 3) * 4
        ky = kpi_row_start_y + (i // 3) * 3
        components.append(build_single_kpi_component(
            component_id=f"kpi-{kpi_item.get('id', f'kpi-{i}')}",
            title=kpi_item.get("displayName", f"KPI {i+1}"),
            formula_pql=kpi_item.get("pql", "COUNT(TABLE.COL)"),
            x=kx, y=ky, w=4, h=3
        ))
    kpi_rows_used = (min(len(kpi_items), 6) + 2) // 3
    pe_y = kpi_row_start_y + (kpi_rows_used * 3)
    components.append(build_process_explorer_component(
        component_id="process-explorer-main",
        event_log_table=event_log_table,
        x=0, y=pe_y, w=12, h=8,
        title=f"{process_name} — Process Variant Flow"
    ))
    table_y = pe_y + 8
    components.append(build_pql_table_component(
        component_id="table-activity-frequency",
        title="Process Activity Frequency",
        axis0_cols=[{"name": "Activity", "text": f"{event_log_table}.ACTIVITY", "sorting": None, "sortingIndex": None}],
        axis1_cols=[
            {"name": "Occurrence Count", "text": f"COUNT({event_log_table}.ACTIVITY)", "sorting": "DESC", "sortingIndex": 0},
            {"name": "Affected Cases",   "text": f"COUNT_DISTINCT({event_log_table}.CASE_KEY)", "sorting": None, "sortingIndex": None}
        ],
        x=0, y=table_y, w=12, h=6
    ))
    extra_y = table_y + 6
    for i, f_item in enumerate(extra_filters):
        components.append(build_dropdown_filter_component(
            component_id=f"filter-extra-{f_item.get('id', f'f-{i}')}",
            title=f_item.get("displayName", f"Filter {i+4}"),
            filter_pql=f_item.get("pql", ""),
            x=(i % 3) * 4, y=extra_y + (i // 3), w=4, h=1
        ))
    return components


def get_kpi_catalog_text() -> str:
    """Returns formatted Knowledge Base text for AI prompt injection."""
    lines = [
        "=== CELONIS KNOWLEDGE BASE ===",
        "",
        "== CELONIS SHEET TEMPLATE TYPES ==",
        "Sheets are created in this ORDER in every analysis:",
        "  Sheet 1: type='case-explorer'    -> Case Explorer (browse individual cases)",
        "  Sheet 2: type='process-explorer' -> Process Explorer (variant flow visualization)",
        "  Sheet 3: type='process-overview' -> Process Overview (KPI overview dashboard)",
        "  Sheet 4: no type (custom)         -> KPI & Analytics (filters + KPIs + tables)",
        "NOTE: 'process-ai', 'conformance', 'social' require PI license — DO NOT use.",
        "",
        "== VALID CELONIS COMPONENT TYPES ==",
        "(Use ONLY these type strings inside sheet components)",
        "",
    ]
    for ctype, info in VALID_CELONIS_COMPONENT_TYPES.items():
        lines.append(f"  TYPE: '{ctype}'")
        lines.append(f"  Desc: {info['description']}")
        if "recommended_size" in info:
            lines.append(f"  Size: w={info['recommended_size']['w']}, h={info['recommended_size']['h']}")
        if "placement" in info:
            lines.append(f"  Placement: {info['placement']}")
        lines.append("")

    lines.append("== 4-SHEET ANALYSIS LAYOUT ==")
    lines.append("Sheet 1 (case-explorer):    Case Explorer — no components needed, Celonis renders built-in UI")
    lines.append("Sheet 2 (process-explorer): process-explorer component w=12 h=12 (full sheet)")
    lines.append("Sheet 3 (process-overview): KPI tiles (h=3 each) + Activity Frequency table")
    lines.append("Sheet 4 (custom):           Filter bar (h=1) + KPI tiles (h=3) + tables (h=6)")
    lines.append("")

    lines.append("== P2P KPI CATALOG ==")
    for kpi in KPI_CATALOG["P2P"]:
        lines.append(f"  KPI: {kpi['id']} | {kpi['name']} ({kpi['unit']})")
        if "formula" in kpi:
            lines.append(f"  PQL: {kpi['formula']}")
        lines.append(f"  Type: {kpi['component_type']}")
        lines.append("")

    lines.append("== O2C KPI CATALOG ==")
    for kpi in KPI_CATALOG["O2C"]:
        lines.append(f"  KPI: {kpi['id']} | {kpi['name']} ({kpi['unit']})")
        if "formula" in kpi:
            lines.append(f"  PQL: {kpi['formula']}")
        lines.append(f"  Type: {kpi['component_type']}")
        lines.append("")

    lines.append("== PROCESS FILTER TEMPLATES (P2P) ==")
    for fname, fpql in PROCESS_FILTER_TEMPLATES["P2P"].items():
        lines.append(f"  {fname}: {fpql}")
    lines.append("")
    lines.append("== PROCESS FILTER TEMPLATES (O2C) ==")
    for fname, fpql in PROCESS_FILTER_TEMPLATES["O2C"].items():
        lines.append(f"  {fname}: {fpql}")

    return "\n".join(lines)
