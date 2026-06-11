import json
from app.agents.base_agent import BaseAgent

class ViewAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="View Agent")

    def generate(self, requirement_spec: str, knowledge_model: str) -> tuple[str, str]:
        system_prompt = (
            "You are an expert Celonis Studio View Designer Agent. Your job is to generate a comprehensive "
            "Celonis Studio View dashboard configuration based on the business requirements and Knowledge Model.\n"
            "Format the output strictly as:\n"
            "---RATIONALE---\n"
            "<Your explanation of UI component binding, tab layouts, dashboard filters, and drill-down behaviors>\n"
            "---VIEW---\n"
            "<Valid JSON configuration describing the Celonis Studio View structure, tabs, filters, and components>\n\n"
            "The JSON structure must include:\n"
            "- view_title: String\n"
            "- tabs: List of objects containing id, name, and components.\n"
            "- components: List of chart or filter objects specifying type (KPI, ProcessExplorer, BarChart, SingleSelectFilter), bound_kpi_id, title, and position.\n"
            "- interaction_points: List of objects detailing actions (e.g. email alert, ServiceNow incident trigger)."
        )

        prompt = (
            f"Specification:\n{requirement_spec}\n\n"
            f"Knowledge Model Layer:\n{knowledge_model}"
        )

        response, model_used = self.invoke(system_prompt, prompt)
        
        rationale, view_content = self._parse_structured_response(response)
        return rationale, view_content

    def _parse_structured_response(self, text: str) -> tuple[str, str]:
        rationale = "No rationale provided."
        view_content = "{}"
        
        if "---RATIONALE---" in text and "---VIEW---" in text:
            parts = text.split("---VIEW---")
            rationale_part = parts[0].replace("---RATIONALE---", "").strip()
            view_part = parts[1].strip()
            # Clean possible markdown wrap ```json
            if view_part.startswith("```"):
                lines = view_part.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                view_part = "\n".join(lines).strip()
            return rationale_part, view_part
        else:
            try:
                start_idx = text.find("{")
                end_idx = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    view_content = text[start_idx:end_idx+1]
                    rationale = text[:start_idx].strip()
            except Exception:
                pass
            return rationale, view_content

    def _mock_response(self, prompt: str) -> str:
        p_lower = prompt.lower()
        if "o2c" in p_lower or "order-to-cash" in p_lower or "order to cash" in p_lower or "sales" in p_lower:
            mock_view = {
                "view_title": "Order-to-Cash Monitoring Cockpit",
                "theme": "Dark Mode (Celonis Premium UI)",
                "tabs": [
                    {
                        "id": "OVERVIEW_TAB",
                        "name": "Process Overview",
                        "components": [
                            {
                                "id": "KPI_THROUGHPUT",
                                "type": "KPI Value Tile",
                                "title": "Avg Throughput Time (SO -> Ship)",
                                "bound_kpi_id": "THROUGHPUT_TIME_SO_TO_SHIP",
                                "layout": {"grid_width": 4, "grid_height": 2, "position": "Top-Left"}
                            },
                            {
                                "id": "KPI_TOUCHLESS",
                                "type": "KPI Gauge Chart",
                                "title": "Touchless Order Rate",
                                "bound_kpi_id": "TOUCHLESS_ORDER_RATE",
                                "layout": {"grid_width": 4, "grid_height": 2, "position": "Top-Middle"}
                            },
                            {
                                "id": "KPI_SO_VALUE",
                                "type": "KPI Value Tile",
                                "title": "Total SO Revenue",
                                "bound_kpi_id": "TOTAL_SO_VALUE",
                                "layout": {"grid_width": 4, "grid_height": 2, "position": "Top-Right"}
                            },
                            {
                                "id": "PROCESS_EXPLORER_O2C",
                                "type": "ProcessExplorer",
                                "title": "O2C Process Variant Flow",
                                "source_tables": ["TEMP_O2C_CASES", "TEMP_O2C_EVENT_LOG"],
                                "layout": {"grid_width": 12, "grid_height": 6, "position": "Center"}
                            }
                        ]
                    },
                    {
                        "id": "INEFFICIENCY_ANALYSIS",
                        "name": "Late Deliveries & Bottlenecks",
                        "components": [
                            {
                                "id": "FILTER_LATE",
                                "type": "SingleSelectFilter",
                                "title": "Show Late Deliveries",
                                "bound_filter_id": "LATE_DELIVERY_FILTER",
                                "layout": {"grid_width": 3, "grid_height": 1, "position": "Left-Filter-Bar"}
                            },
                            {
                                "id": "CHART_CUSTOMER_EFFICIENCY",
                                "type": "BarChart",
                                "title": "Revenue by Customer Country",
                                "dimension": "CUSTOMER_COUNTRY",
                                "kpi": "TOTAL_SO_VALUE",
                                "layout": {"grid_width": 9, "grid_height": 4, "position": "Right-Content"}
                            }
                        ]
                    }
                ],
                "interaction_points": [
                    {
                        "trigger_component": "PROCESS_EXPLORER_O2C",
                        "action_name": "Trigger Customer Alert Email",
                        "target_action": "EmailAPI",
                        "recipient_field": "CUSTOMER_NAME",
                        "body_template": "Dear customer, our process mining audit flagged delay in shipment for Sales Order {SO_NUMBER}."
                    }
                ]
            }
            return (
                "---RATIONALE---\n"
                "Designed a dashboard layout in Celonis Studio. "
                "Tab 1 (Process Overview) includes key business metric cards linked directly to Knowledge Model KPI objects "
                "and embeds the standard ProcessExplorer component. "
                "Tab 2 provides inefficiency filters for Late Deliveries and country bar charts.\n"
                "---VIEW---\n" + json.dumps(mock_view, indent=2)
            )
        else:
            mock_view = {
                "view_title": "Purchase-to-Pay Monitoring Cockpit",
                "theme": "Dark Mode (Celonis Premium UI)",
                "tabs": [
                    {
                        "id": "OVERVIEW_TAB",
                        "name": "Process Overview",
                        "components": [
                            {
                                "id": "KPI_THROUGHPUT",
                                "type": "KPI Value Tile",
                                "title": "Avg Throughput Time (PO -> GR)",
                                "bound_kpi_id": "THROUGHPUT_TIME_PO_TO_GR",
                                "layout": {"grid_width": 4, "grid_height": 2, "position": "Top-Left"}
                            },
                            {
                                "id": "KPI_AUTOMATION",
                                "type": "KPI Gauge Chart",
                                "title": "Touchless PO Rate",
                                "bound_kpi_id": "AUTOMATION_RATE",
                                "layout": {"grid_width": 4, "grid_height": 2, "position": "Top-Middle"}
                            },
                            {
                                "id": "KPI_PO_VALUE",
                                "type": "KPI Value Tile",
                                "title": "Total PO Spend Volume",
                                "bound_kpi_id": "TOTAL_PO_VALUE",
                                "layout": {"grid_width": 4, "grid_height": 2, "position": "Top-Right"}
                            },
                            {
                                "id": "PROCESS_EXPLORER_P2P",
                                "type": "ProcessExplorer",
                                "title": "P2P Process Variant flow",
                                "source_tables": ["TEMP_P2P_CASES", "TEMP_P2P_EVENT_LOG"],
                                "layout": {"grid_width": 12, "grid_height": 6, "position": "Center"}
                            }
                        ]
                    },
                    {
                        "id": "INEFFICIENCY_ANALYSIS",
                        "name": "Bottlenecks & Maverick Buying",
                        "components": [
                            {
                                "id": "FILTER_MAVERICK",
                                "type": "SingleSelectFilter",
                                "title": "Show Maverick Buying",
                                "bound_filter_id": "MAVERICK_BUYING_FILTER",
                                "layout": {"grid_width": 3, "grid_height": 1, "position": "Left-Filter-Bar"}
                            },
                            {
                                "id": "CHART_VENDOR_EFFICIENCY",
                                "type": "BarChart",
                                "title": "PO Count by Supplier Country",
                                "dimension": "VENDOR_COUNTRY",
                                "kpi": "TOTAL_PO_VALUE",
                                "layout": {"grid_width": 9, "grid_height": 4, "position": "Right-Content"}
                            }
                        ]
                    }
                ],
                "interaction_points": [
                    {
                        "trigger_component": "PROCESS_EXPLORER_P2P",
                        "action_name": "Trigger Supplier Audit Email",
                        "target_action": "EmailAPI",
                        "recipient_field": "VENDOR_NAME",
                        "body_template": "Dear supplier, our process mining audit flagged delay in goods receipt for PO {PO_NUMBER}."
                    }
                ]
            }
            return (
                "---RATIONALE---\n"
                "Designed a dashboard layout in Celonis Studio. "
                "Tab 1 (Process Overview) includes key business metric cards linked directly to Knowledge Model KPI objects "
                "and embeds the standard ProcessExplorer component. "
                "Tab 2 provides inefficiency filters for Maverick Buying and country bar charts.\n"
                "---VIEW---\n" + json.dumps(mock_view, indent=2)
            )
