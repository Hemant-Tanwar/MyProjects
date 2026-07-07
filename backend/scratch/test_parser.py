import re

def extract_table_columns_from_sql(sql_content: str) -> dict:
    table_to_cols = {}
    
    if not sql_content:
        return table_to_cols
        
    # Find all target tables created in the SQL to exclude them from columns
    target_tables = set()
    target_pattern = re.compile(r'\bCREATE\s+(?:TEMPORARY\s+)?(?:TABLE|VIEW)\s+([a-zA-Z0-9_]+)\b', re.IGNORECASE)
    for m in target_pattern.finditer(sql_content):
        target_tables.add(m.group(1).upper())
        
    # Find all aliases defined in SELECT list (AS alias) to exclude them
    select_aliases = set()
    as_pattern = re.compile(r'\bAS\s+([a-zA-Z0-9_]+)\b', re.IGNORECASE)
    for m in as_pattern.finditer(sql_content):
        # But wait: AS TIMESTAMP (e.g. CAST(x AS TIMESTAMP)) is not an alias!
        # So filter out common type keywords after AS
        alias_upper = m.group(1).upper()
        if alias_upper not in ["TIMESTAMP", "VARCHAR", "INT", "DATE", "DOUBLE", "FLOAT", "STRING", "CHAR"]:
            select_aliases.add(alias_upper)
        
    # Split SQL into select blocks
    statements = sql_content.split(';')
    blocks = []
    for stmt in statements:
        stmt_clean = stmt.strip()
        if not stmt_clean:
            continue
        union_blocks = re.split(r'\bUNION\s+(?:ALL\s+)?', stmt_clean, flags=re.IGNORECASE)
        for ub in union_blocks:
            ub_clean = ub.strip()
            if ub_clean:
                blocks.append(ub_clean)
                
    SQL_KEYWORDS = {
        "SELECT", "FROM", "JOIN", "ON", "WHERE", "AND", "OR", "UNION", "ALL", "AS", 
        "CREATE", "TABLE", "VIEW", "TEMPORARY", "TEMP", "DROP", "IF", "EXISTS", "CAST", 
        "TIMESTAMP", "NULL", "IN", "NOT", "IS", "LEFT", "RIGHT", "INNER", "OUTER", 
        "CROSS", "USING", "GROUP", "BY", "ORDER", "LIMIT", "CASE", "WHEN", "THEN", 
        "ELSE", "END", "LIKE", "DISTINCT", "AVG", "SUM", "COUNT", "MAX", "MIN",
        "COALESCE", "SUBSTRING", "ROUND", "UPPER", "LOWER", "CONCAT", "DATE"
    }

    for block in blocks:
        # Strip string literals to avoid matching words inside quotes
        block_no_literals = re.sub(r"'[^']*'", "", block)
        block_clean = re.sub(r'\s+', ' ', block_no_literals)
        
        # 1. Extract table names in this block
        table_pattern = re.compile(r'\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)\b', re.IGNORECASE)
        block_tables = []
        alias_to_table = {}
        
        for m in table_pattern.finditer(block_clean):
            t_upper = m.group(1).upper()
            if t_upper.startswith("TEMP_"):
                continue
            block_tables.append(t_upper)
            alias_to_table[t_upper] = t_upper
            if t_upper not in table_to_cols:
                table_to_cols[t_upper] = set()
                
            # Find aliases of this table in the block
            alias_pattern = re.compile(rf'\b{t_upper}\s+(?:AS\s+)?([a-zA-Z0-9_]+)\b', re.IGNORECASE)
            for am in alias_pattern.finditer(block_clean):
                alias = am.group(1).upper()
                if alias not in ["ON", "WHERE", "JOIN", "GROUP", "ORDER", "SELECT", "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "CROSS", "USING", "AS"]:
                    alias_to_table[alias] = t_upper

        if not block_tables:
            continue
            
        # 2. Extract prefixed columns in this block
        col_pattern = re.compile(r'\b([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\b')
        for match in col_pattern.finditer(block_clean):
            prefix, col = match.groups()
            p_upper = prefix.upper()
            col_upper = col.upper()
            if p_upper in alias_to_table:
                real_table = alias_to_table[p_upper]
                # Filter out aliases if they matched
                if col_upper not in select_aliases and col_upper not in target_tables:
                    table_to_cols[real_table].add(col_upper)

        # 3. Extract prefix-less words as potential columns in this block
        sql_words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', block_clean)
        potential_cols = set()
        for word in sql_words:
            w_upper = word.upper()
            if w_upper in SQL_KEYWORDS:
                continue
            if w_upper in alias_to_table:
                continue
            if w_upper.startswith("TEMP_"):
                continue
            if w_upper in select_aliases:
                continue
            if w_upper in target_tables:
                continue
            potential_cols.add(w_upper)
            
        # Associate potential cols with all tables found in this block
        for col in potential_cols:
            for t_name in block_tables:
                table_to_cols[t_name].add(col)

    # Ensure every table has at least MANDT if no columns were parsed
    for t_name in table_to_cols:
        if not table_to_cols[t_name]:
            table_to_cols[t_name].add("MANDT")
            
    return table_to_cols

sql = """
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

res = extract_table_columns_from_sql(sql)
print("Parsed tables:")
for k, v in res.items():
    print(f"  {k}: {sorted(list(v))}")
