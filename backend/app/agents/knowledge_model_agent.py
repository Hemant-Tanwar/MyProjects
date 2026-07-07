import json
from app.agents.base_agent import BaseAgent

class KnowledgeModelAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Knowledge Model Agent")

    def generate(self, requirement_spec: str, data_model: str) -> tuple[str, str]:
        system_prompt = (
            "You are an expert Celonis Knowledge Model Architect. Your job is to define the reusable semantic "
            "layer, business KPIs, dimensions, and filters based on the Celonis data model schema.\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your explanation of business KPI formulas, dimension logic, and PQL syntax decisions>\n"
            "---KNOWLEDGE_MODEL---\n"
            "<Valid JSON configuration describing the Celonis Knowledge Model containing records, KPIs, dimensions, and filter definitions>\n\n"
            "The JSON structure must include:\n"
            "- key_performance_indicators: List of objects containing id, name, formula (PQL syntax, e.g. using KPI(...) or AVG(CALC_THROUGHPUT(...))), description, and unit.\n"
            "- custom_dimensions: List of objects containing id, name, expression, and description.\n"
            "- process_filters: List of objects containing id, name, filter_expression, and description.\n"
            "- business_entities: List of objects containing name, description, and key mappings."
        )

        prompt = (
            f"Specification:\n{requirement_spec}\n\n"
            f"Data Model Schema:\n{data_model}"
        )

        response, model_used = self.invoke(system_prompt, prompt)
        
        rationale, km_content = self._parse_structured_response(response)
        return rationale, km_content

    def _parse_structured_response(self, text: str) -> tuple[str, str]:
        rationale = "No rationale provided."
        km_content = "{}"
        
        if "---RATIONALE---" in text and "---KNOWLEDGE_MODEL---" in text:
            parts = text.split("---KNOWLEDGE_MODEL---")
            rationale_part = parts[0].replace("---RATIONALE---", "").strip()
            km_part = parts[1].strip()
            # Clean possible markdown wrap ```json
            if km_part.startswith("```"):
                lines = km_part.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                km_part = "\n".join(lines).strip()
            return rationale_part, km_part
        else:
            try:
                start_idx = text.find("{")
                end_idx = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    km_content = text[start_idx:end_idx+1]
                    rationale = text[:start_idx].strip()
            except Exception:
                pass
            return rationale, km_content

