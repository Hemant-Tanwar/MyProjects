import json
from app.agents.base_agent import BaseAgent

class QAAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="QA / Validation Agent")

    def validate(self, spec: str, sql: str, dm: str, km: str, view: str) -> tuple[str, str]:
        system_prompt = (
            "You are an expert Celonis QA and Validation Agent. Your job is to check the complete "
            "process mining configuration stack (SQL, Data Model, Knowledge Model, and Studio View) "
            "for absolute correctness, consistency, and compliance.\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your overall assessment of data quality, referential integrity, and potential design risks>\n"
            "---REPORT---\n"
            "<Valid JSON configuration describing the QA validation results, pass/fail status, and warnings>\n\n"
            "The JSON structure must include:\n"
            "- total_score: Number (0-100)\n"
            "- validation_status: String (e.g. 'Passed', 'Failed', 'Approved with Warnings')\n"
            "- checklist_items: List of objects containing check_name, status (Passed, Failed, Warning), "
            "description, and found_issues (List of Strings).\n"
            "Verify these items:\n"
            "1. Null Case ID Check: Does SQL filter out empty keys?\n"
            "2. Duplicate Events Check: Do keys have a unique activity/index identifier?\n"
            "3. Broken Joins: Are joining keys correct (e.g. EBELN = EBELN)?\n"
            "4. Semantic Binding: Do Studio View KPI tiles bind to valid IDs in the Knowledge Model?\n"
            "5. PQL References: Do Knowledge Model formulas reference valid columns in SQL view outputs?"
        )

        prompt = (
            f"Business Spec:\n{spec}\n\n"
            f"SQL Transformations:\n{sql}\n\n"
            f"Data Model Schema:\n{dm}\n\n"
            f"Knowledge Model Layer:\n{km}\n\n"
            f"Studio View Layout:\n{view}"
        )

        response, model_used = self.invoke(system_prompt, prompt)
        
        rationale, qa_report = self._parse_structured_response(response)
        return rationale, qa_report

    def _parse_structured_response(self, text: str) -> tuple[str, str]:
        rationale = "No rationale provided."
        qa_report = "{}"
        
        if "---RATIONALE---" in text and "---REPORT---" in text:
            parts = text.split("---REPORT---")
            rationale_part = parts[0].replace("---RATIONALE---", "").strip()
            report_part = parts[1].strip()
            # Clean possible markdown wrap ```json
            if report_part.startswith("```"):
                lines = report_part.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                report_part = "\n".join(lines).strip()
            return rationale_part, report_part
        else:
            try:
                start_idx = text.find("{")
                end_idx = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    qa_report = text[start_idx:end_idx+1]
                    rationale = text[:start_idx].strip()
            except Exception:
                pass
            return rationale, qa_report

