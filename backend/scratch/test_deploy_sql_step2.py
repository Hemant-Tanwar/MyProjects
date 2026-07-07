import os
import pandas as pd
from pycelonis import get_celonis
from app.celonis_deployer import extract_table_columns_from_sql

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"
sql_content = """
CREATE TABLE O2C_EVENT_LOG AS
SELECT VBELN AS CASE_ID, 'Create Sales Order' AS ACTIVITY, CAST(ERDAT AS TIMESTAMP) AS EVENT_TIME, ERNAM AS USER, NULL AS AMOUNT FROM VBAK WHERE AUART IN ('OR', 'TA')
UNION ALL
SELECT VBELN AS CASE_ID, 'Create Sales Order Item' AS ACTIVITY, CAST(ERDAT AS TIMESTAMP) AS EVENT_TIME, NULL AS USER, NETWR AS AMOUNT FROM VBAP
UNION ALL
SELECT OBJECTID AS CASE_ID, 'Change Sales Order' AS ACTIVITY, CAST(UDATE AS TIMESTAMP) AS EVENT_TIME, USERNAME AS USER, NULL AS AMOUNT FROM CDHDR WHERE OBJECTCLAS = 'VERKBELEG'
UNION ALL
SELECT LIKP.VBELN AS CASE_ID, 'Record Goods Issue' AS ACTIVITY, CAST(LIKP.WADAT_IST AS TIMESTAMP) AS EVENT_TIME, LIKP.ERNAM AS USER, NULL AS AMOUNT 
FROM LIKP 
JOIN MSEG ON LIKP.VBELN = MSEG.VBELN 
WHERE LIKP.WADAT_IST IS NOT NULL AND MSEG.BWART = '601'
UNION ALL
SELECT MSEG.VBELN AS CASE_ID, 'Cancel Goods Issue' AS ACTIVITY, CAST(MKPF.BUDAT AS TIMESTAMP) AS EVENT_TIME, MKPF.USNAM AS USER, NULL AS AMOUNT 
FROM MKPF 
JOIN MSEG ON MKPF.MBLNR = MSEG.MBLNR 
WHERE MSEG.BWART = '602' AND MSEG.VBELN IS NOT NULL
UNION ALL
SELECT VBELN AS CASE_ID, 'Sales Order Status Change' AS ACTIVITY, CAST(AEDAT AS TIMESTAMP) AS EVENT_TIME, NULL AS USER, NULL AS AMOUNT FROM VBAK WHERE GBSTK IS NOT NULL;

CREATE TABLE O2C_CASES AS
SELECT VBELN, ERDAT, VKORG, NETWR, WAERK, AUART 
FROM VBAK
WHERE VBELN IS NOT NULL 
AND ABRVW != 'Canceled' 
AND AUART IN ('OR', 'TA');
"""

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    data_pool = [p for p in c.data_integration.get_data_pools() if p.name == "O2C"][0]
    
    data_source_dir = "/Users/hemanttanwar/Documents/hemant_process_mine/Data_source"
    table_to_cols = extract_table_columns_from_sql(sql_content)
    pool_tables = {t.name.upper(): t for t in data_pool.get_tables()}
    
    print("Pool tables in Celonis:", list(pool_tables.keys()))
    
    for t_name, req_cols in table_to_cols.items():
        t_upper = t_name.upper()
        print(f"\nProcessing: {t_upper}")
        csv_filename = f"{t_upper}.csv"
        csv_path = os.path.join(data_source_dir, csv_filename)
        has_csv = os.path.exists(csv_path)
        print(f"  CSV exists: {has_csv} at {csv_path}")
        print(f"  In pool_tables: {t_upper in pool_tables}")
        
except Exception as e:
    print("Error:", e)
