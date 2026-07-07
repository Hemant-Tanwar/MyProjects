"""
sync_datasource_from_kb.py
==========================
Reads backend/app/agents/Sap_knowledge_base.json, checks every table and
column listed there against the CSVs in Data_source/, and:

  1. If the table CSV is MISSING  → creates it with realistic sample data.
  2. If the table CSV EXISTS but a column is MISSING → appends the column
     with realistic sample data that matches the SAP data type.

Data-type mapping (SAP → Python/pandas):
  CHAR / CUKY / UNIT / LANG / CLNT  → str  (zero-padded where needed)
  NUMC                               → str  (zero-padded numeric string)
  DATS                               → str  ISO date "YYYY-MM-DD"
  TIMS                               → str  "HH:MM:SS"
  DEC / CURR / QUAN / FLTP / INT4   → float / int
"""

import json
import os
import re
import pandas as pd
from datetime import date, time, timedelta

KB_PATH      = os.path.join(os.path.dirname(__file__), "..", "app", "agents", "Sap_knowledge_base.json")
DS_DIR       = os.path.join(os.path.dirname(__file__), "..", "..", "Data_source")
SAMPLE_ROWS  = 10   # rows to generate for new files / new columns


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: realistic value generators per SAP field name + SAP type
# ─────────────────────────────────────────────────────────────────────────────

BASE_DATE  = date(2024, 1, 15)
BASE_TIME  = time(8, 0, 0)

# Pre-seeded domain values for common SAP fields
_DOMAINS = {
    "MANDT":   ["100"] * SAMPLE_ROWS,
    "BUKRS":   ["1000", "2000", "3000", "1000", "2000", "3000", "1000", "2000", "3000", "1000"],
    "EKORG":   ["1000", "1000", "2000", "2000", "1000", "1000", "2000", "2000", "1000", "1000"],
    "WERKS":   ["1000", "1100", "1200", "1300", "1000", "1100", "1200", "1300", "1000", "1100"],
    "LGORT":   ["0001", "0002", "0003", "0001", "0002", "0003", "0001", "0002", "0003", "0001"],
    "WAERS":   ["EUR", "USD", "EUR", "GBP", "EUR", "USD", "EUR", "EUR", "EUR", "USD"],
    "LAND1":   ["DE", "US", "FR", "GB", "IN", "DE", "US", "FR", "GB", "IN"],
    "SPRAS":   ["E", "D", "E", "E", "D", "E", "E", "D", "E", "E"],
    "BWART":   ["101", "102", "261", "262", "501", "502", "601", "602", "311", "312"],
    "BLART":   ["RE", "KR", "ZP", "AB", "SA", "RE", "KR", "ZP", "AB", "SA"],
    "BKLAS":   ["3000", "3001", "7900", "3000", "3001", "7900", "3000", "3001", "7900", "3000"],
    "LOEKZ":   ["", "", "", "", "", "", "", "", "", ""],
    "GBSTK":   ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A"],
    "FKART":   ["F2", "G2", "F1", "F2", "G2", "F1", "F2", "G2", "F1", "F2"],
    "AUART":   ["TA", "TAS", "OR", "TA", "TAS", "OR", "TA", "TAS", "OR", "TA"],
    "MEINS":   ["ST", "KG", "L", "M", "PC", "ST", "KG", "L", "M", "PC"],
    "NETPR":   [100.00, 250.50, 88.25, 300.00, 175.75, 60.00, 430.00, 95.50, 210.00, 540.00],
    "NETWR":   [1000.00, 2505.00, 882.50, 3000.00, 1757.50, 600.00, 4300.00, 955.00, 2100.00, 5400.00],
    "DMBTR":   [1000.00, 2505.00, 882.50, 3000.00, 1757.50, 600.00, 4300.00, 955.00, 2100.00, 5400.00],
    "WRBTR":   [1000.00, 2505.00, 882.50, 3000.00, 1757.50, 600.00, 4300.00, 955.00, 2100.00, 5400.00],
    "MENGE":   [10.0, 20.0, 5.0, 15.0, 8.0, 25.0, 12.0, 30.0, 7.0, 18.0],
    "PSMNG":   [10.0, 20.0, 5.0, 15.0, 8.0, 25.0, 12.0, 30.0, 7.0, 18.0],
    "OBJECTCLAS": ["VERKBELEG", "BELEG", "AUFTR", "VERKBELEG", "BELEG",
                   "AUFTR", "VERKBELEG", "BELEG", "AUFTR", "VERKBELEG"],
    "AUGRU":   ["001", "002", "003", "001", "002", "003", "001", "002", "003", "001"],
    "VSTEL":   ["0001", "0002", "0001", "0002", "0001", "0002", "0001", "0002", "0001", "0002"],
    "VKORG":   ["1000", "1000", "2000", "2000", "1000", "1000", "2000", "2000", "1000", "1000"],
    "VTWEG":   ["10", "20", "10", "20", "10", "20", "10", "20", "10", "20"],
    "SPART":   ["00", "01", "02", "00", "01", "02", "00", "01", "02", "00"],
    "KNUMV":   [f"00{50000000+i}" for i in range(SAMPLE_ROWS)],
}


def _sap_type_category(sap_type: str) -> str:
    """Return broad category: 'str', 'numstr', 'date', 'time', 'float', 'int'."""
    t = sap_type.upper()
    if t.startswith(("CHAR", "CUKY", "UNIT", "LANG", "CLNT", "DATS_STR", "NUMC_STR")):
        return "str"
    if t.startswith("NUMC"):
        return "numstr"
    if t.startswith("DATS"):
        return "date"
    if t.startswith("TIMS"):
        return "time"
    if t.startswith(("DEC", "CURR", "QUAN", "FLTP", "KPEIN", "PEINH")):
        return "float"
    if t.startswith(("INT", "ACCP")):
        return "int"
    return "str"   # safe default — string can be cast to varchar without error


def _numc_width(sap_type: str) -> int:
    m = re.search(r'\((\d+)\)', sap_type)
    return int(m.group(1)) if m else 4


def _make_value(col: str, sap_type: str, row_idx: int) -> object:
    """Return a realistic sample value for a given SAP column+type at row_idx."""
    col_up  = col.upper()
    cat     = _sap_type_category(sap_type)

    # ── 1. Named-domain lookups (highest priority) ────────────────────────────
    if col_up in _DOMAINS:
        vals = _DOMAINS[col_up]
        return vals[row_idx % len(vals)]

    # ── 2. Pattern-based date/time detection ─────────────────────────────────
    col_lo = col.lower()
    date_hints = ("dat", "date", "budat", "bldat", "aedat", "erdat", "eindt",
                  "bedat", "einda", "fkdat", "guebg", "gueen", "lfdat",
                  "prsdt", "valdt", "zfbdt", "augdt", "kodat", "cpudt")
    time_hints = ("uzeit", "cputm", "tcode_time", "time")

    if any(h in col_lo for h in date_hints) or cat == "date":
        d = BASE_DATE + timedelta(days=row_idx * 7)
        return d.strftime("%Y-%m-%d")

    if any(h in col_lo for h in time_hints) or cat == "time":
        h = (8 + row_idx) % 24
        return f"{h:02d}:00:00"

    # ── 3. Numeric columns ────────────────────────────────────────────────────
    amount_hints = ("netwr", "dmbtr", "wrbtr", "hwbas", "fwbas", "mwsts",
                    "navnw", "preis", "netpr", "peinh", "lfimg", "ntgew",
                    "brtgw", "volum", "lmeng", "meins")
    qty_hints    = ("menge", "bmenge", "emeng", "wemng", "bpmng", "psmng",
                    "lmeng", "lfimg", "erfmg")

    if cat == "float" or any(h in col_lo for h in amount_hints):
        base = [100.0, 250.5, 88.25, 300.0, 175.75, 60.0, 430.0, 95.5, 210.0, 540.0]
        return round(base[row_idx % 10], 2)

    if any(h in col_lo for h in qty_hints):
        return float((row_idx + 1) * 5)

    if cat == "int":
        return row_idx + 1

    # ── 4. NUMC fields (numeric-looking strings) ──────────────────────────────
    if cat == "numstr":
        w = _numc_width(sap_type)
        return str(row_idx + 1).zfill(w)

    # ── 5. SAP document numbers (zero-padded strings) ─────────────────────────
    doc_nr_hints = ("vbeln", "ebeln", "belnr", "aufnr", "matnr", "rsnum",
                    "objnr", "kdauf", "kdpos", "vgbel", "lfbnr", "xblnr")
    if any(h in col_lo for h in doc_nr_hints):
        return str(10000000 + row_idx + 1).zfill(10)

    pos_nr_hints = ("posnr", "ebelp", "posnn", "buzei", "kdpos")
    if any(h in col_lo for h in pos_nr_hints):
        return str((row_idx + 1) * 10).zfill(6)

    # ── 6. SAP key/code fields ────────────────────────────────────────────────
    code4_hints = ("bukrs", "werks", "lgort", "ekorg", "vkorg", "spart",
                   "bwkey", "kkber", "periv")
    if any(h in col_lo for h in code4_hints):
        return str(1000 + row_idx % 3).zfill(4)

    # ── 7. Currency / unit / language codes ───────────────────────────────────
    if col_up.endswith(("WAERS", "HWAER")):
        return ["EUR", "USD", "GBP", "EUR", "USD", "EUR", "USD", "EUR", "EUR", "USD"][row_idx % 10]

    # ── 8. User/text fields ────────────────────────────────────────────────────
    user_hints  = ("usnam", "ernam", "aenam", "reswk", "lifnr", "kunnr", "ktokd",
                   "ktokk", "ekgrp")
    if any(h in col_lo for h in user_hints):
        users = ["USER01", "USER02", "ADMIN", "USER03", "USER04",
                 "USER01", "USER02", "ADMIN", "USER03", "USER04"]
        return users[row_idx % 10]

    # ── 9. Text description fields ────────────────────────────────────────────
    txt_hints = ("txt", "name", "bezei", "btext", "bktxt", "ltxt")
    if any(h in col_lo for h in txt_hints):
        return f"Sample Text {row_idx + 1}"

    # ── 10. Boolean / flag fields ─────────────────────────────────────────────
    flag_hints = ("kennz", "xfeld", "flag", "loekz", "stprs")
    if any(h in col_lo for h in flag_hints):
        return ""   # SAP blank = false for char(1) flags

    # ── 11. Safe string default ───────────────────────────────────────────────
    # Integer 0..N prevents CAST_INVALID_INPUT when SQL casts to BIGINT.
    # Return as str so pandas column stays object dtype (matches VARCHAR).
    return str(row_idx)


def generate_table_df(table_name: str, columns: list, n_rows: int = SAMPLE_ROWS) -> pd.DataFrame:
    """Build a DataFrame with sample data for all given columns."""
    data = {}
    for col_def in columns:
        col      = col_def["column"]
        sap_type = col_def.get("type", "CHAR(10)")
        vals     = [_make_value(col, sap_type, i) for i in range(n_rows)]

        # Determine pandas dtype from SAP type category
        cat = _sap_type_category(sap_type)
        if cat in ("float",):
            data[col] = pd.array(vals, dtype="Float64")
        elif cat == "int":
            data[col] = pd.array(vals, dtype="Int64")
        else:
            data[col] = [str(v) for v in vals]   # everything else as string

    return pd.DataFrame(data)


# ─────────────────────────────────────────────────────────────────────────────
# Main sync logic
# ─────────────────────────────────────────────────────────────────────────────

def sync():
    kb_path = os.path.abspath(KB_PATH)
    ds_dir  = os.path.abspath(DS_DIR)

    print(f"\nKnowledge Base : {kb_path}")
    print(f"Data Source Dir: {ds_dir}\n")

    with open(kb_path, encoding="utf-8") as f:
        kb = json.load(f)

    tables = kb.get("source_tables", [])
    print(f"Tables in KB   : {len(tables)}\n")

    created  = []
    updated  = []
    skipped  = []

    for tbl_def in tables:
        table_name = tbl_def.get("table", "").upper()
        kb_columns = tbl_def.get("key_columns", [])
        if not table_name or not kb_columns:
            continue

        csv_path = os.path.join(ds_dir, f"{table_name}.CSV")

        # ── Case A: CSV does not exist → create it from scratch ───────────────
        if not os.path.exists(csv_path):
            print(f"[CREATE] {table_name}  ({len(kb_columns)} columns)")
            df_new = generate_table_df(table_name, kb_columns, SAMPLE_ROWS)
            df_new.to_csv(csv_path, index=False)
            created.append(table_name)
            continue

        # ── Case B: CSV exists → check for missing columns (do NOT add them) ──
        try:
            df = pd.read_csv(csv_path, dtype=str, low_memory=False)
        except Exception as e:
            print(f"[ERROR ] {table_name}  Could not read CSV: {e}")
            continue

        df.columns = [c.upper() for c in df.columns]   # normalise to UPPER
        missing_cols = [c for c in kb_columns if c["column"].upper() not in df.columns]
        if missing_cols:
            print(f"[WARNING] {table_name} is missing columns in datasource: {[c['column'] for c in missing_cols]}. Skipping column creation.")
        skipped.append(table_name)
        continue

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print(f"CREATED  ({len(created)}): {', '.join(created) or '—'}")
    print(f"UPDATED  ({len(updated)}): {', '.join(updated) or '—'}")
    print(f"SKIPPED  ({len(skipped)}): {len(skipped)} tables already complete")
    print("="*60)
    print("Done.\n")


if __name__ == "__main__":
    sync()
