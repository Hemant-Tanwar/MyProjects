import json
from app.agents.base_agent import BaseAgent
from app.celonis_knowledge_base import get_kpi_catalog_text, VALID_CELONIS_COMPONENT_TYPES, KPI_CATALOG

class AnalysisAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Analysis Agent")

    def generate(self, requirement_spec: str, knowledge_model: str) -> tuple[str, str]:
        # Inject the Celonis Knowledge Base context so the LLM generates valid component types
        kb_context = get_kpi_catalog_text()
        valid_types_str = ", ".join(VALID_CELONIS_COMPONENT_TYPES.keys())

        system_prompt = (
            "You are an expert Celonis Process Analytics Designer Agent. Your job is to generate a comprehensive "
            "Celonis Analysis dashboard configuration based on the business requirements and Knowledge Model.\n\n"
            "=== CRITICAL: 4-SHEET ANALYSIS LAYOUT ===\n"
            "You MUST design the analysis with exactly 4 sheets in the following order:\n"
            "1. Case Explorer (type='case-explorer'): Celonis built-in case drill-down (components list is empty).\n"
            "2. Process Explorer (type='process-explorer'): Contains a single 'process-explorer' component (w=12, h=12).\n"
            "3. Process Overview (type='process-overview'): Contains KPI cards (w=4, h=3) and an Activity Frequency 'pql-table' (w=12, h=6).\n"
            "4. KPI & Analytics (no type/omit type key): Custom analytics sheet with filters/dropdowns (w=4, h=1), KPI cards (w=4, h=3), and tables (w=12 or w=6).\n\n"
            "=== CRITICAL: VALID CELONIS COMPONENT TYPES ===\n"
            f"Only use these component types inside the sheet components: {valid_types_str}\n"
            "Use 'process-explorer' only inside the Process Explorer sheet components.\n\n"
            "=== CELONIS KNOWLEDGE BASE ===\n"
            f"{kb_context}\n\n"
            "=== OUTPUT FORMAT ===\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your explanation of sheets, KPI bindings, dropdown filters, and table components>\n"
            "---ANALYSIS---\n"
            "<Valid JSON configuration describing the Celonis Analysis structure, sheets, and components>\n\n"
            "The JSON structure must include:\n"
            "- analysis_title: String\n"
            "- sheets: List of objects containing id, name, type (optional), and components.\n"
            "- components inside each sheet: List of chart, filter, or process-explorer objects specifying type (single-kpi, pql-table, dropdown, process-explorer), "
            "bound_kpi_id or bound_filter_id, title, and layout (grid_width, grid_height, x, y, w, h)."
        )

        prompt = (
            f"Specification:\n{requirement_spec}\n\n"
            f"Knowledge Model Layer:\n{knowledge_model}"
        )

        response, model_used = self.invoke(system_prompt, prompt)
        
        rationale, analysis_content = self._parse_structured_response(response)
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
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                analysis_part = "\n".join(lines).strip()
            return rationale_part, analysis_part
        else:
            try:
                start_idx = text.find("{")
                end_idx = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    analysis_content = text[start_idx:end_idx+1]
                    rationale = text[:start_idx].strip()
            except Exception:
                pass
            return rationale, analysis_content

    def _mock_response(self, prompt: str) -> str:
        p_lower = prompt.lower()
        if "o2c" in p_lower or "order-to-cash" in p_lower or "order to cash" in p_lower or "sales" in p_lower:
            mock_analysis = {
                "analysis_title": "Order-to-Cash Monitoring Cockpit",
                "sheets": [
                    {
                        "id": "sheet-case-explorer",
                        "name": "Case Explorer",
                        "type": "case-explorer",
                        "components": []
                    },
                    {
                        "id": "sheet-process-explorer",
                        "name": "Process Explorer",
                        "type": "process-explorer",
                        "components": [
                            {
                                "id": "pe-variant-flow",
                                "type": "process-explorer",
                                "title": "O2C — Process Variant Flow",
                                "eventLogs": [{"eventLog": "TEMP_O2C_EVENT_LOG"}],
                                "layout": {"grid_width": 12, "grid_height": 12, "x": 0, "y": 0, "w": 12, "h": 12}
                            }
                        ]
                    },
                    {
                        "id": "sheet-process-overview",
                        "name": "Process Overview",
                        "type": "process-overview",
                        "components": [
                            {
                                "id": "overview-kpi-throughput",
                                "type": "single-kpi",
                                "title": "Avg Throughput Time (SO -> Ship)",
                                "bound_kpi_id": "THROUGHPUT_TIME_SO_TO_SHIP",
                                "formula": {
                                    "name": "Avg Throughput Time (SO -> Ship)",
                                    "text": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Create Sales Order Item'] TO LAST_OCCURRENCE['Ship Goods'], EVENTTIME('_cel_event_log')))"
                                },
                                "layout": {"grid_width": 4, "grid_height": 3, "x": 0, "y": 0, "w": 4, "h": 3}
                            },
                            {
                                "id": "overview-kpi-touchless",
                                "type": "single-kpi",
                                "title": "Touchless Order Rate",
                                "bound_kpi_id": "TOUCHLESS_ORDER_RATE",
                                "formula": {
                                    "name": "Touchless Order Rate",
                                    "text": "COUNT(CASE WHEN PU_COUNT(TEMP_O2C_CASES, TEMP_O2C_EVENT_LOG.ACTIVITY, TEMP_O2C_EVENT_LOG.USER_NAME = 'SYSTEM') = PU_COUNT(TEMP_O2C_CASES, TEMP_O2C_EVENT_LOG.ACTIVITY) THEN TEMP_O2C_CASES.CASE_KEY END) / COUNT(TEMP_O2C_CASES.CASE_KEY) * 100.0"
                                },
                                "layout": {"grid_width": 4, "grid_height": 3, "x": 4, "y": 0, "w": 4, "h": 3}
                            },
                            {
                                "id": "overview-kpi-so-value",
                                "type": "single-kpi",
                                "title": "Total SO Revenue",
                                "bound_kpi_id": "TOTAL_SO_VALUE",
                                "formula": {
                                    "name": "Total SO Revenue",
                                    "text": "SUM(TEMP_O2C_CASES.SO_AMOUNT)"
                                },
                                "layout": {"grid_width": 4, "grid_height": 3, "x": 8, "y": 0, "w": 4, "h": 3}
                            },
                            {
                                "id": "overview-activity-table",
                                "type": "pql-table",
                                "title": "Process Activity Frequency",
                                "axis0": [{"name": "Activity", "text": "TEMP_O2C_EVENT_LOG.ACTIVITY"}],
                                "axis1": [
                                    {"name": "Occurrence Count", "text": "COUNT(TEMP_O2C_EVENT_LOG.ACTIVITY)", "sorting": "DESC", "sortingIndex": 0},
                                    {"name": "Affected Cases", "text": "COUNT_DISTINCT(TEMP_O2C_EVENT_LOG.CASE_KEY)"}
                                ],
                                "axis2": [],
                                "layout": {"grid_width": 12, "grid_height": 6, "x": 0, "y": 3, "w": 12, "h": 6}
                            }
                        ]
                    },
                    {
                        "id": "sheet-kpi-analytics",
                        "name": "KPI & Analytics",
                        "components": [
                            {
                                "id": "analytics-filter-late",
                                "type": "dropdown",
                                "title": "Show Late Deliveries",
                                "bound_filter_id": "LATE_DELIVERY_FILTER",
                                "filter": {
                                    "name": "Show Late Deliveries",
                                    "text": "FILTER PROCESS OCCURRENCE 'Ship Goods' AFTER 'Create Invoice';"
                                },
                                "layout": {"grid_width": 4, "grid_height": 1, "x": 0, "y": 0, "w": 4, "h": 1}
                            }
                        ]
                    }
                ]
            }
            return (
                "---RATIONALE---\n"
                "Designed a 4-sheet Celonis Analysis layout matching requirements. "
                "Sheet 1 is Case Explorer, Sheet 2 is Process Explorer, Sheet 3 is Process Overview with KPIs and Activity Frequency, "
                "and Sheet 4 is KPI & Analytics with dropdown filter for Late Deliveries.\n"
                "---ANALYSIS---\n" + json.dumps(mock_analysis, indent=2)
            )
        else:
            mock_analysis = {
                "analysis_title": "Purchase-to-Pay Monitoring Cockpit",
                "sheets": [
                    {
                        "id": "sheet-case-explorer",
                        "name": "Case Explorer",
                        "type": "case-explorer",
                        "components": []
                    },
                    {
                        "id": "sheet-process-explorer",
                        "name": "Process Explorer",
                        "type": "process-explorer",
                        "components": [
                            {
                                "id": "pe-variant-flow",
                                "type": "process-explorer",
                                "title": "P2P — Process Variant Flow",
                                "eventLogs": [{"eventLog": "TEMP_P2P_EVENT_LOG"}],
                                "layout": {"grid_width": 12, "grid_height": 12, "x": 0, "y": 0, "w": 12, "h": 12}
                            }
                        ]
                    },
                    {
                        "id": "sheet-process-overview",
                        "name": "Process Overview",
                        "type": "process-overview",
                        "components": [
                            {
                                "id": "overview-kpi-throughput",
                                "type": "single-kpi",
                                "title": "Avg Throughput Time (PO -> GR)",
                                "bound_kpi_id": "THROUGHPUT_TIME_PO_TO_GR",
                                "formula": {
                                    "name": "Avg Throughput Time (PO -> GR)",
                                    "text": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Create Purchase Order Item'] TO LAST_OCCURRENCE['Receive Goods'], EVENTTIME('_cel_event_log')))"
                                },
                                "layout": {"grid_width": 4, "grid_height": 3, "x": 0, "y": 0, "w": 4, "h": 3}
                            },
                            {
                                "id": "overview-kpi-automation",
                                "type": "single-kpi",
                                "title": "Touchless PO Rate",
                                "bound_kpi_id": "AUTOMATION_RATE",
                                "formula": {
                                    "name": "Touchless PO Rate",
                                    "text": "COUNT(CASE WHEN PU_COUNT(TEMP_P2P_CASES, TEMP_P2P_EVENT_LOG.ACTIVITY, TEMP_P2P_EVENT_LOG.USER_NAME = 'SYSTEM') = PU_COUNT(TEMP_P2P_CASES, TEMP_P2P_EVENT_LOG.ACTIVITY) THEN TEMP_P2P_CASES.CASE_KEY END) / COUNT(TEMP_P2P_CASES.CASE_KEY) * 100.0"
                                },
                                "layout": {"grid_width": 4, "grid_height": 3, "x": 4, "y": 0, "w": 4, "h": 3}
                            },
                            {
                                "id": "overview-kpi-po-value",
                                "type": "single-kpi",
                                "title": "Total PO Spend Volume",
                                "bound_kpi_id": "TOTAL_PO_VALUE",
                                "formula": {
                                    "name": "Total PO Spend Volume",
                                    "text": "SUM(TEMP_P2P_CASES.PO_AMOUNT)"
                                },
                                "layout": {"grid_width": 4, "grid_height": 3, "x": 8, "y": 0, "w": 4, "h": 3}
                            },
                            {
                                "id": "overview-activity-table",
                                "type": "pql-table",
                                "title": "Process Activity Frequency",
                                "axis0": [{"name": "Activity", "text": "TEMP_P2P_EVENT_LOG.ACTIVITY"}],
                                "axis1": [
                                    {"name": "Occurrence Count", "text": "COUNT(TEMP_P2P_EVENT_LOG.ACTIVITY)", "sorting": "DESC", "sortingIndex": 0},
                                    {"name": "Affected Cases", "text": "COUNT_DISTINCT(TEMP_P2P_EVENT_LOG.CASE_KEY)"}
                                ],
                                "axis2": [],
                                "layout": {"grid_width": 12, "grid_height": 6, "x": 0, "y": 3, "w": 12, "h": 6}
                            }
                        ]
                    },
                    {
                        "id": "sheet-kpi-analytics",
                        "name": "KPI & Analytics",
                        "components": [
                            {
                                "id": "analytics-filter-maverick",
                                "type": "dropdown",
                                "title": "Show Maverick Buying",
                                "bound_filter_id": "MAVERICK_BUYING_FILTER",
                                "filter": {
                                    "name": "Show Maverick Buying",
                                    "text": "FILTER PROCESS OCCURRENCE 'Receive Invoice' BEFORE 'Create Purchase Order Item';"
                                },
                                "layout": {"grid_width": 4, "grid_height": 1, "x": 0, "y": 0, "w": 4, "h": 1}
                            }
                        ]
                    }
                ]
            }
            return (
                "---RATIONALE---\n"
                "Designed a 4-sheet Celonis Analysis layout matching requirements. "
                "Sheet 1 is Case Explorer, Sheet 2 is Process Explorer, Sheet 3 is Process Overview with KPIs and Activity Frequency, "
                "and Sheet 4 is KPI & Analytics with dropdown filter for Maverick Buying.\n"
                "---ANALYSIS---\n" + json.dumps(mock_analysis, indent=2)
            )
