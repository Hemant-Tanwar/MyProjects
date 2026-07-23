import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.celonis_knowledge_base import build_3_sheet_analysis, KPI_CATALOG, PROCESS_FILTER_TEMPLATES

print("Resolving dummy items...")
process_type = "P2P"
event_log_tbl = "TEMP_P2P_EVENT_LOG"
case_tbl = "TEMP_P2P_CASES"

catalog = KPI_CATALOG.get(process_type, [])
kpi_items = []
for k in catalog[:6]:
    pql = k.get("formula", "")
    pql = pql.format(event_log_table=event_log_tbl, case_table=case_tbl, case_col="CASE_KEY")
    kpi_items.append({"id": k["id"], "displayName": k["name"], "pql": pql})

filter_catalog = PROCESS_FILTER_TEMPLATES.get(process_type, {})
filter_items = []
for fid, fpql in list(filter_catalog.items())[:3]:
    fpql = fpql.format(event_log_table=event_log_tbl, case_table=case_tbl, case_col="CASE_KEY")
    filter_items.append({"id": fid, "displayName": fid.replace("_", " ").title(), "pql": fpql})

print("Calling build_3_sheet_analysis...")
sheets = build_3_sheet_analysis(
    kpi_items=kpi_items,
    filter_items=filter_items,
    event_log_table=event_log_tbl,
    case_table=case_tbl,
    case_col="CASE_KEY",
    process_name="Purchase-to-Pay"
)

print(f"Success! Number of sheets built: {len(sheets)}")
for i, sheet in enumerate(sheets):
    print(f"Sheet {i+1}: Name={sheet.get('name')}, contentType={sheet.get('contentType')}, Components count={len(sheet.get('components', []))}")
    if sheet.get("components"):
        for c in sheet["components"]:
            print(f"  - Component: ID={c.get('id')}, Type={c.get('type')}, Title={c.get('title') or c.get('settings', {}).get('title')}")
            # print PQL for the components to verify they were formatted correctly
            if "formula" in c:
                print(f"    Formula Text: {c['formula'].get('text')}")
            if "filter" in c:
                print(f"    Filter Text: {c['filter'].get('text')}")
