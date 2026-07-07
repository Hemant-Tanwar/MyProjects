import json
from app.agents.base_agent import BaseAgent

class DataModelAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Data Model Agent")

    def generate(self, requirement_spec: str, sql_transformations: str) -> tuple[str, str]:
        system_prompt = (
            "You are an expert Celonis Data Architect Agent. Your job is to define the Celonis Data Model "
            "based on SQL staging tables and user specifications.\n\n"
            "=== RELATIONSHIP JOIN RULES ===\n"
            "- A relationship join between the Case Table (e.g., P2P_CASES) and any other source table (e.g., EKKO, EKPO, EKBE) MUST use the correct matching key columns.\n"
            "- DO NOT join CASE_ID directly to a single key (like EBELN or VBELN) if CASE_ID is a composite/concatenated key (like EBELN-EBELP or VBELN-POSNR). This would result in zero matching records.\n"
            "- Instead, use the individual constituent columns (e.g., join P2P_CASES.EBELN to EKKO.EBELN; join P2P_CASES.EBELN and P2P_CASES.EBELP to EKPO.EBELN and EKPO.EBELP respectively).\n"
            "- Celonis Data Model relationships support composite keys or single key columns. Map them precisely to avoid invalid joins.\n\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your explanation of tables, primary keys, foreign keys, and event-to-case cardinality>\n"
            "---MODEL---\n"
            "<Valid JSON configuration describing the Celonis data model schema, relationships, and case table binding>\n\n"
            "The JSON structure must include:\n"
            "- case_table: String (identifying case master table)\n"
            "- event_table: String (identifying event log table)\n"
            "- tables: List of objects containing name, type (Case, Event, Dimension), primary_keys, and description.\n"
            "- relationships: List of objects specifying source_table, target_table, source_column, target_column, and cardinality (e.g. 1:N).\n"
            "- model_type: String (e.g. 'Case-centric' or 'Object-centric')"
        )

        prompt = (
            f"Specification:\n{requirement_spec}\n\n"
            f"SQL Transformations:\n{sql_transformations}"
        )

        response, model_used = self.invoke(system_prompt, prompt)
        
        rationale, model_content = self._parse_structured_response(response)
        return rationale, model_content

    def fix_error(self, requirement_spec: str, sql_transformations: str, failing_model: str, error_msg: str) -> tuple[str, str]:
        system_prompt = (
            "You are an expert Celonis Data Architect Agent. Your job is to fix a failing Celonis Data Model configuration JSON.\n"
            "Below is the original requirements specification, the SQL transformations, the failing Data Model JSON, and the error message received from the platform/database.\n"
            "Analyze the error carefully, fix the structural or semantic issues, and output the corrected rationale and Data Model JSON.\n\n"
            "=== RELATIONSHIP JOIN RULES ===\n"
            "- A relationship join between the Case Table (e.g., P2P_CASES) and any other source table (e.g., EKKO, EKPO, EKBE) MUST use the correct matching key columns.\n"
            "- DO NOT join CASE_ID directly to a single key (like EBELN or VBELN) if CASE_ID is a composite/concatenated key (like EBELN-EBELP or VBELN-POSNR). This would result in zero matching records.\n"
            "- Instead, use the individual constituent columns (e.g., join P2P_CASES.EBELN to EKKO.EBELN; join P2P_CASES.EBELN and P2P_CASES.EBELP to EKPO.EBELN and EKPO.EBELP respectively).\n"
            "- Celonis Data Model relationships support composite keys or single key columns. Map them precisely to avoid invalid joins.\n\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your explanation of the fix and what was corrected. KEEP THIS EXTREMELY BRIEF (under 4 sentences) to avoid token limits!>\n"
            "---MODEL---\n"
            "<Valid JSON configuration describing the Celonis data model schema, relationships, and case table binding>\n\n"
            "The JSON structure must include:\n"
            "- case_table: String (identifying case master table)\n"
            "- event_table: String (identifying event log table)\n"
            "- tables: List of objects containing name, type (Case, Event, Dimension), primary_keys, and description.\n"
            "- relationships: List of objects specifying source_table, target_table, source_column, target_column, and cardinality (e.g. 1:N).\n"
            "- model_type: String"
        )

        prompt = (
            f"### Original Requirements:\n{requirement_spec}\n\n"
            f"### SQL Transformations:\n{sql_transformations}\n\n"
            f"### Failing Data Model JSON:\n```json\n{failing_model}\n```\n\n"
            f"### Error Message:\n{error_msg}\n\n"
            f"Please identify and correct the error in the Data Model configuration JSON."
        )

        response, model_used = self.invoke(system_prompt, prompt)
        rationale, model_content = self._parse_structured_response(response)
        return rationale, model_content

    def _parse_structured_response(self, text: str) -> tuple[str, str]:
        rationale = "No rationale provided."
        model_content = "{}"
        
        if "---RATIONALE---" in text and "---MODEL---" in text:
            parts = text.split("---MODEL---")
            rationale_part = parts[0].replace("---RATIONALE---", "").strip()
            model_part = parts[1].strip()
            # Clean possible markdown wrap ```json
            if model_part.startswith("```"):
                lines = model_part.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                model_part = "\n".join(lines).strip()
            return rationale_part, model_part
        else:
            try:
                start_idx = text.find("{")
                end_idx = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    model_content = text[start_idx:end_idx+1]
                    rationale = text[:start_idx].strip()
            except Exception:
                pass
            return rationale, model_content

