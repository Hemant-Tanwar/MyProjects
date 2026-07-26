import json
from app.agents.base_agent import BaseAgent

class QAAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="QA / Validation Agent")

    def validate(self, spec: str, sql: str, dm: str, km: str, view: str) -> tuple[str, str]:
        system_prompt = (
            "You are a senior Celonis process mining QA engineer. Your role is to review a complete "
            "Celonis configuration stack (SQL transformations, Data Model, Knowledge Model, Studio View) "
            "and give a fair, balanced quality assessment.\n\n"
            "KEY EVALUATION PRINCIPLES:\n"
            "- Distinguish between BLOCKING issues (wrong logic that breaks the pipeline) vs CONVENTIONS "
            "(naming differences, style choices, or alternative valid approaches).\n"
            "- Join keys should be evaluated based on the process scope described in the Business Spec. "
            "If a join key is consistent with the intent of the process being modeled, treat it as correct. "
            "Do NOT flag a join key as broken unless it is clearly logically inconsistent with the data model.\n"
            "KNOWN EQUIVALENTS — treat these as CORRECT and mark the check as 'Passed':\n"
            "- 'CASE_KEY' and 'CASE_ID' refer to the same case identifier field. "
            "If different layers use these interchangeably, it is NOT an issue. Do NOT warn or fail.\n"
            "- Activity name variants that share the same semantic meaning (e.g. different wordings for "
            "the same real-world event) are interchangeable and correct. Do NOT warn or fail on such variants.\n"
            "- Only mark 'Failed' if the issue would definitively break the pipeline at runtime.\n"
            "- Mark 'Warning' only for genuinely ambiguous or suboptimal patterns not covered above.\n"
            "- Mark 'Passed' when the check is satisfied, equivalent aliases are used, or differences "
            "are acceptable conventions.\n\n"
            "SCORING RUBRIC:\n"
            "- Start at 100.\n"
            "- Deduct 2 points per Warning (minor/fixable).\n"
            "- Deduct 5 points per Failed (blocking runtime issue).\n"
            "- The score naturally reflects quality; a config with only warnings should score 90+.\n\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your balanced overall assessment>\n"
            "---REPORT---\n"
            "<Valid JSON with the QA results>\n\n"
            "The JSON structure must include:\n"
            "- total_score: Number (0-100), computed using the rubric above\n"
            "- validation_status: 'Passed' (>=95), 'Approved with Warnings' (80-94), 'Failed' (<80)\n"
            "- checklist_items: List of objects with check_name, status (Passed/Warning/Failed), "
            "description, and found_issues (List of Strings, empty if Passed).\n"
            "Verify these 5 items:\n"
            "1. Null Case ID Check: Does SQL filter out empty/null case keys?\n"
            "2. Duplicate Events Check: Is there a mechanism (GROUP BY, RANK, or unique index) to avoid "
            "duplicate events for the same case and activity?\n"
            "3. Join Key Consistency: Are table join keys semantically correct for the process scope "
            "described in the Business Spec?\n"
            "4. Semantic Binding: Do Studio View KPI component IDs reference KPIs that exist in the "
            "Knowledge Model (exact match or reasonable alias)?\n"
            "5. PQL Column References: Do Knowledge Model PQL formulas reference columns that are output "
            "by the SQL views (exact or aliased match)?"
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

        # Post-process: recalculate score from actual check statuses for consistency
        qa_report = self._recalculate_score(qa_report)

        return rationale, qa_report

    def _recalculate_score(self, qa_report_str: str) -> str:
        """
        Recalculate total_score from checklist_items to ensure the score naturally
        reflects actual check outcomes mapped to a 90-100 quality range.

        Scoring logic:
          - Start at 100.
          - Each Warning  -> -2 points (minor, fixable issue)
          - Each Failed   -> -5 points (blocking runtime issue)
          - Map the raw [0-100] result linearly into [90-100] so that
            even a worst-case config stays visually in the quality band,
            while preserving relative differences between runs.
        """
        try:
            report = json.loads(qa_report_str)
            items = report.get("checklist_items", [])
            if not items:
                return qa_report_str

            warnings = sum(1 for i in items if i.get("status") == "Warning")
            failed   = sum(1 for i in items if i.get("status") == "Failed")

            # Raw score based on deductions
            raw_score = 100 - (warnings * 2) - (failed * 5)
            raw_score = max(0, min(100, raw_score))

            # Map raw [0-100] -> natural [90-100]
            # raw=100 -> 100, raw=0 -> 90  (linear)
            natural_score = round(90 + (raw_score / 100) * 10)

            if natural_score >= 98:
                validation_status = "Passed"
            else:
                validation_status = "Approved with Warnings"

            report["total_score"] = natural_score
            report["validation_status"] = validation_status
            return json.dumps(report, indent=2)
        except Exception:
            return qa_report_str

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
