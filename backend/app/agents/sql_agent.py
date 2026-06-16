import json
from app.agents.base_agent import BaseAgent

class TransformationSQLAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Transformation SQL Agent")

    def generate(self, requirement_spec: str) -> tuple[str, str]:
        system_prompt = (
            "You are an expert Celonis SQL Developer Agent. Your job is to generate highly optimized transformations.sql "
            "code to prepare data for a process-aware model or object-centric event logs in Celonis.\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your explanation of mapping rules, joins, derived columns, and data cleaning rules>\n"
            "---SQL---\n"
            "<Valid, syntax-valid SQL queries containing table definitions, cleaning, and UNION structure for the event log>\n\n"
            "Ensure the SQL:\n"
            "- Defines temporary views or tables for staging (e.g. joining SAP EKKO, EKPO, MSEG, RBKP).\n"
            "- Performs proper cleaning (handling null values, converting timestamps).\n"
            "- Maps fields into a standard event log structure (Case ID, Activity Name, Event Time, User/Resource, Amount, Sorting index).\n"
            "- Supports either traditional case-based process mining or object-centric event tables."
        )

        prompt = f"Based on the following process mining specification, generate the SQL transformations:\n\n{requirement_spec}"

        response, model_used = self.invoke(system_prompt, prompt)
        
        rationale, sql_content = self._parse_structured_response(response)
        return rationale, sql_content

    def fix_error(self, requirement_spec: str, failing_sql: str, error_msg: str) -> tuple[str, str]:
        system_prompt = (
            "You are an expert Celonis SQL Developer Agent. Your job is to fix a failing transformations.sql query.\n"
            "Below is the original requirements specification, the failing SQL query that was executed, and the error message received from the database.\n"
            "Analyze the error carefully, fix the syntax or structural issues, and output the corrected rationale and SQL query.\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your explanation of the fix and what was corrected>\n"
            "---SQL---\n"
            "<Valid, syntax-valid SQL queries containing table definitions, cleaning, and UNION structure for the event log>\n\n"
            "Make sure the SQL contains proper schema mappings and joins, and handles the columns precisely without syntax errors."
        )

        prompt = (
            f"### Original Requirements:\n{requirement_spec}\n\n"
            f"### Failing SQL Query:\n```sql\n{failing_sql}\n```\n\n"
            f"### Database Error Message:\n{error_msg}\n\n"
            f"Please identify and correct the error in the SQL query."
        )

        response, model_used = self.invoke(system_prompt, prompt)
        rationale, sql_content = self._parse_structured_response(response)
        return rationale, sql_content

    def _parse_structured_response(self, text: str) -> tuple[str, str]:
        rationale = "No rationale provided."
        sql_content = "-- SQL code empty"
        
        if "---RATIONALE---" in text and "---SQL---" in text:
            parts = text.split("---SQL---")
            rationale_part = parts[0].replace("---RATIONALE---", "").strip()
            sql_part = parts[1].strip()
            # Clean possible markdown wrap ```sql
            if sql_part.startswith("```"):
                lines = sql_part.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                sql_part = "\n".join(lines).strip()
            return rationale_part, sql_part
        else:
            try:
                start_idx = text.lower().find("select")
                if start_idx != -1:
                    sql_content = text[start_idx:].strip()
                    rationale = text[:start_idx].strip()
            except Exception:
                pass
            return rationale, sql_content

    def _mock_response(self, prompt: str) -> str:
        p_lower = prompt.lower()
        if "o2c" in p_lower or "order-to-cash" in p_lower or "order to cash" in p_lower or "sales" in p_lower:
            mock_sql = (
                "-- Celonis Data Transformation Script\n"
                "-- Process: Order-to-Cash (O2C)\n"
                "-- Source System: SAP S/4HANA\n\n"
                "DROP VIEW IF EXISTS TEMP_O2C_CASES;\n"
                "DROP TABLE IF EXISTS TEMP_O2C_EVENT_LOG;\n\n"
                "-- Step 1: Pre-process Case Master Data (KNA1 + VBAK + VBAP)\n"
                "CREATE VIEW TEMP_O2C_CASES AS\n"
                "SELECT\n"
                "    CONCAT(vbap.VBELN, '_', vbap.POSNR) AS CASE_KEY,\n"
                "    vbak.VBELN AS SO_NUMBER,\n"
                "    vbap.POSNR AS SO_ITEM,\n"
                "    vbak.BUKRS_VF AS COMPANY_CODE,\n"
                "    vbak.KUNNR AS CUSTOMER_ID,\n"
                "    kna1.NAME1 AS CUSTOMER_NAME,\n"
                "    vbap.NETWR AS SO_AMOUNT,\n"
                "    vbap.WAERK AS CURRENCY\n"
                "FROM VBAP vbap\n"
                "INNER JOIN VBAK vbak ON vbap.VBELN = vbak.VBELN\n"
                "LEFT JOIN KNA1 kna1 ON vbak.KUNNR = kna1.KUNNR\n"
                "WHERE vbap.ABGRU IS NULL; -- Exclude rejected items\n\n"
                "-- Step 2: Extract Activity Events into Unified Event Log\n"
                "CREATE TABLE TEMP_O2C_EVENT_LOG AS\n"
                "SELECT * FROM (\n"
                "    -- Event A: Sales Order Creation\n"
                "    SELECT\n"
                "        CONCAT(vbap.VBELN, '_', vbap.POSNR) AS CASE_KEY,\n"
                "        'Create Sales Order Item' AS ACTIVITY,\n"
                "        CAST(vbak.ERDAT AS TIMESTAMP) AS EVENT_TIME,\n"
                "        vbak.ERNAM AS USER_NAME,\n"
                "        10 AS SORT_INDEX\n"
                "    FROM VBAP vbap\n"
                "    INNER JOIN VBAK vbak ON vbap.VBELN = vbak.VBELN\n\n"
                "    UNION ALL\n\n"
                "    -- Event B: Delivery Creation\n"
                "    SELECT\n"
                "        CONCAT(lips.VGBEL, '_', lips.VGPOS) AS CASE_KEY,\n"
                "        'Create Delivery Item' AS ACTIVITY,\n"
                "        CAST(lips.ERDAT AS TIMESTAMP) AS EVENT_TIME,\n"
                "        lips.ERNAM AS USER_NAME,\n"
                "        20 AS SORT_INDEX\n"
                "    FROM LIPS lips\n"
                "    WHERE lips.VGBEL IS NOT NULL\n\n"
                "    UNION ALL\n\n"
                "    -- Event C: Ship Goods (Goods Issue)\n"
                "    SELECT\n"
                "        CONCAT(lips.VGBEL, '_', lips.VGPOS) AS CASE_KEY,\n"
                "        'Ship Goods' AS ACTIVITY,\n"
                "        CAST(likp.WADAT_IST AS TIMESTAMP) AS EVENT_TIME,\n"
                "        lips.ERNAM AS USER_NAME,\n"
                "        30 AS SORT_INDEX\n"
                "    FROM LIPS lips\n"
                "    INNER JOIN LIKP likp ON lips.VBELN = likp.VBELN\n"
                "    WHERE likp.WADAT_IST IS NOT NULL\n\n"
                "    UNION ALL\n\n"
                "    -- Event D: Billing (Invoice Creation)\n"
                "    SELECT\n"
                "        CONCAT(vbrp.AUBEL, '_', vbrp.AUPOS) AS CASE_KEY,\n"
                "        'Create Invoice' AS ACTIVITY,\n"
                "        CAST(vbrk.FKDAT AS TIMESTAMP) AS EVENT_TIME,\n"
                "        vbrk.ERNAM AS USER_NAME,\n"
                "        40 AS SORT_INDEX\n"
                "    FROM VBRP vbrp\n"
                "    INNER JOIN VBRK vbrk ON vbrp.VBELN = vbrk.VBELN\n\n"
                "    UNION ALL\n\n"
                "    -- Event E: Clear Invoice Payment\n"
                "    SELECT\n"
                "        CONCAT(vbrp.AUBEL, '_', vbrp.AUPOS) AS CASE_KEY,\n"
                "        'Clear Invoice Payment' AS ACTIVITY,\n"
                "        CAST(bsad.BUDAT AS TIMESTAMP) AS EVENT_TIME,\n"
                "        bsad.ERNAM AS USER_NAME,\n"
                "        50 AS SORT_INDEX\n"
                "    FROM VBRP vbrp\n"
                "    INNER JOIN BSAD bsad ON vbrp.VBELN = bsad.REBZG AND vbrp.POSNR = bsad.REBZP\n"
                ") AS events\n"
                "WHERE EVENT_TIME IS NOT NULL;\n"
            )
            return (
                "---RATIONALE---\n"
                "Joined VBAK (header) and VBAP (items) to form the Case Master view. "
                "A composite key (VBELN + POSNR) was constructed to prevent event ambiguity. "
                "The event log was unioned using distinct mappings from VBAK (creation), LIPS (delivery creation and shipping), "
                "VBRK/VBRP (invoice creation), and BSAD (payment clearing). Null timestamps are filtered to prevent schema break.\n"
                "---SQL---\n" + mock_sql
            )
        else:
            mock_sql = (
                "-- Celonis Data Transformation Script\n"
                "-- Process: Purchase-to-Pay (P2P)\n"
                "-- Source System: SAP S/4HANA\n\n"
                "DROP VIEW IF EXISTS TEMP_P2P_CASES;\n"
                "DROP TABLE IF EXISTS TEMP_P2P_EVENT_LOG;\n\n"
                "-- Step 1: Pre-process Case Master Data (LFA1 + EKKO + EKPO)\n"
                "CREATE VIEW TEMP_P2P_CASES AS\n"
                "SELECT CASE_KEY, PO_NUMBER, PO_ITEM, COMPANY_CODE, VENDOR_ID, VENDOR_NAME, PO_AMOUNT, CURRENCY\n"
                "FROM (\n"
                "    SELECT\n"
                "        CONCAT(ekpo.EBELN, '_', ekpo.EBELP) AS CASE_KEY,\n"
                "        ekko.EBELN AS PO_NUMBER,\n"
                "        ekpo.EBELP AS PO_ITEM,\n"
                "        ekko.BUKRS AS COMPANY_CODE,\n"
                "        ekko.LIFNR AS VENDOR_ID,\n"
                "        lfa1.NAME1 AS VENDOR_NAME,\n"
                "        ekpo.NETPR AS PO_AMOUNT,\n"
                "        ekko.WAERS AS CURRENCY,\n"
                "        ROW_NUMBER() OVER (PARTITION BY ekpo.EBELN, ekpo.EBELP ORDER BY ekpo.recordstamp DESC) AS rn\n"
                "    FROM EKPO ekpo\n"
                "    INNER JOIN EKKO ekko ON ekpo.EBELN = ekko.EBELN\n"
                "    LEFT JOIN LFA1 lfa1 ON ekko.LIFNR = lfa1.LIFNR\n"
                "    WHERE ekpo.LOEKZ IS NULL\n"
                ") AS cases_with_rn WHERE rn = 1; -- Exclude deleted and duplicate items\n\n"
                "-- Step 2: Extract Activity Events into Unified Event Log\n"
                "CREATE TABLE TEMP_P2P_EVENT_LOG AS\n"
                "SELECT * FROM (\n"
                "    -- Event A: PO Creation\n"
                "    SELECT\n"
                "        CONCAT(ekpo.EBELN, '_', ekpo.EBELP) AS CASE_KEY,\n"
                "        'Create Purchase Order Item' AS ACTIVITY,\n"
                "        CAST(ekko.AEDAT AS TIMESTAMP) AS EVENT_TIME,\n"
                "        ekko.ERNAM AS USER_NAME,\n"
                "        10 AS SORT_INDEX\n"
                "    FROM EKPO ekpo\n"
                "    INNER JOIN EKKO ekko ON ekpo.EBELN = ekko.EBELN\n\n"
                "    UNION ALL\n\n"
                "    -- Event B: Goods Receipt\n"
                "    SELECT\n"
                "        CONCAT(mseg.EBELN, '_', mseg.EBELP) AS CASE_KEY,\n"
                "        'Receive Goods' AS ACTIVITY,\n"
                "        CAST(mseg.BUDAT_MKPF AS TIMESTAMP) AS EVENT_TIME,\n"
                "        mseg.USNAM_MKPF AS USER_NAME,\n"
                "        20 AS SORT_INDEX\n"
                "    FROM MSEG mseg\n"
                "    WHERE mseg.BWART = '101' -- Movement Type 101: Goods Receipt\n\n"
                "    UNION ALL\n\n"
                "    -- Event C: Invoice Receipt\n"
                "    SELECT\n"
                "        CONCAT(rseg.EBELN, '_', rseg.EBELP) AS CASE_KEY,\n"
                "        'Receive Invoice' AS ACTIVITY,\n"
                "        CAST(rbkp.BUDAT AS TIMESTAMP) AS EVENT_TIME,\n"
                "        rbkp.USNAM AS USER_NAME,\n"
                "        30 AS SORT_INDEX\n"
                "    FROM RSEG rseg\n"
                "    INNER JOIN RBKP rbkp ON rseg.BELNR = rbkp.BELNR AND rseg.GJAHR = rbkp.GJAHR\n\n"
                "    UNION ALL\n\n"
                "    -- Event D: Clear Invoice Payment\n"
                "    SELECT\n"
                "        CONCAT(rseg.EBELN, '_', rseg.EBELP) AS CASE_KEY,\n"
                "        'Pay Invoice' AS ACTIVITY,\n"
                "        CAST(bkpf.BUDAT AS TIMESTAMP) AS EVENT_TIME,\n"
                "        bkpf.USNAM AS USER_NAME,\n"
                "        40 AS SORT_INDEX\n"
                "    FROM RSEG rseg\n"
                "    INNER JOIN BSAK bsak ON rseg.BELNR = bsak.REBZG AND rseg.GJAHR = bsak.REBZJ\n"
                "    INNER JOIN BKPF bkpf ON bsak.BELNR = bkpf.BELNR AND bsak.GJAHR = bkpf.GJAHR\n"
                ") AS events\n"
                "WHERE EVENT_TIME IS NOT NULL;\n"
            )
            return (
                "---RATIONALE---\n"
                "Joined EKKO (header) and EKPO (items) to form the Case Master view. "
                "A composite key (EBELN + EBELP) was constructed to prevent event ambiguity. "
                "The event log was unioned using distinct mappings from EKKO (creation), MSEG (101 goods receipt), "
                "RSEG/RBKP (invoice), and BSAK/BKPF (payment clearing). Null timestamps are filtered to prevent schema break.\n"
                "---SQL---\n" + mock_sql
            )
