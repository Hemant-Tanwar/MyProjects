import json
import re
from app.agents.base_agent import BaseAgent
from app.celonis_knowledge_base import (
    KPI_CATALOG,
    PROCESS_FILTER_TEMPLATES,
    get_kpi_catalog_text,
    build_3_sheet_analysis,
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
          2. Call build_3_sheet_analysis() from celonis_knowledge_base.py to
             build the full 3-sheet layout programmatically using verified
             Celonis API structures.
          3. Return a JSON string that deploy_analysis() can use directly.

        This approach ensures:
          - Sheets use the real Celonis 'contentType' field (not 'type')
          - Process Explorer sheet uses 'processExplorerComponent' at sheet level
          - Process Overview has 'timeUnits' / 'aggregateFunction' fields
          - All component structures are validated against working Celonis examples
        """
        # Parse semantic KPIs and filters from the actual Knowledge Model JSON
        km_kpis = []
        km_filters = []
        try:
            km_data = json.loads(knowledge_model)
            kpi_list = km_data.get("key_performance_indicators", []) or km_data.get("kpis", [])
            for k in kpi_list:
                if k.get("id") and k.get("formula"):
                    km_kpis.append({
                        "id": k.get("id"),
                        "name": k.get("name", k.get("displayName", k.get("id"))),
                        "formula": k.get("formula"),
                        "description": k.get("description", ""),
                        "component_type": "single-kpi"
                    })
            filter_list = km_data.get("filters", []) or km_data.get("process_filters", [])
            for f in filter_list:
                if f.get("id") and f.get("formula"):
                    km_filters.append({
                        "id": f.get("id"),
                        "displayName": f.get("name", f.get("displayName", f.get("id"))),
                        "pql": f.get("formula")
                    })
        except Exception as e:
            import logging
            logging.getLogger("analysis_agent").warning(f"Could not parse Knowledge Model: {e}")

        kb_context = get_kpi_catalog_text()
        if km_kpis:
            kb_context += "\n== SEMANTIC KPIS FROM KNOWLEDGE MODEL (PRIORITY) ==\n"
            for k in km_kpis:
                kb_context += f"  KPI: {k['id']} | {k['name']}\n  PQL: {k['formula']}\n  Type: {k['component_type']}\n\n"

        # ── Step 1: Let LLM choose the process type + relevant KPI/filter IDs ──
        system_prompt = (
            "You are a Celonis Process Analytics Designer. Given a business requirement and "
            "a Knowledge Model, select which KPIs and process filters from the catalog below "
            "are most relevant for this analysis. ALWAYS prioritize utilizing semantic KPIs defined in "
            "the Knowledge Model if they exist.\n\n"
            "=== CELONIS KNOWLEDGE BASE ===\n"
            f"{kb_context}\n\n"
            "=== YOUR TASK ===\n"
            "Output a JSON object with:\n"
            "  process_type: 'P2P', 'O2C', or 'GENERIC'\n"
            "  event_log_table: name of the event log table (e.g. TEMP_P2P_EVENT_LOG or TEMP_O2C_EVENT_LOG)\n"
            "  case_table: name of the case/header table (e.g. TEMP_P2P_CASES or TEMP_O2C_CASES)\n"
            "  process_name: short human-readable process name (e.g. 'Purchase-to-Pay')\n"
            "  selected_kpi_ids: list of KPI id strings from the catalog (max 6)\n"
            "  selected_filter_ids: list of filter name strings from templates (max 3)\n\n"
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
        catalog = km_kpis + KPI_CATALOG.get(process_type, []) + KPI_CATALOG.get("GENERIC", [])
        raw_kpis = []
        if sel_kpi_ids:
            raw_kpis = [k for k in catalog if k["id"] in sel_kpi_ids]
        if not raw_kpis:
            raw_kpis = km_kpis if km_kpis else catalog[:6]

        kpi_items = []
        for k in raw_kpis:
            pql = k.get("formula", "")
            try:
                pql = pql.format(event_log_table=event_log_tbl, case_table=case_tbl, case_col="CASE_KEY")
            except Exception:
                pass
            kpi_items.append({"id": k["id"], "displayName": k["name"], "pql": pql})

        # Resolve filter items from templates
        filter_catalog = {}
        for f in km_filters:
            filter_catalog[f["id"]] = f["pql"]
        ftemplates = PROCESS_FILTER_TEMPLATES.get(process_type, {}) or PROCESS_FILTER_TEMPLATES.get("P2P", {})
        for fid, fpql in ftemplates.items():
            if fid not in filter_catalog:
                filter_catalog[fid] = fpql

        raw_filters = []
        if sel_filter_ids:
            raw_filters = [(fid, filter_catalog[fid]) for fid in sel_filter_ids if fid in filter_catalog]
        if not raw_filters:
            raw_filters = list(filter_catalog.items())[:3]

        filter_items = []
        for fid, fpql in raw_filters:
            try:
                fpql = fpql.format(event_log_table=event_log_tbl, case_table=case_tbl, case_col="CASE_KEY")
            except Exception:
                pass
            # Find display name
            disp_name = next((f["displayName"] for f in km_filters if f["id"] == fid), fid.replace("_", " ").title())
            filter_items.append({"id": fid, "displayName": disp_name, "pql": fpql})

        # ── Step 3: Build 3-sheet analysis using KB builder ────────────────────
        sheets = build_3_sheet_analysis(
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
