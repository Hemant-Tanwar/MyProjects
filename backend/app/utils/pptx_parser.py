import zipfile
import xml.etree.ElementTree as ET
import os

def extract_text_from_pptx(file_path: str) -> str:
    if not file_path or not os.path.exists(file_path):
        return ""
    try:
        texts = []
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Get list of slide files and sort them to read in order
            slide_files = sorted([f for f in zip_ref.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")])
            for slide_file in slide_files:
                slide_xml = zip_ref.read(slide_file)
                root = ET.fromstring(slide_xml)
                # In pptx slide xml, drawing namespace is usually http://schemas.openxmlformats.org/drawingml/2006/main
                ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
                slide_text = []
                for elem in root.findall('.//a:t', ns):
                    if elem.text:
                        slide_text.append(elem.text)
                if slide_text:
                    slide_name = os.path.basename(slide_file).replace(".xml", "")
                    texts.append(f"--- {slide_name.upper()} ---\n" + "\n".join(slide_text))
        return "\n\n".join(texts)
    except Exception as e:
        return f"Error reading PPTX file: {str(e)}"
