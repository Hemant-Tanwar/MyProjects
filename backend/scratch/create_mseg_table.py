import os
import json
import pandas as pd
import numpy as np

# Path definitions
sap_dict_path = "/Users/hemanttanwar/Downloads/celonis_agentic_ai/knowledge_base/sap_dictionary.json"
data_source_dir = "/Users/hemanttanwar/Documents/hemant_process_mine/Data_source"

# 1. Parse MSEG fields
with open(sap_dict_path, 'r') as f:
    sap_dict = json.load(f)

mseg_fields = [field_obj["field"].lower() for field_obj in sap_dict["MSEG"]["fields"]]
print(f"Loaded {len(mseg_fields)} MSEG fields from dictionary.")

# Ensure essential fields exist in list, add auditing ones if not
mseg_fields_set = set(mseg_fields)
additional_fields = ["operation_flag", "is_deleted", "recordstamp"]
for field in additional_fields:
    if field not in mseg_fields_set:
        mseg_fields.append(field)

# 2. Read existing relational data
ekbe_path = os.path.join(data_source_dir, "EKBE.CSV")
ekpo_path = os.path.join(data_source_dir, "EKPO.CSV")
ekko_path = os.path.join(data_source_dir, "EKKO.CSV")

ekbe_df = pd.read_csv(ekbe_path) if os.path.exists(ekbe_path) else pd.DataFrame()
ekpo_df = pd.read_csv(ekpo_path) if os.path.exists(ekpo_path) else pd.DataFrame()
ekko_df = pd.read_csv(ekko_path) if os.path.exists(ekko_path) else pd.DataFrame()

print(f"Loaded EKBE: {len(ekbe_df)} rows")
print(f"Loaded EKPO: {len(ekpo_df)} rows")
print(f"Loaded EKKO: {len(ekko_df)} rows")

# Build reference lookups
ekpo_lookup = {}
if not ekpo_df.empty:
    for _, row in ekpo_df.iterrows():
        ebeln_val = str(row.get("ebeln", "")).strip()
        ebelp_val = row.get("ebelp")
        try:
            ebelp = int(float(ebelp_val)) if pd.notnull(ebelp_val) else 0
        except Exception:
            ebelp = 0
        
        key = (ebeln_val, ebelp)
        ekpo_lookup[key] = {
            "matnr": row.get("matnr", None),
            "werks": row.get("werks", None),
            "lgort": row.get("lgort", None),
            "meins": row.get("meins", None),
            "bukrs": row.get("bukrs", None)
        }

ekko_lookup = {}
if not ekko_df.empty:
    for _, row in ekko_df.iterrows():
        ebeln_val = str(row.get("ebeln", "")).strip()
        ekko_lookup[ebeln_val] = {
            "lifnr": row.get("lifnr", None),
            "bukrs": row.get("bukrs", None),
            "ernam": row.get("ernam", None)
        }

# Generate MSEG rows
mseg_rows = []

# If EKBE exists, we base our material document rows on EKBE entries (representing Goods Receipt, etc.)
if not ekbe_df.empty:
    for idx, row in ekbe_df.iterrows():
        # Clean values
        ebeln = str(row.get("ebeln", "")).strip()
        ebelp_val = row.get("ebelp")
        try:
            ebelp = int(float(ebelp_val)) if pd.notnull(ebelp_val) else 0
        except Exception:
            ebelp = 0
        
        # We need a material document number (belnr or lfbnr)
        mblnr = row.get("belnr")
        if pd.isnull(mblnr) or str(mblnr).strip() == "":
            mblnr = row.get("lfbnr")
        if pd.isnull(mblnr) or str(mblnr).strip() == "":
            # Generate one if not found but ebeln exists
            if ebeln:
                mblnr = f"500{ebeln[-7:]}"
            else:
                mblnr = f"500000000{idx}"
        
        mblnr = str(mblnr).strip()
        
        mjahr = row.get("gjahr")
        if pd.isnull(mjahr) or str(mjahr).strip() == "":
            mjahr = row.get("lfgja")
        if pd.isnull(mjahr) or str(mjahr).strip() == "":
            mjahr = 2022
        try:
            mjahr = int(float(mjahr))
        except Exception:
            mjahr = 2022
        
        zeile = row.get("buzei")
        if pd.isnull(zeile) or str(zeile).strip() == "":
            zeile = row.get("lfpos")
        if pd.isnull(zeile) or str(zeile).strip() == "":
            zeile = 10
        try:
            zeile = int(float(zeile))
        except Exception:
            zeile = 10
        
        # Look up additional values from EKPO
        ekpo_info = ekpo_lookup.get((ebeln, ebelp), {})
        # Look up lifnr from EKKO
        ekko_info = ekko_lookup.get(ebeln, {})
        
        # Helper to get clean value or fallback to default
        def clean_val(val, default=None):
            if pd.isnull(val) or str(val).strip() == "" or str(val).lower() == "nan":
                return default
            return val

        # Values from EKBE row
        matnr = clean_val(row.get("matnr")) or ekpo_info.get("matnr")
        werks = clean_val(row.get("werks")) or ekpo_info.get("werks")
        lgort = clean_val(row.get("lgort")) or ekpo_info.get("lgort")
        meins = ekpo_info.get("meins") or "EA"
        
        lifnr = ekko_info.get("lifnr")
        bukrs = clean_val(row.get("bukrs")) or ekpo_info.get("bukrs") or ekko_info.get("bukrs") or "USA1"
        
        # Determine bwart value dynamically to have multiple movement types
        shkzg_val = clean_val(row.get("shkzg"), "S")
        bwart_val = clean_val(row.get("bwart"))
        if not bwart_val:
            if shkzg_val == "H":
                bwart_val = "122" if idx % 4 == 0 else "102"
            else:
                if idx % 15 == 0:
                    bwart_val = "311"
                elif idx % 20 == 0:
                    bwart_val = "201"
                elif idx % 12 == 0:
                    bwart_val = "161"
                else:
                    bwart_val = "101"

        # Build mseg dictionary
        mseg_row = {f: None for f in mseg_fields}
        
        mseg_row["mandt"] = clean_val(row.get("mandt"), 250)
        mseg_row["mblnr"] = mblnr
        mseg_row["mjahr"] = mjahr
        mseg_row["zeile"] = zeile
        mseg_row["line_id"] = idx + 1
        mseg_row["bwart"] = bwart_val
        mseg_row["matnr"] = matnr
        mseg_row["werks"] = werks
        mseg_row["lgort"] = lgort
        mseg_row["charg"] = clean_val(row.get("charg"))
        mseg_row["shkzg"] = clean_val(row.get("shkzg"), "S")
        mseg_row["waers"] = clean_val(row.get("waers"), "USD")
        mseg_row["dmbtr"] = clean_val(row.get("dmbtr"), clean_val(row.get("dmbtr_pop"), 100.0))
        mseg_row["menge"] = clean_val(row.get("menge"), clean_val(row.get("menge_pop"), 10.0))
        mseg_row["meins"] = meins
        mseg_row["ebeln"] = ebeln
        mseg_row["ebelp"] = ebelp
        mseg_row["lifnr"] = lifnr
        mseg_row["bukrs"] = bukrs
        
        # Populate header fields from EKBE/EKKO to avoid type inference issues
        mseg_row["budat_mkpf"] = clean_val(row.get("budat"), "2022-01-31")
        mseg_row["usnam_mkpf"] = clean_val(ekko_info.get("ernam"), "SATISHE")
        mseg_row["cpudt_mkpf"] = clean_val(row.get("cpudt"), "2022-01-31")
        mseg_row["cputm_mkpf"] = clean_val(row.get("cputm"), "12:00:00")
        mseg_row["vgart_mkpf"] = "WE"  # Goods receipt
        
        # Add timestamp and other audits
        mseg_row["operation_flag"] = "I"
        mseg_row["is_deleted"] = False
        mseg_row["recordstamp"] = clean_val(row.get("recordstamp"), "2022-01-31 20:41:57.486125+00:00")
        
        mseg_rows.append(mseg_row)
else:
    # Fallback: Create mock data using some default logic
    print("Warning: EKBE is empty or not found. Creating default mock rows.")
    for idx in range(20):
        mseg_row = {f: None for f in mseg_fields}
        mseg_row["mandt"] = 250
        mseg_row["mblnr"] = f"50000000{idx}"
        mseg_row["mjahr"] = 2022
        mseg_row["zeile"] = 10
        mseg_row["line_id"] = idx + 1
        mseg_row["bwart"] = "101"
        mseg_row["matnr"] = "TEST-MAT"
        mseg_row["werks"] = "1000"
        mseg_row["shkzg"] = "S"
        mseg_row["waers"] = "USD"
        mseg_row["dmbtr"] = 100.0
        mseg_row["menge"] = 10.0
        mseg_row["meins"] = "EA"
        mseg_row["operation_flag"] = "I"
        mseg_row["is_deleted"] = False
        mseg_row["recordstamp"] = "2022-01-31 20:41:57.486125+00:00"
        mseg_rows.append(mseg_row)

df_mseg = pd.DataFrame(mseg_rows)
# Fill NaN/NaT with None or empty to be safe
df_mseg = df_mseg.where(pd.notnull(df_mseg), None)

# Ensure MSEG name is uppercase (MSEG.CSV)
dest_path = os.path.join(data_source_dir, "MSEG.CSV")
df_mseg.to_csv(dest_path, index=False)
print(f"Successfully generated MSEG table with {len(df_mseg)} rows and {len(df_mseg.columns)} columns.")
print(f"Saved to: {dest_path}")
