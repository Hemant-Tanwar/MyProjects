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

    def _mock_response(self, prompt: str) -> str:
        p_lower = prompt.lower()
        if "o2c" in p_lower or "order-to-cash" in p_lower or "order to cash" in p_lower or "sales" in p_lower:
            mock_km = {
                "id": "O2C_Semantic_KM",
                "displayName": "Order-to-Cash Semantic Layer",
                "key_performance_indicators": [
                    {
                        "id": "THROUGHPUT_TIME_SO_TO_SHIP",
                        "name": "Sales Order Item to Shipment Throughput Time",
                        "description": "Calculates the average elapsed time between order creation and physical shipping.",
                        "formula": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Create Sales Order Item'] TO LAST_OCCURRENCE['Ship Goods'], EVENTTIME('_cel_event_log')))",
                        "unit": "Days"
                    },
                    {
                        "id": "TOUCHLESS_ORDER_RATE",
                        "name": "Touchless Sales Order Rate",
                        "description": "Percentage of sales order items processed fully automatically without changes or blocks.",
                        "formula": "COUNT(CASE WHEN PU_COUNT(TEMP_O2C_CASES, TEMP_O2C_EVENT_LOG.ACTIVITY, TEMP_O2C_EVENT_LOG.USER_NAME = 'SYSTEM') = PU_COUNT(TEMP_O2C_CASES, TEMP_O2C_EVENT_LOG.ACTIVITY) THEN TEMP_O2C_CASES.CASE_KEY END) / COUNT(TEMP_O2C_CASES.CASE_KEY) * 100.0",
                        "unit": "%"
                    },
                    {
                        "id": "TOTAL_SO_VALUE",
                        "name": "Total Sales Order Net Value",
                        "description": "Sum of SO line items values.",
                        "formula": "SUM(TEMP_O2C_CASES.SO_AMOUNT)",
                        "unit": "EUR"
                    }
                ],
                "custom_dimensions": [
                    {
                        "id": "CUSTOMER_COUNTRY",
                        "name": "Customer Country Code",
                        "expression": "KNA1.LAND1",
                        "description": "The country where the customer is situated."
                    },
                    {
                        "id": "SO_VALUE_BUCKETS",
                        "name": "Sales Order Value Tier",
                        "expression": "CASE WHEN TEMP_O2C_CASES.SO_AMOUNT > 20000 THEN 'High Value' ELSE 'Standard' END",
                        "description": "Categorizes sales items into value groupings."
                    }
                ],
                "process_filters": [
                    {
                        "id": "LATE_DELIVERY_FILTER",
                        "name": "Late Deliveries",
                        "filter_expression": "FILTER PROCESS OCCURRENCE 'Ship Goods' AFTER 'Create Invoice';",
                        "description": "Filter to view cases where the shipment occurred after invoice registration."
                    }
                ]
            }
            return (
                "---RATIONALE---\n"
                "Formulated specific semantic objects in PQL. "
                "The Throughput Time KPI uses the `CALC_THROUGHPUT` standard function in Celonis, referencing "
                "the first occurrence of Sales Order creation and the last occurrence of shipping. "
                "The Touchless Order Rate KPI utilizes `PU_COUNT` (Process Pull Count) to evaluate whether all events "
                "for a case were performed by a system user (User Name = 'SYSTEM').\n"
                "---KNOWLEDGE_MODEL---\n" + json.dumps(mock_km, indent=2)
            )
        else:
            mock_km = {
                "id": "P2P_Semantic_KM",
                "displayName": "Purchase-to-Pay Semantic Layer",
                "key_performance_indicators": [
                    {
                        "id": "THROUGHPUT_TIME_PO_TO_GR",
                        "name": "PO Item to Goods Receipt Throughput Time",
                        "description": "Calculates the average elapsed time between purchasing items and receiving them.",
                        "formula": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Create Purchase Order Item'] TO LAST_OCCURRENCE['Receive Goods'], EVENTTIME('_cel_event_log')))",
                        "unit": "Days"
                    },
                    {
                        "name": "Automation Rate (Touchless PO)",
                        "id": "AUTOMATION_RATE",
                        "description": "Percentage of PO line items created and processed fully automatically without changes.",
                        "formula": "COUNT(CASE WHEN PU_COUNT(TEMP_P2P_CASES, TEMP_P2P_EVENT_LOG.ACTIVITY, TEMP_P2P_EVENT_LOG.USER_NAME = 'SYSTEM') = PU_COUNT(TEMP_P2P_CASES, TEMP_P2P_EVENT_LOG.ACTIVITY) THEN TEMP_P2P_CASES.CASE_KEY END) / COUNT(TEMP_P2P_CASES.CASE_KEY) * 100.0",
                        "unit": "%"
                    },
                    {
                        "id": "TOTAL_PO_VALUE",
                        "name": "Total Purchase Order Net Value",
                        "description": "Sum of PO line items values.",
                        "formula": "SUM(TEMP_P2P_CASES.PO_AMOUNT)",
                        "unit": "EUR"
                    }
                ],
                "custom_dimensions": [
                    {
                        "id": "VENDOR_COUNTRY",
                        "name": "Vendor Country Code",
                        "expression": "LFA1.LAND1",
                        "description": "The country where the supplier is situated."
                    },
                    {
                        "id": "VALUE_BUCKETS",
                        "name": "Order Value Tier",
                        "expression": "CASE WHEN TEMP_P2P_CASES.PO_AMOUNT > 10000 THEN 'High Value' ELSE 'Standard' END",
                        "description": "Categorizes purchase items into value groupings."
                    }
                ],
                "process_filters": [
                    {
                        "id": "MAVERICK_BUYING_FILTER",
                        "name": "Maverick Buying cases",
                        "filter_expression": "FILTER PROCESS OCCURRENCE 'Receive Invoice' BEFORE 'Create Purchase Order Item';",
                        "description": "Filter to view cases where the supplier invoice was registered prior to PO authorization."
                    }
                ]
            }
            return (
                "---RATIONALE---\n"
                "Formulated specific semantic objects in PQL. "
                "The Throughput Time KPI uses the `CALC_THROUGHPUT` standard function in Celonis, referencing "
                "the first occurrence of PO item creation and the last occurrence of Goods Receipt. "
                "The Automation Rate KPI utilizes `PU_COUNT` (Process Pull Count) to evaluate whether all events "
                "for a case were performed by a system user (User Name = 'SYSTEM').\n"
                "---KNOWLEDGE_MODEL---\n" + json.dumps(mock_km, indent=2)
            )
