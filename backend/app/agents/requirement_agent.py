import json
from app.agents.base_agent import BaseAgent

class RequirementAnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Requirement Analyzer Agent")

    def analyze(self, business_requirement: str) -> tuple[str, str]:
        kb = self._load_sap_knowledge_base()
        processes = kb.get("processes", [])
        
        # Match process based on keywords in the business requirement text
        matched_processes = []
        text_lower = business_requirement.lower()
        for p in processes:
            name_lower = p.get("name", "").lower()
            id_lower = p.get("id", "").lower()
            module_lower = p.get("sap_module", "").lower()
            
            # Synonyms mapping to help catch process context
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
            if id_lower in text_lower or name_lower in text_lower or module_lower in text_lower:
                is_match = True
            else:
                for syn in synonyms:
                    if syn in text_lower:
                        is_match = True
                        break
            if is_match:
                matched_processes.append(p)
                
        # Fallback to dynamic custom modeling if no standard process was matched
        if not matched_processes:
            kb_text = (
                "No standard predefined SAP processes match this requirement. "
                "Please analyze this custom business requirement dynamically. Use general process mining best practices "
                "to define the process_name, case_id_definition, activity_definitions, key_timestamp_fields, and KPIs "
                "based entirely on the user's business description."
            )
        else:
            kb_summary = []
            for p in matched_processes:
                p_desc = f"- Process: {p.get('name')} ({p.get('id')}) - Module: {p.get('sap_module')}\n"
                p_desc += f"  Case Key: {p.get('case_definition', {}).get('case_key')} ({p.get('case_definition', {}).get('description')})\n"
                p_desc += "  Standard Activities:\n"
                for act in p.get("activities", []):
                    p_desc += f"    * {act.get('name')}: Triggered by {act.get('source_table')}.{act.get('timestamp_column')} ({act.get('trigger')})\n"
                kb_summary.append(p_desc)
            kb_text = "\n".join(kb_summary)
            
        system_prompt = (
            "You are an expert Celonis Requirement Analyzer Agent. Your job is to parse raw business requirements "
            "(which may include detailed slide contents from PowerPoint/PPTX files) and convert them into a highly "
            "comprehensive Process Mining Specification JSON format.\n\n"
            "=== CRITICAL REQUIREMENTS RULE ===\n"
            "- You MUST read the entire business requirement, including any slides labeled 'ADDITIONAL PPTX REQUIREMENTS'.\n"
            "- Do NOT truncate, ignore, or drop any activities, KPIs, source fields, or business rules mentioned in the slides.\n"
            "- Ensure every activity and data mapping defined in the slides is captured in the activity_definitions and key_timestamp_fields.\n\n"
            "=== PROCESS MINING REFERENCE / SYSTEM INSTRUCTIONS ===\n"
            f"{kb_text}\n\n"
            "=== OUTPUT FORMAT ===\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your explanation and traceability notes here>\n"
            "---SPECIFICATION---\n"
            "<Valid JSON representation>\n\n"
            "The JSON structure must include:\n"
            "- process_name: String\n"
            "- source_systems: List of Strings (e.g. ['SAP', 'Oracle'])\n"
            "- case_id_definition: String (definition of what constitutes a case)\n"
            "- activity_definitions: List of objects containing 'name' and 'trigger_condition'\n"
            "- key_timestamp_fields: List of objects containing 'activity_name' and 'source_field'\n"
            "- kpis: List of objects containing 'name', 'description', and 'calculation_idea'\n"
            "- business_filters: List of objects containing 'name' and 'rule'\n"
            "- acceptance_rules: List of Strings"
        )

        prompt = f"Analyze the following business requirement:\n\n{business_requirement}"

        response, model_used = self.invoke(system_prompt, prompt)
        
        # Parse the structured response
        rationale, spec_json = self._parse_structured_response(response)
        return rationale, spec_json

    def _parse_structured_response(self, text: str) -> tuple[str, str]:
        rationale = "No rationale provided."
        spec = "{}"
        
        if "---RATIONALE---" in text and "---SPECIFICATION---" in text:
            parts = text.split("---SPECIFICATION---")
            rationale_part = parts[0].replace("---RATIONALE---", "").strip()
            spec_part = parts[1].strip()
            # Clean possible markdown wrap ```json
            if spec_part.startswith("```"):
                lines = spec_part.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                spec_part = "\n".join(lines).strip()
            return rationale_part, spec_part
        else:
            # Try to grab JSON if tags aren't perfectly placed
            try:
                start_idx = text.find("{")
                end_idx = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    spec = text[start_idx:end_idx+1]
                    rationale = text[:start_idx].strip()
            except Exception:
                pass
            return rationale, spec

