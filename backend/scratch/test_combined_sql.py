from pycelonis import get_celonis

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

sql_content = """-- Celonis Data Transformation Script
-- Process: Purchase-to-Pay (P2P)
-- Source System: SAP S/4HANA

DROP VIEW IF EXISTS TEMP_P2P_CASES;
DROP TABLE IF EXISTS TEMP_P2P_EVENT_LOG;

-- Step 1: Pre-process Case Master Data (LFA1 + EKKO + EKPO)
CREATE VIEW TEMP_P2P_CASES AS
SELECT
    CONCAT(ekpo.EBELN, '_', ekpo.EBELP) AS CASE_KEY,
    ekko.EBELN AS PO_NUMBER,
    ekpo.EBELP AS PO_ITEM,
    ekko.BUKRS AS COMPANY_CODE,
    ekko.LIFNR AS VENDOR_ID,
    lfa1.NAME1 AS VENDOR_NAME,
    ekpo.NETPR AS PO_AMOUNT,
    ekko.WAERS AS CURRENCY
FROM EKPO ekpo
INNER JOIN EKKO ekko ON ekpo.EBELN = ekko.EBELN
LEFT JOIN LFA1 lfa1 ON ekko.LIFNR = lfa1.LIFNR
WHERE ekpo.LOEKZ IS NULL; -- Exclude deleted items

-- Step 2: Extract Activity Events into Unified Event Log
CREATE TABLE TEMP_P2P_EVENT_LOG AS
SELECT * FROM (
    -- Event A: PO Creation
    SELECT
        CONCAT(ekpo.EBELN, '_', ekpo.EBELP) AS CASE_KEY,
        'Create Purchase Order Item' AS ACTIVITY,
        CAST(ekko.AEDAT AS TIMESTAMP) AS EVENT_TIME,
        ekko.ERNAM AS USER_NAME,
        10 AS SORT_INDEX
    FROM EKPO ekpo
    INNER JOIN EKKO ekko ON ekpo.EBELN = ekko.EBELN

    UNION ALL

    -- Event B: Goods Receipt
    SELECT
        CONCAT(mseg.EBELN, '_', mseg.EBELP) AS CASE_KEY,
        'Receive Goods' AS ACTIVITY,
        CAST(mseg.BUDAT_MKPF AS TIMESTAMP) AS EVENT_TIME,
        mseg.USNAM_MKPF AS USER_NAME,
        20 AS SORT_INDEX
    FROM MSEG mseg
    WHERE mseg.BWART = '101' -- Movement Type 101: Goods Receipt

    UNION ALL

    -- Event C: Invoice Receipt
    SELECT
        CONCAT(rseg.EBELN, '_', rseg.EBELP) AS CASE_KEY,
        'Receive Invoice' AS ACTIVITY,
        CAST(rbkp.BUDAT AS TIMESTAMP) AS EVENT_TIME,
        rbkp.USNAM AS USER_NAME,
        30 AS SORT_INDEX
    FROM RSEG rseg
    INNER JOIN RBKP rbkp ON rseg.BELNR = rbkp.BELNR AND rseg.GJAHR = rbkp.GJAHR

    UNION ALL

    -- Event D: Clear Invoice Payment
    SELECT
        CONCAT(rseg.EBELN, '_', rseg.EBELP) AS CASE_KEY,
        'Pay Invoice' AS ACTIVITY,
        CAST(bkpf.BUDAT AS TIMESTAMP) AS EVENT_TIME,
        bkpf.USNAM AS USER_NAME,
        40 AS SORT_INDEX
    FROM RSEG rseg
    INNER JOIN BSAK bsak ON rseg.BELNR = bsak.REBZG AND rseg.GJAHR = bsak.REBZJ
    INNER JOIN BKPF bkpf ON bsak.BELNR = bkpf.BELNR AND bsak.GJAHR = bkpf.GJAHR
) AS events
WHERE EVENT_TIME IS NOT NULL;"""

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pools = c.data_integration.get_data_pools()
    pool = [p for p in pools if p.name == pool_name][0]
    master_pool = [p for p in pools if p.name == "SAP_Dictionary_Master_Pool"][0]
    
    # Get all master tables
    master_tables = [t.name.upper() for t in master_pool.get_tables() if not t.name.upper().startswith("CELONIS_")]
    
    job = pool.create_job(name="Combined SQL Test Job Command Line")
    
    view_statements = []
    for table in master_tables:
        view_statements.append(f"DROP VIEW IF EXISTS {table};")
        view_statements.append(f"CREATE VIEW {table} AS SELECT * FROM \"{master_pool.id}\".\"{table}\";")
        
    sql = "\n".join(view_statements) + "\n\n" + sql_content
    
    t = job.create_transformation(name="T_COMBINED", statement=sql)
    print("Executing combined SQL transformation...")
    try:
        job.execute(wait=True)
        print("Succeeded!")
    except Exception as e:
        print("Failed:", e)
        
    t.delete()
    job.delete()
        
except Exception as e:
    print("Error:", e)
