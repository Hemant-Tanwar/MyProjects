import json
import re
import os
from app.agents.base_agent import BaseAgent

class TransformationSQLAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Transformation SQL Agent")

    def generate(self, requirement_spec: str) -> tuple[str, str]:
        kb = self._load_sap_knowledge_base()
        
        # 1. Match process based on keywords in requirement_spec
        processes = kb.get("processes", [])
        matched_processes = []
        spec_lower = requirement_spec.lower()
        for p in processes:
            name_lower = p.get("name", "").lower()
            id_lower = p.get("id", "").lower()
            module_lower = p.get("sap_module", "").lower()
            synonyms = []
            if id_lower == "p2p":
                synonyms = ["purchase-to-pay", "purchase to pay", "procurement", "po", "ekko", "ekpo", "p2p", "purchase order"]
            elif id_lower == "o2c":
                synonyms = ["order-to-cash", "order to cash", "sales", "so", "vbak", "vbap", "o2c", "sales order"]
            elif id_lower == "ap":
                synonyms = ["accounts payable", "ap", "vendor invoice", "bkpf", "bseg", "miro", "invoice verification"]
            elif id_lower == "ar":
                synonyms = ["accounts receivable", "ar", "customer invoice", "billing", "vbrk", "vbrp"]
                
            is_match = False
            if id_lower in spec_lower or name_lower in spec_lower or module_lower in spec_lower:
                is_match = True
            else:
                for syn in synonyms:
                    if syn in spec_lower:
                        is_match = True
                        break
            if is_match:
                matched_processes.append(p)
                
        # Fallback to dynamic custom modeling if no standard process was matched
        if not matched_processes:
            kb_text = (
                "The process spec describes a custom process not predefined in the standard SAP knowledge base. "
                "Please generate the SQL transformations dynamically based on the specifications. "
                "Rely on general SQL and process mining principles to map events, clean data, and construct case keys."
            )
            schemas_instruction = "Use standard tables listed below if they match. If the requirement references other tables/columns not listed below, you are allowed to use them as requested by the user requirements."
        else:
            kb_summary = []
            for p in matched_processes:
                p_desc = f"- Process: {p.get('name')} ({p.get('id')})\n"
                p_desc += f"  Case Key mapping: {p.get('case_definition', {}).get('case_key')} ({p.get('case_definition', {}).get('description')})\n"
                p_desc += "  Standard Activity triggers:\n"
                for act in p.get("activities", []):
                    p_desc += f"    * {act.get('name')}: Triggered by {act.get('source_table')}.{act.get('timestamp_column')} ({act.get('trigger')})\n"
                kb_summary.append(p_desc)
            kb_text = "\n".join(kb_summary)
            schemas_instruction = "Use ONLY these standard source tables and columns when constructing queries. DO NOT hallucinate other tables or columns:"

        # 2. Filter schemas from knowledge base to keep only mentioned or process tables
        import re
        words = set(re.findall(r'\b[A-Za-z0-9_]{3,10}\b', requirement_spec))
        if matched_processes:
            for p in matched_processes:
                for t_name in p.get("source_tables_used", []):
                    words.add(t_name.upper())
                
        tables = kb.get("source_tables", [])
        schema_list = []
        for t in tables:
            table_name = t.get("table", "").upper()
            if table_name in words or table_name.lower() in spec_lower:
                cols = [c.get("column", "") for c in t.get("key_columns", [])]
                schema_list.append(f"- {table_name}: ({', '.join(cols)})")
                
        if not schema_list and matched_processes:
            for t in tables:
                table_name = t.get("table", "").upper()
                if table_name in {"EKKO", "EKPO", "MSEG", "RBKP", "RSEG", "BKPF", "BSEG", "VBAK", "VBAP", "LIKP", "LIPS", "VBRK", "VBRP"}:
                    cols = [c.get("column", "") for c in t.get("key_columns", [])]
                    schema_list.append(f"- {table_name}: ({', '.join(cols)})")
                    
        schemas = "\n".join(schema_list)

        system_prompt = (
            "You are an expert Celonis SQL Developer Agent. Your job is to generate highly optimized transformations.sql "
            "code to prepare data for Celonis Case-Centric Process Mining (CCPM) or Object-Centric Process Mining (OCPM).\n\n"
            "=== DATABASE DIALECT: VERTICA SQL ===\n"
            "Celonis transformation jobs execute on a Vertica database (or transpile Vertica to Spark SQL). You MUST follow Vertica SQL syntax EXACTLY:\n"
            "- DO NOT use TRY_CAST — this function does NOT exist in Vertica. Using it will cause a syntax error.\n"
            "- DO NOT use CREATE VIEW or CREATE TEMPORARY VIEW. Use CREATE TABLE <name> AS SELECT ... instead.\n"
            "- DO NOT use DROP TABLE <name>; use DROP TABLE IF EXISTS <name>; before every CREATE TABLE.\n"
            "\n"
            "=== VERTICA SAFE CASTING & DATA TYPES ===\n"
            "- Castings: Use CAST(expression AS data_type) or double-colon shorthand expression::data_type. Keep SAP doc numbers as VARCHAR always.\n"
            "- Timestamps/Dates: TO_TIMESTAMP(col, 'yyyy-MM-dd HH:mm:ss') or TO_TIMESTAMP(col, 'yyyy-MM-dd')\n"
            "  -- Use lowercase 'yyyy-MM-dd HH:mm:ss' or 'yyyy-MM-dd' patterns for Spark >= 3.0 compatibility (never uppercase 'YYYY' or 'DD', and do NOT use 'HH24', 'MI', or 'SS' in uppercase). This is compatible with both Vertica and Spark.\n"
            "  -- Keep columns nullable. Do NOT use COALESCE with fallback/dummy dates like '1900-01-01' for timestamps or key dates. If a date is null, let it be null.\n"
            "  -- Do NOT use NULLIF or TRIM inside TO_TIMESTAMP or TO_DATE. Instead, filter out null/empty timestamps from the query entirely using: WHERE col IS NOT NULL AND col <> ''\n"
            "  -- If column is already DATE or TIMESTAMP type: col::TIMESTAMP\n"
            "- Numeric / decimal: COALESCE(NULLIF(TRIM(col), '')::DECIMAL(15,2), 0.0)\n"
            "- Integer / bigint: COALESCE(NULLIF(TRIM(col), '')::BIGINT, 0)\n"
            "- Strings: Keep VARCHAR/CHAR columns safe with COALESCE(col, '') or just col.\n"
            "- Booleans: Use BOOLEAN (supports TRUE, FALSE, NULL).\n"
            "- NULL Handling: Use 'col IS NULL' or 'col IS NOT NULL' instead of = NULL or <> NULL.\n"
            "\n"
            "=== VERTICA DATE & UTILITY FUNCTIONS ===\n"
            "  TO_TIMESTAMP(str, fmt)    — parse string to timestamp\n"
            "  TO_DATE(str, fmt)         — parse string to date\n"
            "  TO_CHAR(ts, fmt)          — convert date/timestamp to formatted string\n"
            "  ADD_MONTHS(date, n)       — add n months to a date\n"
            "  DATE_TRUNC('unit', date)  — truncate date to precision (e.g. 'month', 'day')\n"
            "  DATE_PART('unit', ts)     — extract subfield (e.g., 'year', 'month', 'day')\n"
            "  DATEDIFF('unit', ts1, ts2)— date difference in units ('day', 'month', etc.)\n"
            "  NOW() / CURRENT_TIMESTAMP — current system date/timestamp\n"
            "  CURRENT_DATE              — current system date\n"
            "  INTERVAL math             — e.g., date_column + INTERVAL '1 day' or date_column - INTERVAL '1 month'\n"
            "\n"
            "=== CCPM (Case-Centric Process Mining) RULES ===\n"
            "- Creates a traditional Case table (e.g. O2C_CASES) and an Event Log table (e.g. O2C_EVENT_LOG).\n"
            "- The Cases Table (e.g., P2P_CASES, O2C_CASES) MUST contain both the CASE_ID column and all constituent source key columns as individual columns (e.g., if CASE_ID is 'EBELN-EBELP', select both EBELN and EBELP as separate columns). This is required so the Data Model Agent can construct valid joins to other tables.\n"
            "- DO NOT use a single massive query with UNION ALL to build the entire event log.\n"
            "- First, create the empty event log table with standard columns:\n"
            "  `CREATE TABLE <event_log_table> (CASE_ID VARCHAR(255), ACTIVITY VARCHAR(255), EVENT_TIME TIMESTAMP, USER_NAME VARCHAR(255), AMOUNT DECIMAL(15,2));`\n"
            "- Then, for each activity, write a separate INSERT INTO statement:\n"
            "  `INSERT INTO <event_log_table> SELECT <columns> FROM <source_table> WHERE ...;`\n"
            "- The Event Log table requires fields: CASE_ID, ACTIVITY, EVENT_TIME, USER_NAME, AMOUNT.\n"
            "\n"
            "=== OCPM (Object-Centric Process Mining) RULES ===\n"
            "- Prepares normalized object tables (e.g. Sales_Order, Invoice, Item) and event tables linked to objects.\n"
            "- Focuses on many-to-many relationships without flattening into a single Case ID.\n"
            "\n"
            "=== SQL STRUCTURE RULES ===\n"
            "- First: DROP TABLE IF EXISTS <name>; for each output table.\n"
            "- For Event Logs: Create the empty table first, then run separate INSERT INTO queries for each activity step.\n"
            "- For other tables (like Cases table): create them separately with CREATE TABLE <name> AS SELECT ... ;\n\n"
            "=== AVAILABLE SOURCE TABLES & SCHEMAS ===\n"
            f"{schemas_instruction}\n"
            f"{schemas}\n\n"
            "=== SAP PROCESS MINING KNOWLEDGE BASE ===\n"
            "Refer to these standard SAP activity triggers, case mappings, and table relations for guidance:\n"
            f"{kb_text}\n\n"
            "=== OUTPUT FORMAT ===\n"
            "Format the output strictly as:\n"
            "---SQL---\n"
            "<Valid, syntax-valid SQL queries containing table definitions, cleaning, and UNION structure for the event log>\n"
            "---RATIONALE---\n"
            "<Your explanation of mapping rules, joins, derived columns, and data cleaning rules. KEEP THIS EXTREMELY BRIEF (under 4 sentences) to avoid token limits!>\n\n"
            "Ensure the SQL:\n"
            "- Defines staging tables: use CREATE TABLE <name> AS SELECT ... instead of views.\n"
            "- Performs proper cleaning (handling null values, converting timestamps).\n"
            "- Maps fields into a standard event log structure (Case ID, Activity Name, Event Time, User/Resource, Amount, Sorting index).\n"
            "- Supports either traditional case-based process mining (CCPM) or object-centric event tables (OCPM)."
        )

        prompt = f"Based on the following process mining specification, generate the SQL transformations:\n\n{requirement_spec}"

        response, model_used = self.invoke(system_prompt, prompt)
        
        rationale, sql_content = self._parse_structured_response(response)
        return rationale, sql_content

    def fix_error(self, requirement_spec: str, failing_sql: str, error_msg: str) -> tuple[str, str]:
        kb = self._load_sap_knowledge_base()
        
        # 1. Match process based on keywords
        processes = kb.get("processes", [])
        matched_processes = []
        spec_lower = requirement_spec.lower()
        for p in processes:
            name_lower = p.get("name", "").lower()
            id_lower = p.get("id", "").lower()
            module_lower = p.get("sap_module", "").lower()
            synonyms = []
            if id_lower == "p2p":
                synonyms = ["purchase-to-pay", "purchase to pay", "procurement", "po", "ekko", "ekpo", "p2p", "purchase order"]
            elif id_lower == "o2c":
                synonyms = ["order-to-cash", "order to cash", "sales", "so", "vbak", "vbap", "o2c", "sales order"]
            elif id_lower == "ap":
                synonyms = ["accounts payable", "ap", "vendor invoice", "bkpf", "bseg", "miro", "invoice verification"]
            elif id_lower == "ar":
                synonyms = ["accounts receivable", "ar", "customer invoice", "billing", "vbrk", "vbrp"]
                
            is_match = False
            if id_lower in spec_lower or name_lower in spec_lower or module_lower in spec_lower:
                is_match = True
            else:
                for syn in synonyms:
                    if syn in spec_lower:
                        is_match = True
                        break
            if is_match:
                matched_processes.append(p)
                
        # Fallback to dynamic custom modeling if no standard process was matched
        if not matched_processes:
            kb_text = (
                "The process spec describes a custom process not predefined in the standard SAP knowledge base. "
                "Please generate the SQL transformations dynamically based on the specifications. "
                "Rely on general SQL and process mining principles to map events, clean data, and construct case keys."
            )
            schemas_instruction = "Use standard tables listed below if they match. If the requirement references other tables/columns not listed below, you are allowed to use them as requested by the user requirements."
        else:
            kb_summary = []
            for p in matched_processes:
                p_desc = f"- Process: {p.get('name')} ({p.get('id')})\n"
                p_desc += f"  Case Key mapping: {p.get('case_definition', {}).get('case_key')} ({p.get('case_definition', {}).get('description')})\n"
                p_desc += "  Standard Activity triggers:\n"
                for act in p.get("activities", []):
                    p_desc += f"    * {act.get('name')}: Triggered by {act.get('source_table')}.{act.get('timestamp_column')} ({act.get('trigger')})\n"
                kb_summary.append(p_desc)
            kb_text = "\n".join(kb_summary)
            schemas_instruction = "Use ONLY these standard source tables and columns when constructing queries. DO NOT hallucinate other tables or columns:"

        # 2. Filter schemas
        import re
        words = set(re.findall(r'\b[A-Za-z0-9_]{3,10}\b', requirement_spec))
        if matched_processes:
            for p in matched_processes:
                for t_name in p.get("source_tables_used", []):
                    words.add(t_name.upper())
                
        tables = kb.get("source_tables", [])
        schema_list = []
        for t in tables:
            table_name = t.get("table", "").upper()
            if table_name in words or table_name.lower() in spec_lower:
                cols = [c.get("column", "") for c in t.get("key_columns", [])]
                schema_list.append(f"- {table_name}: ({', '.join(cols)})")
                
        if not schema_list and matched_processes:
            for t in tables:
                table_name = t.get("table", "").upper()
                if table_name in {"EKKO", "EKPO", "MSEG", "RBKP", "RSEG", "BKPF", "BSEG", "VBAK", "VBAP", "LIKP", "LIPS", "VBRK", "VBRP"}:
                    cols = [c.get("column", "") for c in t.get("key_columns", [])]
                    schema_list.append(f"- {table_name}: ({', '.join(cols)})")
                    
        schemas = "\n".join(schema_list)

        # ── Diagnose known error patterns and inject targeted fix guidance ─────
        error_guidance = ""

        if "CAST_INVALID_INPUT" in error_msg or "cannot be cast" in error_msg.lower():
            error_guidance = (
                "\n=== CRITICAL: CAST_INVALID_INPUT FIX RULES (Vertica) ===\n"
                "DO NOT use TRY_CAST — it does not exist in Vertica.\n"
                "Use the following Vertica-compatible safe cast patterns:\n"
                "1. For numeric columns (NETWR, DMBTR, WRBTR, MENGE, NETPR, etc.):\n"
                "   COALESCE(NULLIF(TRIM(col), '')::DECIMAL(15,2), 0.0)\n"
                "   COALESCE(NULLIF(TRIM(col), '')::BIGINT, 0)\n"
                "2. For timestamp / date columns:\n"
                "   TO_TIMESTAMP(col, 'yyyy-MM-dd HH:mm:ss') or TO_TIMESTAMP(col, 'yyyy-MM-dd')\n"
                "   -- DO NOT use COALESCE with dummy default values like '1900-01-01' for event timestamps or key dates.\n"
                "   -- If the date is null or empty, it should be kept as NULL. Filter out rows with NULL/empty timestamps from the event log entirely using 'WHERE col IS NOT NULL AND col <> '''.\n"
                "   -- Do NOT use NULLIF or TRIM inside TO_TIMESTAMP.\n"
                "3. SAP document number fields (VBELN, EBELN, BELNR, MATNR, KUNNR, LIFNR, AUFNR):\n"
                "   Keep as VARCHAR — do NOT cast to numeric.\n"
                "Apply these patterns to every failing CAST expression in the SQL.\n\n"
            )
        elif "UNRESOLVED_COLUMN" in error_msg:
            # Extract the suggestion from the error if present
            import re as _re
            suggestions = _re.findall(r'\[`([^`]+)`\]', error_msg)
            suggestion_hint = (
                f" Use one of these suggested names instead: {suggestions}."
                if suggestions else ""
            )
            error_guidance = (
                "\n=== CRITICAL: UNRESOLVED_COLUMN FIX RULES ===\n"
                f"A column name referenced in the SQL does not exist in that table.{suggestion_hint}\n"
                "Fix rules:\n"
                "1. If the error message suggests alternative names, rename the column to one of those.\n"
                "2. If the column does not exist at all, replace it with "
                "CAST(NULL AS VARCHAR(100)) AS col_name or remove it.\n"
                "3. Do NOT add WHERE clauses or change the table structure.\n\n"
            )
        elif "TABLE_OR_VIEW_NOT_FOUND" in error_msg:
            error_guidance = (
                "\n=== CRITICAL: TABLE_OR_VIEW_NOT_FOUND FIX RULES ===\n"
                "A source table referenced in FROM or JOIN does not exist in the database.\n"
                "Fix rules:\n"
                "1. Change any INNER JOIN to LEFT JOIN for the missing table so the query still runs.\n"
                "2. Replace columns from the missing table with NULL literals: "
                "CAST(NULL AS VARCHAR(100)) AS col_name.\n"
                "3. If the missing table is in a DROP/CREATE statement, add IF EXISTS to the DROP.\n"
                "4. Do NOT try to CREATE the missing source table — only fix the SELECT query.\n\n"
            )
        elif "AMBIGUOUS_REFERENCE" in error_msg or "ambiguous" in error_msg.lower():
            error_guidance = (
                "\n=== CRITICAL: AMBIGUOUS_REFERENCE FIX RULES ===\n"
                "A column or function reference is ambiguous because it exists in multiple source tables or conflicts with column names.\n"
                "Fix rules:\n"
                "1. If using the current date function (CURRENT_DATE), use CURRENT_DATE() with parentheses so it is resolved as a function rather than a column.\n"
                "2. Otherwise, explicitly qualify the ambiguous column with its table name or table alias (e.g., table_alias.column_name).\n\n"
            )
        elif "DATETIME_PATTERN_RECOGNITION" in error_msg or "DateTimeFormatter" in error_msg:
            error_guidance = (
                "\n=== CRITICAL: DATETIME_PATTERN_RECOGNITION FIX RULES ===\n"
                "Spark >= 3.0 requires lowercase 'yyyy-MM-dd' or 'yyyyMMdd' or 'yyyy-MM-dd HH:mm:ss' for date/timestamp patterns, NOT uppercase 'YYYY-MM-DD' or 'YYYYMMDD' or 'HH24:MI:SS'.\n"
                "Fix rules:\n"
                "1. Replace all 'YYYY-MM-DD' or 'YYYYMMDD' patterns with 'yyyy-MM-dd' or 'yyyyMMdd' inside TO_TIMESTAMP or TO_DATE.\n"
                "2. Ensure year is 'yyyy', month is 'MM', day is 'dd' (case sensitive), hour is 'HH' (24-hour hour), minutes is 'mm' (lowercase), seconds is 'ss' (lowercase).\n\n"
            )
        elif "CANNOT_PARSE_TIMESTAMP" in error_msg or "could not be parsed" in error_msg.lower():
            error_guidance = (
                "\n=== CRITICAL: CANNOT_PARSE_TIMESTAMP FIX RULES ===\n"
                "A timestamp string could not be parsed in Vertica/Spark because the pattern does not match the text shape or format.\n"
                "Fix rules:\n"
                "1. If the timestamp string contains space and time (e.g. '2024-01-15 00:00:00'), use 'yyyy-MM-dd HH:mm:ss' pattern inside TO_TIMESTAMP.\n"
                "2. If it is a date-only string (e.g. '2024-01-15'), use 'yyyy-MM-dd' pattern inside TO_DATE or TO_TIMESTAMP.\n"
                "3. Do NOT use NULLIF or TRIM inside TO_TIMESTAMP. Filter out invalid/empty strings beforehand using 'WHERE col IS NOT NULL AND col <> '''.\n"
                "4. Alternatively, if the column is already a TIMESTAMP/DATE type in the database, just cast it directly: column::TIMESTAMP without TO_TIMESTAMP/TO_DATE.\n\n"
            )

        system_prompt = (
            "You are an expert Celonis SQL Developer Agent. Your job is to fix a failing transformations.sql query.\n"
            "Below is the original requirements specification, the failing SQL query that was executed, and the error message received from the database.\n"
            "Analyze the error carefully, fix the syntax or structural issues, and output the corrected SQL.\n\n"
            "=== DATABASE DIALECT: VERTICA SQL ===\n"
            "Celonis transformation jobs execute on a Vertica database. You MUST follow Vertica SQL syntax EXACTLY:\n"
            "- DO NOT use TRY_CAST or try_to_timestamp — these functions do NOT exist in Vertica. Remove or replace every TRY_CAST or try_to_timestamp.\n"
            "- DO NOT use CREATE VIEW or CREATE TEMPORARY VIEW. Use CREATE TABLE <name> AS SELECT ... instead.\n"
            "- Always add DROP TABLE IF EXISTS <name>; before each CREATE TABLE.\n"
            "\n"
            "=== VERTICA SAFE CASTING & DATA TYPES ===\n"
            "- Castings: Use CAST(expression AS data_type) or double-colon shorthand expression::data_type. Keep SAP doc numbers as VARCHAR always.\n"
            "- Timestamps/Dates: TO_TIMESTAMP(col, 'yyyy-MM-dd HH:mm:ss') or TO_TIMESTAMP(col, 'yyyy-MM-dd')\n"
            "  -- Use lowercase 'yyyy-MM-dd HH:mm:ss' or 'yyyy-MM-dd' patterns for Spark >= 3.0 compatibility (never uppercase 'YYYY' or 'DD', and do NOT use 'HH24', 'MI', or 'SS' in uppercase). This is compatible with both Vertica and Spark.\n"
            "  -- Keep columns nullable. Do NOT use COALESCE with dummy default values like '1900-01-01' for event timestamps or key dates.\n"
            "  -- If the date is null or empty, it should be kept as NULL. Filter out rows with NULL/empty timestamps from the event log entirely using 'WHERE col IS NOT NULL AND col <> '''.\n"
            "  -- Do NOT use NULLIF or TRIM inside TO_TIMESTAMP.\n"
            "  -- If column is already DATE or TIMESTAMP type, cast directly: col::TIMESTAMP\n"
            "- Numeric / decimal: COALESCE(NULLIF(TRIM(col), '')::DECIMAL(15,2), 0.0)\n"
            "- Integer / bigint: COALESCE(NULLIF(TRIM(col), '')::BIGINT, 0)\n"
            "- Strings: Keep VARCHAR/CHAR columns safe with COALESCE(col, '') or just col. Keep SAP doc numbers as VARCHAR always.\n"
            "- Booleans: Use BOOLEAN (supports TRUE, FALSE, NULL).\n"
            "- NULL Handling: Use 'col IS NULL' or 'col IS NOT NULL' instead of = NULL or <> NULL.\n"
            "\n"
            "=== VERTICA DATE & UTILITY FUNCTIONS ===\n"
            "  TO_TIMESTAMP(str, fmt)    — parse string to timestamp\n"
            "  TO_DATE(str, fmt)         — parse string to date\n"
            "  TO_CHAR(ts, fmt)          — convert date/timestamp to formatted string\n"
            "  ADD_MONTHS(date, n)       — add n months to a date\n"
            "  DATE_TRUNC('unit', date)  — truncate date to precision (e.g. 'month', 'day')\n"
            "  DATE_PART('unit', ts)     — extract subfield (e.g., 'year', 'month', 'day')\n"
            "  DATEDIFF('unit', ts1, ts2)— date difference in units ('day', 'month', etc.)\n"
            "  NOW() / CURRENT_TIMESTAMP — current system date/timestamp\n"
            "  CURRENT_DATE              — current system date\n"
            "  INTERVAL math             — e.g., date_column + INTERVAL '1 day' or date_column - INTERVAL '1 month'\n"
            "\n"
            "=== CCPM (Case-Centric Process Mining) RULES ===\n"
            "- Creates a traditional Case table and an Event Log table.\n"
            "- The Cases Table (e.g., P2P_CASES, O2C_CASES) MUST contain both the CASE_ID column and all constituent source key columns as individual columns (e.g., if CASE_ID is 'EBELN-EBELP', select both EBELN and EBELP as separate columns). This is required so the Data Model Agent can construct valid joins to other tables.\n"
            "- DO NOT use a single massive query with UNION ALL to build the entire event log.\n"
            "- First, create the empty event log table with standard columns:\n"
            "  `CREATE TABLE <event_log_table> (CASE_ID VARCHAR(255), ACTIVITY VARCHAR(255), EVENT_TIME TIMESTAMP, USER_NAME VARCHAR(255), AMOUNT DECIMAL(15,2));`\n"
            "- Then, for each activity, write a separate INSERT INTO statement:\n"
            "  `INSERT INTO <event_log_table> SELECT <columns> FROM <source_table> WHERE ...;`\n"
            "- The Event Log table requires fields: CASE_ID, ACTIVITY, EVENT_TIME, USER_NAME, AMOUNT.\n"
            "\n"
            "=== OCPM (Object-Centric Process Mining) RULES ===\n"
            "- Prepares normalized object tables and event tables linked to objects.\n"
            "- Focuses on many-to-many relationships without flattening into a single Case ID.\n"
            "\n"
            "=== AVAILABLE SOURCE TABLES & SCHEMAS ===\n"
            f"{schemas_instruction}\n"
            f"{schemas}\n\n"
            "=== SAP PROCESS MINING KNOWLEDGE BASE ===\n"
            f"{kb_text}\n\n"
            f"{error_guidance}"
            "=== OUTPUT FORMAT ===\n"
            "---SQL---\n"
            "<corrected SQL>\n"
            "---RATIONALE---\n"
            "<brief explanation of what was fixed, max 4 sentences>\n\n"
            "Make sure the SQL handles all columns precisely without syntax errors."
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
        sql_content = ""

        # Scenario A: Strict tags with SQL first, then Rationale
        if "---SQL---" in text and "---RATIONALE---" in text:
            if text.find("---SQL---") < text.find("---RATIONALE---"):
                parts = text.split("---RATIONALE---")
                sql_part = parts[0].replace("---SQL---", "").strip()
                rationale_part = parts[1].strip()
            else:
                parts = text.split("---SQL---")
                rationale_part = parts[0].replace("---RATIONALE---", "").strip()
                sql_part = parts[1].strip()
            sql_content = sql_part
            rationale = rationale_part
        # Scenario B: Strict tags with only SQL tag present
        elif "---SQL---" in text:
            parts = text.split("---SQL---")
            rationale_part = parts[0].replace("---RATIONALE---", "").strip()
            sql_part = parts[1].strip()
            sql_content = sql_part
            rationale = rationale_part
        # Scenario C: Markdown code blocks
        else:
            code_block_match = re.search(r'```sql\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
            if code_block_match:
                sql_content = code_block_match.group(1).strip()
                rationale = text.replace(code_block_match.group(0), "").strip()
            else:
                # Look for first occurrence of sql commands
                sql_keywords = [r'\bselect\b', r'\bcreate\s+view\b', r'\bcreate\s+table\b', r'\bwith\b', r'\bdrop\b']
                first_idx = -1
                for kw in sql_keywords:
                    match = re.search(kw, text, re.IGNORECASE)
                    if match:
                        if first_idx == -1 or match.start() < first_idx:
                            first_idx = match.start()
                if first_idx != -1:
                    sql_content = text[first_idx:].strip()
                    rationale = text[:first_idx].strip()
                else:
                    rationale = text
                    sql_content = ""

        # Clean rationale of tags and markdown headers
        if rationale:
            rationale = rationale.replace("---RATIONALE---", "").strip()
            rationale = re.sub(r'(?i)^###?\s*Rationale\s*', '', rationale).strip()

        # Clean SQL content of tags and code blocks
        if sql_content:
            sql_content = sql_content.strip()
            sql_content = re.sub(r'(?i)^###?\s*SQL\s*', '', sql_content).strip()
            sql_content = re.sub(r'(?i)^\*\*SQL\*\*\s*', '', sql_content).strip()
            
            if sql_content.startswith("```"):
                lines = sql_content.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                sql_content = "\n".join(lines).strip()

        if not sql_content or sql_content.strip() == "":
            sql_content = "-- SQL code empty"
            
        return rationale, sql_content


