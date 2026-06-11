import json
from app.agents.base_agent import BaseAgent

class DataModelAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Data Model Agent")

    def generate(self, requirement_spec: str, sql_transformations: str) -> tuple[str, str]:
        system_prompt = (
            "You are an expert Celonis Data Architect Agent. Your job is to define the Celonis Data Model "
            "based on SQL staging tables and user specifications.\n"
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

    def _mock_response(self, prompt: str) -> str:
        p_lower = prompt.lower()
        if "o2c" in p_lower or "order-to-cash" in p_lower or "order to cash" in p_lower or "sales" in p_lower:
            mock_model = {
                "model_name": "O2C_Order_to_Cash_Data_Model",
                "model_type": "Case-centric (Process Mining standard)",
                "case_table": "TEMP_O2C_CASES",
                "event_table": "TEMP_O2C_EVENT_LOG",
                "tables": [
                    {
                        "name": "TEMP_O2C_CASES",
                        "type": "Case Table / Master Data",
                        "primary_keys": ["CASE_KEY"],
                        "description": "Sales order items representing the main process cases."
                    },
                    {
                        "name": "TEMP_O2C_EVENT_LOG",
                        "type": "Activity / Event Log Table",
                        "primary_keys": ["CASE_KEY", "ACTIVITY", "SORT_INDEX"],
                        "description": "Process events (SO Creation, Delivery, GI, Invoice, Clearing) with timestamps."
                    },
                    {
                        "name": "KNA1",
                        "type": "Dimension Table (Customer master)",
                        "primary_keys": ["KUNNR"],
                        "description": "Customer master attributes: Name, Country, Account Group."
                    }
                ],
                "relationships": [
                    {
                        "source_table": "TEMP_O2C_CASES",
                        "target_table": "TEMP_O2C_EVENT_LOG",
                        "source_column": "CASE_KEY",
                        "target_column": "CASE_KEY",
                        "cardinality": "1:N",
                        "description": "Every sales order item has zero, one, or multiple transaction activities."
                    },
                    {
                        "source_table": "KNA1",
                        "target_table": "TEMP_O2C_CASES",
                        "source_column": "KUNNR",
                        "target_column": "CUSTOMER_ID",
                        "cardinality": "1:N",
                        "description": "A single customer can place multiple sales orders."
                    }
                ]
            }
            return (
                "---RATIONALE---\n"
                "Configured a case-centric process mining model with `TEMP_O2C_CASES` bound as the Case table, "
                "and `TEMP_O2C_EVENT_LOG` bound as the Event Table. "
                "Primary keys are defined uniquely. A 1:N relationship from `TEMP_O2C_CASES` to `TEMP_O2C_EVENT_LOG` "
                "is mapped on the composite column `CASE_KEY`. Customer master details are connected as a lookup dimension.\n"
                "---MODEL---\n" + json.dumps(mock_model, indent=2)
            )
        else:
            mock_model = {
                "model_name": "P2P_Procurement_Data_Model",
                "model_type": "Case-centric (Process Mining standard)",
                "case_table": "TEMP_P2P_CASES",
                "event_table": "TEMP_P2P_EVENT_LOG",
                "tables": [
                    {
                        "name": "TEMP_P2P_CASES",
                        "type": "Case Table / Master Data",
                        "primary_keys": ["CASE_KEY"],
                        "description": "Purchase order items representing the main process cases."
                    },
                    {
                        "name": "TEMP_P2P_EVENT_LOG",
                        "type": "Activity / Event Log Table",
                        "primary_keys": ["CASE_KEY", "ACTIVITY", "SORT_INDEX"],
                        "description": "Process events (PO Creation, GR, IR, Clearing) with timestamps."
                    },
                    {
                        "name": "LFA1",
                        "type": "Dimension Table (Vendor master)",
                        "primary_keys": ["LIFNR"],
                        "description": "Vendor master attributes: Name, Country, Industry."
                    }
                ],
                "relationships": [
                    {
                        "source_table": "TEMP_P2P_CASES",
                        "target_table": "TEMP_P2P_EVENT_LOG",
                        "source_column": "CASE_KEY",
                        "target_column": "CASE_KEY",
                        "cardinality": "1:N",
                        "description": "Every case has zero, one, or multiple transaction activities."
                    },
                    {
                        "source_table": "LFA1",
                        "target_table": "TEMP_P2P_CASES",
                        "source_column": "LIFNR",
                        "target_column": "VENDOR_ID",
                        "cardinality": "1:N",
                        "description": "A single vendor can be linked to multiple purchase orders."
                    }
                ]
            }
            return (
                "---RATIONALE---\n"
                "Configured a case-centric process mining model with `TEMP_P2P_CASES` bound as the Case table, "
                "and `TEMP_P2P_EVENT_LOG` bound as the Event Table. "
                "Primary keys are defined uniquely. A 1:N relationship from `TEMP_P2P_CASES` to `TEMP_P2P_EVENT_LOG` "
                "is mapped on the composite column `CASE_KEY`. Vendor master details are connected as a lookup dimension.\n"
                "---MODEL---\n" + json.dumps(mock_model, indent=2)
            )
