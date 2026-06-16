import sys
import os
import json
import yaml

# Add backend directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, SessionModel, ArtifactModel
from pycelonis import get_celonis

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

def slugify(text: str) -> str:
    import re
    text = text.lower()
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return text.strip('_')

def run_push():
    db = SessionLocal()
    try:
        # Get latest session
        sess = db.query(SessionModel).order_by(SessionModel.created_at.desc()).first()
        if not sess:
            print("No sessions found in local database!")
            return
            
        print(f"Retrieving artifacts for session: {sess.name} (ID: {sess.id})")
        stages = ["requirement", "sql", "data_model", "knowledge_model", "view", "qa"]
        bundle = {}
        for stg in stages:
            art = db.query(ArtifactModel).filter(
                ArtifactModel.session_id == sess.id,
                ArtifactModel.stage == stg
            ).order_by(ArtifactModel.version.desc()).first()
            bundle[stg] = art.content if art else ""
            
        print("Connecting to Celonis...")
        celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
        print("Connected successfully!")
        
        # 1. Create/Get Data Pool
        pool_name = sess.name
        print(f"1. Managing Data Pool '{pool_name}'...")
        pools = celonis.data_integration.get_data_pools()
        data_pool = None
        for p in pools:
            if p.name == pool_name:
                data_pool = p
                break
        if not data_pool:
            print(f"Creating new Data Pool: {pool_name}")
            data_pool = celonis.data_integration.create_data_pool(name=pool_name)
        else:
            print(f"Found existing Data Pool: {data_pool.name}")
            
        # 2. Create/Get Data Model in Data Pool
        dm_name = f"{sess.name} Data Model"
        print(f"2. Managing Data Model '{dm_name}'...")
        data_models = data_pool.get_data_models()
        data_model = None
        for dm in data_models:
            if dm.name == dm_name:
                data_model = dm
                break
        if not data_model:
            print(f"Creating new Data Model: {dm_name}")
            data_model = data_pool.create_data_model(name=dm_name)
        else:
            print(f"Found existing Data Model: {data_model.name}")
            
        # 3. Create/Get Data Job
        job_name = f"{sess.name} Data Job"
        print(f"3. Managing Data Job '{job_name}'...")
        jobs = data_pool.get_jobs()
        data_job = None
        for j in jobs:
            if j.name == job_name:
                data_job = j
                break
        if not data_job:
            print(f"Creating new Data Job: {job_name}")
            data_job = data_pool.create_job(name=job_name)
        else:
            print(f"Found existing Data Job: {data_job.name}")
            
        # 4. Create/Update SQL Transformation
        sql_content = bundle.get("sql", "")
        if sql_content:
            print("4. Managing SQL Transformation Task...")
            transformations = data_job.get_transformations()
            task = None
            for t in transformations:
                if t.name == "SQL Transformation":
                    task = t
                    break
            if not task:
                print("Creating new SQL Transformation task...")
                task = data_job.create_transformation(name="SQL Transformation", description="Auto-generated SQL transformations")
            print("Pushing SQL statements to Celonis...")
            task.update_statement(sql_content)
            print("SQL Transformation updated.")
        else:
            print("4. Skipping SQL Transformation (no SQL content generated yet).")
            
        # 5. Create/Get Space
        space_name = f"{sess.name} Space"
        print(f"5. Managing Studio Space '{space_name}'...")
        spaces = celonis.studio.get_spaces()
        space = None
        for s in spaces:
            if s.name == space_name:
                space = s
                break
        if not space:
            print(f"Creating new Space: {space_name}")
            space = celonis.studio.create_space(name=space_name)
        else:
            print(f"Found existing Space: {space.name}")
            
        # 6. Create/Get Package
        pkg_name = f"{sess.name} Package"
        pkg_key = slugify(sess.name).replace("_", "-")
        # Append unique session ID suffix to prevent global package key conflict
        pkg_key = f"{pkg_key}-{sess.id[:8]}"
        print(f"6. Managing Package '{pkg_name}' (Key: {pkg_key})...")
        packages = space.get_packages()
        package = None
        for p in packages:
            if p.key == pkg_key:
                package = p
                break
        if not package:
            print(f"Creating new Package: {pkg_name}")
            package = space.create_package(name=pkg_name, key=pkg_key)
        else:
            print(f"Found existing Package: {package.name}")
            
        # 7. Create/Update Knowledge Model inside Package
        km_json_str = bundle.get("knowledge_model", "{}")
        if km_json_str and km_json_str != "{}":
            print("7. Managing Knowledge Model...")
            try:
                km_obj = json.loads(km_json_str)
            except Exception as e:
                print("Error parsing Knowledge Model JSON, fallback to empty object:", e)
                km_obj = {}
                
            # Use unique session suffix for global keys to avoid key collision
            session_suffix = sess.id[:8]
            km_key = f"{pkg_key}-km-{session_suffix}"
            
            # Map elements into modern KM structure
            mapped_kpis = []
            for item in km_obj.get("key_performance_indicators", []):
                mapped_kpis.append({
                    "id": item.get("id"),
                    "displayName": item.get("name") or item.get("displayName"),
                    "description": item.get("description"),
                    "pql": item.get("formula")
                })
                
            mapped_filters = []
            for item in km_obj.get("process_filters", []):
                mapped_filters.append({
                    "id": item.get("id"),
                    "displayName": item.get("name") or item.get("displayName"),
                    "description": item.get("description"),
                    "pql": item.get("filter_expression")
                })
                
            # Create or recreate package variable 'data-model'
            try:
                for v in package.get_variables():
                    if v.key == "data-model":
                        print("Deleting existing variable 'data-model'...")
                        v.delete()
            except Exception as var_del_err:
                print("Failed to delete variable:", var_del_err)
                
            try:
                package.create_variable(key="data-model", value=data_model.id, type_="DATA_MODEL", runtime=False)
                print("Created variable 'data-model'.")
            except Exception as var_create_err:
                print("Failed to create variable:", var_create_err)

            event_log_id = "TEMP_P2P_EVENT_LOG"
            try:
                for t in data_model.get_tables():
                    tname_up = t.name.upper()
                    if "EVENT" in tname_up or "LOG" in tname_up:
                        event_log_id = t.name
                        break
            except Exception:
                pass

            km_content = {
                "kind": "BASE",
                "metadata": {
                    "key": km_key,
                    "displayName": km_obj.get("displayName", f"{sess.name} Semantic Layer"),
                },
                "dataModelId": "${{data-model}}",
                "kpis": mapped_kpis,
                "filters": mapped_filters,
                "records": [
                    {
                        "id": event_log_id,
                        "displayName": f"{event_log_id.replace('_', ' ').title()} Table",
                        "pql": f'"{event_log_id}"'
                    }
                ],
                "eventLogsMetadata": {
                    "eventLogs": [
                        {
                            "id": event_log_id,
                            "displayName": f"{event_log_id.replace('_', ' ').title()}",
                            "pql": f'"{event_log_id}"."ACTIVITY"',
                            "recordId": event_log_id
                        }
                    ]
                }
            }
            
            # Re-create/update Knowledge Model
            existing_km = None
            kms = package.get_knowledge_models()
            for existing in kms:
                if existing.key == km_key:
                    existing_km = existing
                    break
            
            if existing_km:
                print("Updating existing Knowledge Model...")
                existing_km.serialized_content = yaml.dump(km_content, sort_keys=False)
                existing_km.update()
                knowledge_model = existing_km
            else:
                print("Creating Knowledge Model...")
                knowledge_model = package.create_knowledge_model(content=km_content)
            print("Knowledge Model pushed/updated successfully.")
        else:
            print("7. Skipping Knowledge Model (no knowledge model content yet).")
            knowledge_model = None
            
        # 8. Create/Update View inside Package
        view_json_str = bundle.get("view", "{}")
        if view_json_str and view_json_str != "{}":
            print("8. Managing Studio View...")
            try:
                view_obj = json.loads(view_json_str)
            except Exception as e:
                print("Error parsing View JSON, fallback to empty object:", e)
                view_obj = {}
                
            view_name = view_obj.get("name", f"{sess.name} Dashboard")
            view_key = f"{pkg_key}-view-{sess.id[:8]}"
            
            views = package.get_views()
            for existing_view in views:
                if existing_view.key == view_key or existing_view.name == view_name:
                    print(f"Deleting existing View '{view_key}' to overwrite...")
                    existing_view.delete()
                    
            km_key_arg = knowledge_model.key if knowledge_model else None
            print("Creating Studio View...")
            view = package.create_view(
                name=view_name,
                key=view_key,
                knowledge_model_key=km_key_arg
            )
            
            try:
                components = []
                rows = []
                current_row_cols = []
                current_row_width = 0
                row_count = 1
                
                for tab in view_obj.get("tabs", []):
                    for comp in tab.get("components", []):
                        comp_id = comp.get("id")
                        comp_type_raw = comp.get("type")
                        comp_layout = comp.get("layout", {})
                        try:
                            size = int(comp_layout.get("grid_width", 12))
                        except Exception:
                            size = 12
                        
                        settings = {"title": comp.get("title", "")}
                        
                        if comp_type_raw in ["KPI Value Tile", "KPI Gauge Chart"]:
                            comp_type = "kpi-card"
                            settings["kpi"] = comp.get("bound_kpi_id")
                        elif comp_type_raw == "ProcessExplorer":
                            comp_type = "process-explorer"
                            settings["eventLogs"] = [{"eventLog": event_log_id}]
                        elif comp_type_raw in ["SingleSelectFilter", "Filter"]:
                            comp_type = "dropdown"
                            settings["filter"] = comp.get("bound_filter_id")
                        elif comp_type_raw in ["BarChart", "ColumnChart"]:
                            comp_type = "column-chart"
                            settings["dimension"] = comp.get("dimension")
                            settings["kpi"] = comp.get("kpi")
                        
                        components.append({
                            "id": comp_id,
                            "type": comp_type,
                            "settings": settings
                        })
                        
                        if current_row_width + size > 12:
                            rows.append({
                                "id": f"row-{row_count}",
                                "order": row_count * 100,
                                "columns": current_row_cols
                            })
                            row_count += 1
                            current_row_cols = []
                            current_row_width = 0
                            
                        current_row_cols.append({
                            "id": f"col-{row_count}-{len(current_row_cols)+1}",
                            "size": size,
                            "order": (len(current_row_cols) + 1) * 100,
                            "componentId": comp_id
                        })
                        current_row_width += size
                        
                if current_row_cols:
                    rows.append({
                        "id": f"row-{row_count}",
                        "order": row_count * 100,
                        "columns": current_row_cols
                    })
                    
                view_config = {
                    "metadata": {
                        "key": view_key,
                        "name": view_name,
                        "template": False,
                        "knowledgeModelKey": km_key_arg
                    },
                    "layout": {
                        "rows": rows
                    },
                    "components": components
                }
                
                from pycelonis.service.blueprint.service import Blueprint, BoardAssetType, BoardUpsertRequest
                from pycelonis.service.package_manager.service import ContentNodeTransport
                
                yaml_content = yaml.dump(view_config, sort_keys=False)
                updated_view_blueprint = Blueprint.put_api_boards_board_id(
                    view.client,
                    board_id=view.id,
                    request_body=BoardUpsertRequest(
                        id=view.id,
                        configuration=yaml_content,
                        parent_node_id=view.parent_node_id,
                        parent_node_key=view.parent_node_key,
                        root_node_key=view.root_node_key,
                        board_asset_type=BoardAssetType.BOARD_V2,
                    ),
                    should_activate=True,
                    should_publish=True,
                )
                updated_view_package_manager = ContentNodeTransport(**updated_view_blueprint.json_dict())
                view._update(updated_view_package_manager)
                print("Studio View layout and components successfully populated.")
            except Exception as view_layout_err:
                print("Failed to populate view layout:", view_layout_err)
            print("Studio View pushed successfully.")
        else:
            print("8. Skipping Studio View (no view content yet).")
            
        # 9. Publish Package changes
        print("9. Publishing Package...")
        package.publish(version="1.0.0")
        print("Package published successfully!")
        
        print("\nSUCCESS: All assets successfully created and pushed to Celonis!")
        
    except Exception as e:
        import traceback
        print("\nERROR pushing to Celonis:")
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    run_push()
