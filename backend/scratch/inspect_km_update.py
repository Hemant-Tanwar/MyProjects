from pycelonis.ems.studio.content_node.knowledge_model import KnowledgeModel
import inspect

print("=== KnowledgeModel class methods ===")
for x in dir(KnowledgeModel):
    if not x.startswith("_"):
        try:
            val = getattr(KnowledgeModel, x)
            if callable(val):
                print(f"- [method] {x}{inspect.signature(val)}")
        except Exception:
            pass

print("\n=== KnowledgeModel.update source ===")
try:
    print(inspect.getsource(KnowledgeModel.update))
except Exception as e:
    print("Error:", e)
