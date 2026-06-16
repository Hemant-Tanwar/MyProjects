-- Celonis Data Transformation Script
-- Process: Purchase-to-Pay (P2P)
-- Source System: SAP S/4HANA

DROP TABLE IF EXISTS TEMP_P2P_CASES;
DROP TABLE IF EXISTS TEMP_P2P_EVENT_LOG;

-- Step 1: Pre-process Case Master Data (LFA1 + EKKO + EKPO)
CREATE TABLE TEMP_P2P_CASES AS
SELECT CASE_KEY, PO_NUMBER, PO_ITEM, COMPANY_CODE, VENDOR_ID, VENDOR_NAME, PO_AMOUNT, CURRENCY
FROM (
    SELECT
        CONCAT(ekpo.EBELN, '_', ekpo.EBELP) AS CASE_KEY,
        ekko.EBELN AS PO_NUMBER,
        ekpo.EBELP AS PO_ITEM,
        ekko.BUKRS AS COMPANY_CODE,
        ekko.LIFNR AS VENDOR_ID,
        lfa1.NAME1 AS VENDOR_NAME,
        ekpo.NETPR AS PO_AMOUNT,
        ekko.WAERS AS CURRENCY,
        ROW_NUMBER() OVER (PARTITION BY ekpo.EBELN, ekpo.EBELP ORDER BY ekpo.recordstamp DESC) AS rn
    FROM EKPO ekpo
    INNER JOIN EKKO ekko ON ekpo.EBELN = ekko.EBELN
    LEFT JOIN LFA1 lfa1 ON ekko.LIFNR = lfa1.LIFNR
    WHERE ekpo.LOEKZ IS NULL
) AS cases_with_rn WHERE rn = 1; -- Exclude deleted and duplicate items

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
WHERE EVENT_TIME IS NOT NULL;