# Deployment Runbook - p2p
Promoted by: Admin
QA Validation Score: 100/100
Deployment Timestamp: 2026-06-16T15:15:07.539387

## Promotion Steps:
1. Execute `transformations.sql` in Celonis Event Collection (Data Pool).
2. Map `TEMP_P2P_CASES` (Case Table) and `TEMP_P2P_EVENT_LOG` (Event Table) in Data Model.
3. Create new Knowledge Model package using the defined schema in `knowledge_model.yaml`.
4. Publish Celonis Analysis layout using defined schema in `celonis_analysis_spec.json`.
