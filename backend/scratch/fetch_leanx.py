import urllib.request
import re
from html.parser import HTMLParser

class LeanXParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_row = False
        self.in_cell = False
        self.cells = []
        self.current_cell = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_row = True
            self.cells = []
        elif tag == "td" and self.in_row:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_row:
            self.in_row = False
            if self.cells:
                self.rows.append(self.cells)
        elif tag == "td" and self.in_row:
            self.in_cell = False
            self.cells.append(" ".join(self.current_cell).strip())

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data.strip())

def parse_table_schema(html: str):
    parser = LeanXParser()
    parser.feed(html)
    
    schema = {}
    for r in parser.rows:
        # We look for rows that have at least 5 cells
        if len(r) >= 5:
            # Let's inspect the first cell to see if it starts with a valid column name
            first_cell = r[0]
            words = first_cell.split()
            if not words:
                continue
            col_name = words[0]
            # Ensure it looks like a valid SAP column (uppercase letters and numbers, usually 3-10 chars)
            if re.match(r'^[A-Z0-9_\/]{2,30}$', col_name):
                # The data type is usually in the 4th cell (index 3)
                data_type_cell = r[3]
                data_type_words = data_type_cell.split()
                data_type = data_type_words[0] if data_type_words else "CHAR"
                
                # Length is in the 5th cell (index 4)
                length_cell = r[4]
                length_words = length_cell.split()
                length = length_words[0] if length_words else "10"
                
                schema[col_name] = {
                    "type": data_type,
                    "length": length
                }
    return schema

url = "https://leanx.eu/sap/table/ekko"
req = urllib.request.Request(
    url, 
    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
)

try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        schema = parse_table_schema(html)
        print(f"Parsed {len(schema)} columns.")
        # Print a few columns
        for col, info in list(schema.items())[:15]:
            print(f"Column: {col:15} Type: {info['type']:8} Length: {info['length']}")
except Exception as e:
    print(f"Error: {e}")
