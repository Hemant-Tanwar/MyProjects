import json

knowledge_model_sample = """{
  "key_performance_indicators": [
    {
      "id": "touchless_rate",
      "name": "Touchless Rate",
      "formula": "COUNT_TABLE(AP_CASES) FILTER (NOT FILTER_ACTIVITY('Set Payment Block') AND NOT FILTER_ACTIVITY('Change Invoice')) / COUNT_TABLE(AP_CASES)",
      "description": "Percentage of invoices posted without manual intervention (payment blocks or changes).",
      "unit": "%"
    },
    {
      "id": "cycle_time",
      "name": "Average Cycle Time",
      "formula": "AVG(CALC_THROUGHPUT(FIRST_OCCURRENCE['Invoice Received'] TO LAST_OCCURRENCE['Payment Issued'], REMAP_TIMESTAMPS(\\"AP_EVENT_LOG\\".\\"EVENT_TIME\\", DAYS)))",
      "description": "Average time in days from invoice receipt to payment issuance.",
      "unit": "Days"
    }
  ]
}"""

km_kpis = []
try:
    km_data = json.loads(knowledge_model_sample)
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
except Exception as e:
    print("Error parsing KM:", e)

print("Parsed KM KPIs:")
for k in km_kpis:
    print(f"ID: {k['id']}, Name: {k['name']}, Formula: {k['formula']}")
