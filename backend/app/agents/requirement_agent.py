import json
from app.agents.base_agent import BaseAgent

class RequirementAnalyzerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Requirement Analyzer Agent")

    def analyze(self, business_requirement: str) -> tuple[str, str]:
        system_prompt = (
            "You are an expert Celonis Requirement Analyzer Agent. Your job is to parse raw business requirements "
            "and convert them into a highly structured Process Mining Specification JSON format. "
            "Your output must contain exactly two sections: \n"
            "1. RATIONALE: A concise explanation of your design choices, process identification, and scope.\n"
            "2. SPECIFICATION: A valid JSON object representing the structured process mining requirements.\n"
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

    def _mock_response(self, prompt: str) -> str:
        p_lower = prompt.lower()
        if "o2c" in p_lower or "order-to-cash" in p_lower or "order to cash" in p_lower or "sales" in p_lower:
            mock_spec = {
                "process_name": "Order-to-Cash (O2C) Optimization",
                "source_systems": ["SAP ECC / S4HANA"],
                "case_id_definition": "VBAP.VBELN (Sales Order Document Number) + VBAP.POSNR (Sales Order Line Item Number)",
                "activity_definitions": [
                    {"name": "Create Sales Order Item", "trigger_condition": "Creation of sales order item in VBAP table"},
                    {"name": "Approve Sales Order Item", "trigger_condition": "Credit check release or billing block removal in VBAK / VBUK"},
                    {"name": "Create Delivery Item", "trigger_condition": "Post outbound delivery item in LIPS table"},
                    {"name": "Ship Goods", "trigger_condition": "Goods issue posting in MKPF / MSEG or LIPS.WADAT_IST"},
                    {"name": "Create Invoice", "trigger_condition": "Billing document posting in VBRK / VBRP"},
                    {"name": "Clear Invoice Payment", "trigger_condition": "Customer payment clearing in BSAD / BKPF"}
                ],
                "key_timestamp_fields": [
                    {"activity_name": "Create Sales Order Item", "source_field": "VBAK.ERDAT or CDHDR.UDATE"},
                    {"activity_name": "Approve Sales Order Item", "source_field": "CDHDR.UDATE"},
                    {"activity_name": "Create Delivery Item", "source_field": "LIPS.ERDAT"},
                    {"activity_name": "Ship Goods", "source_field": "LIPS.WADAT_IST"},
                    {"activity_name": "Create Invoice", "source_field": "VBRK.FKDAT"},
                    {"activity_name": "Clear Invoice Payment", "source_field": "BSAD.BUDAT"}
                ],
                "kpis": [
                    {"name": "Order-to-Shipping Throughput Time", "description": "Time elapsed between creating sales order item and shipping goods", "calculation_idea": "AVG(Timestamp(Ship Goods) - Timestamp(Create Sales Order Item))"},
                    {"name": "Touchless Order Rate", "description": "Percentage of sales orders processed without manual touches or billing blocks", "calculation_idea": "COUNT(cases with no changes/blocks) / Total SO Cases"},
                    {"name": "Delivery Delay", "description": "Time delay between planned delivery date and actual goods issue", "calculation_idea": "AVG(Timestamp(Ship Goods) - Timestamp(Planned Delivery Date))"}
                ],
                "business_filters": [
                    {"name": "High Value Sales Orders", "rule": "Sales Order Item net value (VBAP.NETWR) > 20,000 EUR"},
                    {"name": "Late Deliveries", "rule": "Actual Goods Issue (LIPS.WADAT_IST) > Planned Delivery Date (EPAS.MBDAT)"}
                ],
                "acceptance_rules": [
                    "Case ID must never be null",
                    "Activities must follow sequential timestamps (Create SO <= Create Delivery <= Ship Goods <= Create Invoice <= Clear Payment)",
                    "Billing document must reference the sales order item (VBRP.AUBEL = VBAP.VBELN and VBRP.AUPOS = VBAP.POSNR)"
                ]
            }
            return (
                "---RATIONALE---\n"
                "The requirement is mapped to an Order-to-Cash process flow extraction based on typical SAP SD schema constructs. "
                "The Case ID is established at the Line Item level (VBELN + POSNR) because transaction actions occur at the item level. "
                "Identified key entities: VBAK, VBAP, LIPS, VBRK, VBRP, BSAD.\n"
                "---SPECIFICATION---\n" + json.dumps(mock_spec, indent=2)
            )
        else:
            # Generate rich response simulating Bedrock output for a generic P2P process
            mock_spec = {
                "process_name": "Purchase-to-Pay (P2P) Optimization",
                "source_systems": ["SAP ECC / S4HANA"],
                "case_id_definition": "EKPO.EBELN (Purchase Order Document Number) + EKPO.EBELP (Purchase Order Line Item Number)",
                "activity_definitions": [
                    {"name": "Create Purchase Order Item", "trigger_condition": "Creation of purchase order item in EKPO table"},
                    {"name": "Approve Purchase Order Item", "trigger_condition": "Release indicator update in EKKO or CDHDR tracking"},
                    {"name": "Receive Goods", "trigger_condition": "Post goods receipt in MSEG table with transaction type 101"},
                    {"name": "Receive Invoice", "trigger_condition": "Register vendor invoice in RBKP / RSEG tables"},
                    {"name": "Pay Invoice", "trigger_condition": "Clear payment in BSAK / BKPF financial ledger"}
                ],
                "key_timestamp_fields": [
                    {"activity_name": "Create Purchase Order Item", "source_field": "EKKO.AEDAT or CDHDR.UDATE"},
                    {"activity_name": "Approve Purchase Order Item", "source_field": "CDHDR.UDATE"},
                    {"activity_name": "Receive Goods", "source_field": "MSEG.BUDAT"},
                    {"activity_name": "Receive Invoice", "source_field": "RBKP.BUDAT"},
                    {"activity_name": "Pay Invoice", "source_field": "BKPF.BUDAT"}
                ],
                "kpis": [
                    {"name": "PO-to-GR Throughput Time", "description": "Time elapsed between creating PO item and receiving goods", "calculation_idea": "AVG(Timestamp(Receive Goods) - Timestamp(Create Purchase Order Item))"},
                    {"name": "Touchless PO Rate", "description": "Percentage of POs that did not require manual approval changes", "calculation_idea": "COUNT(cases with no changes) / Total PO Cases"},
                    {"name": "Invoice Verification Time", "description": "Time to post an invoice since goods receipt", "calculation_idea": "AVG(Timestamp(Receive Invoice) - Timestamp(Receive Goods))"}
                ],
                "business_filters": [
                    {"name": "High Value Orders", "rule": "PO Item net value (EKPO.NETPR) > 10,000 EUR"},
                    {"name": "Maverick Buying", "rule": "Invoice posting occurs before PO creation date"}
                ],
                "acceptance_rules": [
                    "Case ID must never be null",
                    "Activities must follow sequential timestamps (Create PO <= Receive Goods <= Receive Invoice <= Clear Payment)",
                    "Goods receipt must link to the purchase order reference (MSEG.EBELN = EKPO.EBELN)"
                ]
            }
            return (
                "---RATIONALE---\n"
                "The requirement is mapped to a Purchase-to-Pay process flow extraction based on typical SAP schema constructs. "
                "The Case ID is established at the Line Item level (EBELN + EBELP) because transaction actions occur at the item level. "
                "Identified key entities: EKKO, EKPO, MSEG, RBKP, BSAK.\n"
                "---SPECIFICATION---\n" + json.dumps(mock_spec, indent=2)
            )
