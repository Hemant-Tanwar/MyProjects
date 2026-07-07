import json
import re
from app.agents.base_agent import BaseAgent
from app.celonis_knowledge_base import (
    KPI_CATALOG,
    PROCESS_FILTER_TEMPLATES,
    get_kpi_catalog_text,
    build_4_sheet_analysis,
)


class AnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Analysis Agent")

    def generate(self, requirement_spec: str, knowledge_model: str) -> tuple[str, str]:
        """
        Generate a Celonis Analysis configuration.

        Strategy:
          1. Ask the LLM to select the right KPI ids and filter ids from the
             Knowledge Base catalog (lightweight task — just IDs, not formulas).
          2. Call build_4_sheet_analysis() from celonis_knowledge_base.py to
             build the full 4-sheet layout programmatically using verified
             Celonis API structures.
          3. Return a JSON string that deploy_analysis() can use directly.

        This approach ensures:
          - Sheets use the real Celonis 'contentType' field (not 'type')
          - Process Explorer sheet uses 'processExplorerComponent' at sheet level
          - Process Overview has 'timeUnits' / 'aggregateFunction' fields
          - All component structures are validated against working Celonis examples
        """
        kb_context = get_kpi_catalog_text()

        # ── Step 1: Let LLM choose the process type + relevant KPI/filter IDs ──
        system_prompt = (
            "You are a Celonis Process Analytics Designer. Given a business requirement and "
            "a Knowledge Model, select which KPIs and process filters from the catalog below "
            "are most relevant for this analysis.\n\n"
            "=== CELONIS KNOWLEDGE BASE ===\n"
            f"{kb_context}\n\n"
            "=== YOUR TASK ===\n"
            "Output a JSON object with:\n"
            "  process_type: 'P2P', 'O2C', or 'GENERIC'\n"
            "  event_log_table: name of the event log table (e.g. TEMP_P2P_EVENT_LOG or TEMP_O2C_EVENT_LOG)\n"
            "  case_table: name of the case/header table (e.g. TEMP_P2P_CASES or TEMP_O2C_CASES)\n"
            "  process_name: short human-readable process name (e.g. 'Purchase-to-Pay')\n"
            "  selected_kpi_ids: list of KPI id strings from the catalog (max 6)\n"
            "  selected_filter_ids: list of filter name strings from PROCESS_FILTER_TEMPLATES (max 3)\n\n"
            "=== OUTPUT FORMAT ===\n"
            "---RATIONALE---\n"
            "<Brief explanation of KPI and filter selections>\n"
            "---ANALYSIS---\n"
            "<JSON object as described above>"
        )

        prompt = (
            f"Specification:\n{requirement_spec}\n\n"
            f"Knowledge Model:\n{knowledge_model}"
        )

        response, _ = self.invoke(system_prompt, prompt)
        rationale, selection_json_str = self._parse_structured_response(response)

        # ── Step 2: Parse LLM selection, resolve KPIs and filters ─────────────
        try:
            selection = json.loads(selection_json_str)
        except Exception:
            selection = {}

        process_type   = selection.get("process_type", "P2P").upper()
        event_log_tbl  = selection.get("event_log_table", "TEMP_P2P_EVENT_LOG")
        case_tbl       = selection.get("case_table", "TEMP_P2P_CASES")
        process_name   = selection.get("process_name", process_type)
        sel_kpi_ids    = selection.get("selected_kpi_ids", [])
        sel_filter_ids = selection.get("selected_filter_ids", [])

        # Resolve KPI items from catalog
        catalog = KPI_CATALOG.get(process_type, []) + KPI_CATALOG.get("GENERIC", [])
        if sel_kpi_ids:
            kpi_items = [
                {"id": k["id"], "displayName": k["name"], "pql": k.get("formula", "")}
                for k in catalog if k["id"] in sel_kpi_ids
            ]
        else:
            # Default: first 6 KPIs from the matching catalog
            kpi_items = [
                {"id": k["id"], "displayName": k["name"], "pql": k.get("formula", "")}
                for k in catalog[:6]
            ]

        # Resolve filter items from templates
        filter_catalog = PROCESS_FILTER_TEMPLATES.get(
            process_type, PROCESS_FILTER_TEMPLATES.get("P2P", {})
        )
        if sel_filter_ids:
            filter_items = [
                {"id": fid, "displayName": fid.replace("_", " ").title(), "pql": filter_catalog.get(fid, "")}
                for fid in sel_filter_ids if fid in filter_catalog
            ]
        else:
            # Default: first 3 filters
            filter_items = [
                {"id": fid, "displayName": fid.replace("_", " ").title(), "pql": fpql}
                for fid, fpql in list(filter_catalog.items())[:3]
            ]

        # ── Step 3: Build 4-sheet analysis using KB builder ────────────────────
        sheets = build_4_sheet_analysis(
            kpi_items=kpi_items,
            filter_items=filter_items,
            event_log_table=event_log_tbl,
            case_table=case_tbl,
            process_name=process_name
        )

        # ── Step 4: Wrap in final analysis config JSON ─────────────────────────
        analysis_config = {
            "analysis_title": f"{process_name} Analysis",
            "process_type":   process_type,
            "event_log_table": event_log_tbl,
            "case_table":     case_tbl,
            "sheets":         sheets,
            "kpi_items":      kpi_items,
            "filter_items":   filter_items
        }

        analysis_content = json.dumps(analysis_config, indent=2)
        return rationale, analysis_content

    def _parse_structured_response(self, text: str) -> tuple[str, str]:
        rationale = "No rationale provided."
        analysis_content = "{}"

        if "---RATIONALE---" in text and "---ANALYSIS---" in text:
            parts = text.split("---ANALYSIS---")
            rationale_part = parts[0].replace("---RATIONALE---", "").strip()
            analysis_part = parts[1].strip()
            # Clean possible markdown wrap ```json
            if analysis_part.startswith("```"):
                lines = analysis_part.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                analysis_part = "\n".join(lines).strip()
            return rationale_part, analysis_part
        else:
            try:
                start_idx = text.find("{")
                end_idx = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    analysis_content = text[start_idx:end_idx + 1]
                    rationale = text[:start_idx].strip()
            except Exception:
                pass
            return rationale, analysis_content
