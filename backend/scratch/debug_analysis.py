from pycelonis import get_celonis
import json
import logging

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

print("Connecting to Celonis...")
c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
spaces = c.studio.get_spaces()
print("Spaces in Celonis:")
for s in spaces:
    print(f"  - {s.name}")
space = spaces[0] # Select first space for inspection
package = space.get_packages()[0]

print(f"Package: {package.name} (Key: {package.key})")
analyses = package.get_analyses()
if not analyses:
    print("No analyses found!")
    exit()

analysis = analyses[-1]
print(f"Analysis Name: {analysis.name}")
print(f"Analysis Class: {analysis.__class__.__name__}")
print(f"Analysis ID: {analysis.id}")
print(f"Analysis Key: {analysis.key}")

print("\n--- Attributes and Methods of Analysis Object ---")
for attr in dir(analysis):
    if not attr.startswith("_"):
        val = getattr(analysis, attr)
        print(f"  {attr}: {type(val)}")

print("\n--- serialized_content length and type ---")
sc = getattr(analysis, "serialized_content", None)
print(f"Type: {type(sc)}")
print(f"Length: {len(sc) if sc else 0}")

if sc:
    try:
        content = analysis._get_content()
        print("\nSuccessfully parsed with analysis.get_content()!")
        print("Draft ID:", content.draft.id)
        doc = content.draft.document
        print("Document ID:", doc.id)
        print("Document Name:", doc.name)
        print("Sheets count:", len(doc.sheets) if doc.sheets else 0)
        if doc.sheets:
            for i, sheet in enumerate(doc.sheets):
                print(f"  Sheet {i+1} Name: {sheet.name}")
                print(f"  Sheet {i+1} Components count: {len(sheet.components) if sheet.components else 0}")
                if sheet.components:
                    for comp in sheet.components:
                        print(f"    - ID: {comp.id}, Type: {comp.type}, Title: {comp.title}")
                        
        print("\n--- Serialized back to dict via content.dict(by_alias=True) ---")
        import pprint
        pprint.pprint(content.dict(by_alias=True, exclude_unset=True))
    except Exception as parse_err:
        print("Failed to parse via get_content():", parse_err)
        import traceback
        traceback.print_exc()

