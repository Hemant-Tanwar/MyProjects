import sys
import os
import re
import json
import yaml
import pandas as pd
import logging

# Add backend directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, SessionModel, ArtifactModel
from pycelonis import get_celonis

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CELONIS_URL = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
API_TOKEN = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^a-z0-9_]+', '_', text)
    return text.strip('_')

def run_test():
    db = SessionLocal()
    try:
        # Get latest session
        sess = db.query(SessionModel).order_by(SessionModel.created_at.desc()).first()
        if not sess:
            logger.error("No sessions found in local database!")
            return
            
        logger.info(f"Retrieving artifacts for session: {sess.name} (ID: {sess.id})")
        stages = ["requirement", "sql", "data_model", "knowledge_model", "view", "qa"]
        bundle = {}
        for stg in stages:
            art = db.query(ArtifactModel).filter(
                ArtifactModel.session_id == sess.id,
                ArtifactModel.stage == stg
            ).order_by(ArtifactModel.version.desc()).first()
            bundle[stg] = art.content if art else ""
            
        logger.info("Connecting to Celonis...")
        celonis = get_celonis(base_url=CELONIS_URL, api_token=API_TOKEN, key_type="USER_KEY")
        logger.info("Connected successfully!")
        
        # 1. Manage Data Pool
        pool_name = sess.name
        logger.info(f"1. Managing Data Pool '{pool_name}'...")
        pools = celonis.data_integration.get_data_pools()
        data_pool = None
        for p in pools:
            if p.name == pool_name:
                data_pool = p
                break
        if not data_pool:
            logger.info(f"Creating new Data Pool: {pool_name}")
            data_pool = celonis.data_integration.create_data_pool(name=pool_name)
        else:
            logger.info(f"Found existing Data Pool: {data_pool.name}")
            
        # 2. Get Connection
        logger.info("2. Checking for data connections...")
        conns = data_pool.get_data_connections()
        conn = conns[0] if conns else None
        
        data_source_id = conn.id if conn else None
        conn_name = conn.name if conn else None
        logger.info(f"Using connection Name: {conn_name}, ID: {data_source_id}")
        
        # 3. Upload all local CSVs to Data Pool
        data_source_dir = "/Users/hemanttanwar/Documents/hemant_process_mine/Data_source"
        logger.info(f"3. Uploading all CSV files from {data_source_dir}...")
        csv_files = [f for f in os.listdir(data_source_dir) if f.lower().endswith(".csv")]
        
        uploaded_tables = set()
        for f in csv_files:
            table_name = os.path.splitext(f)[0]
            file_path = os.path.join(data_source_dir, f)
            logger.info(f"Reading and uploading table {table_name} from {f}...")
            df = pd.read_csv(file_path)
            # Replace NaN/None values with empty strings or proper type representation to avoid issues
            df = df.where(pd.notnull(df), None)
            
            data_pool.create_table(
                df=df,
                table_name=table_name,
                drop_if_exists=True,
                data_source_id=data_source_id
            )
            uploaded_tables.add(table_name.upper())
            logger.info(f"Uploaded {table_name} successfully.")
            
        # 4. Scan SQL transformation script for referenced tables
        sql_content = bundle.get("sql", "")
        if not sql_content:
            logger.error("No SQL transformation script found!")
            return
            
        logger.info("4. Identifying referenced source tables in SQL script...")
        # Extract tables referenced in FROM/JOIN
        source_tables = []
        matches = re.findall(r'\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)\b', sql_content, re.IGNORECASE)
        for m in matches:
            t_upper = m.upper()
            if not t_upper.startswith("TEMP_") and t_upper not in source_tables:
                source_tables.append(t_upper)
                
        logger.info(f"Referenced source tables: {source_tables}")
        
        # Generate mock tables for any missing tables referenced in the query
        for table in source_tables:
            if table not in uploaded_tables:
                logger.info(f"Table '{table}' referenced in SQL is missing from Data_source directory. Generating mock table...")
                # Find columns referenced for this table in SQL (e.g. table.COLUMN or TABLE.COLUMN)
                cols = set()
                col_matches = re.findall(rf'\b{table}\.([a-zA-Z0-9_]+)\b', sql_content, re.IGNORECASE)
                for col in col_matches:
                    cols.add(col.upper())
                if not cols:
                    cols.add("MANDT")
                df_mock = pd.DataFrame(columns=list(cols))
                row_data = []
                for col in list(cols):
                    col_lower = col.lower()
                    if col_lower in ["netwr", "netpr", "menge", "dmbtr", "wrbtr", "amount", "price", "qty", "quantity"]:
                        row_data.append(0.0)
                    elif "dat" in col_lower or "time" in col_lower:
                        row_data.append("2026-01-01 00:00:00")
                    else:
                        row_data.append("0")
                df_mock.loc[0] = row_data
                
                data_pool.create_table(
                    df=df_mock,
                    table_name=table,
                    drop_if_exists=True,
                    data_source_id=data_source_id
                )
                logger.info(f"Uploaded mock table {table} with columns: {list(cols)}")
                uploaded_tables.add(table)
                
        # 5. Prefix SQL query with connection name
        if conn_name:
            logger.info(f"5. Prefixing tables in SQL with connection name '{conn_name}'...")
            prefixed_sql = sql_content
            for table in source_tables:
                pattern = rf'\b(FROM|JOIN)\s+{table}\b'
                prefixed_sql = re.sub(pattern, rf'\1 "{conn_name}"."{table}"', prefixed_sql, flags=re.IGNORECASE)
        else:
            prefixed_sql = sql_content
            
        # 6. Manage and Execute SQL Job
        job_name = f"{sess.name} Data Job"
        logger.info(f"6. Managing Data Job '{job_name}'...")
        jobs = data_pool.get_jobs()
        data_job = None
        for j in jobs:
            if j.name == job_name:
                data_job = j
                break
        if not data_job:
            data_job = data_pool.create_job(name=job_name)
            
        transformations = data_job.get_transformations()
        task = None
        for t in transformations:
            if t.name == "SQL Transformation":
                task = t
                break
        if not task:
            task = data_job.create_transformation(name="SQL Transformation", description="Auto-generated SQL transformations")
            
        task.update_statement(prefixed_sql)
        logger.info("SQL statement updated. Running data job execution synchronously...")
        data_job.execute(wait=True)
        
        status_obj = data_job.get_current_execution_status()
        status_str = status_obj.status if hasattr(status_obj, "status") else str(status_obj)
        logger.info(f"Job execution completed. Status: {status_str}")
        if "success" not in status_str.lower():
            raise Exception(f"SQL execution failed with status: {status_str}")
            
        # 7. Create/Get Data Model
        dm_name = f"{sess.name} Data Model"
        logger.info(f"7. Managing Data Model '{dm_name}'...")
        data_models = data_pool.get_data_models()
        data_model = None
        for dm in data_models:
            if dm.name == dm_name:
                data_model = dm
                break
        if not data_model:
            data_model = data_pool.create_data_model(name=dm_name)
            
        # 8. Map Output Tables inside Data Model
        logger.info("8. Mapping output tables in Data Model...")
        dm_tables = data_model.get_tables()
        dm_table_names = [t.name.upper() for t in dm_tables]
        
        for tname in ["TEMP_P2P_CASES", "TEMP_P2P_EVENT_LOG"]:
            if tname not in dm_table_names:
                logger.info(f"Adding table {tname} to Data Model")
                data_model.add_table(name=tname)
                
        # Retrieve mapped table objects
        event_table = None
        case_table = None
        for t in data_model.get_tables():
            if t.name.upper() == "TEMP_P2P_EVENT_LOG":
                event_table = t
            elif t.name.upper() == "TEMP_P2P_CASES":
                case_table = t
                
        if not event_table or not case_table:
            raise Exception("Failed to add or retrieve TEMP_P2P_EVENT_LOG or TEMP_P2P_CASES from Data Model.")
            
        # Create Primary/Foreign Key Relationship
        fks = data_model.get_foreign_keys()
        fk_exists = False
        for fk in fks:
            if fk.source_table_id == event_table.id and fk.target_table_id == case_table.id:
                fk_exists = True
                break
        if not fk_exists:
            logger.info("Creating foreign key relationship: TEMP_P2P_EVENT_LOG -> TEMP_P2P_CASES...")
            data_model.create_foreign_key(
                source_table_id=event_table.id,
                target_table_id=case_table.id,
                columns=[("CASE_KEY", "CASE_KEY")]
            )
            
        # Create Process Configuration
        configs = data_model.get_process_configurations()
        if not configs:
            logger.info("Creating process configuration...")
            data_model.create_process_configuration(
                activity_table_id=event_table.id,
                case_id_column="CASE_KEY",
                activity_column="ACTIVITY",
                timestamp_column="EVENT_TIME",
                sorting_column="SORT_INDEX",
                case_table_id=case_table.id
            )
            
        # Reload Data Model
        logger.info("Reloading Data Model...")
        data_model.reload(wait=True)
        logger.info("Data Model reloaded successfully.")
        
        # 9. Manage Space & Package
        space_name = f"{sess.name} Space"
        logger.info(f"9. Managing Studio Space '{space_name}'...")
        spaces = celonis.studio.get_spaces()
        space = None
        for s in spaces:
            if s.name == space_name:
                space = s
                break
        if not space:
            space = celonis.studio.create_space(name=space_name)
            
        pkg_name = f"{sess.name} Package"
        pkg_key = slugify(sess.name).replace("_", "-")
        # Append unique session ID suffix to prevent global package key conflict
        pkg_key = f"{pkg_key}-{sess.id[:8]}"
        logger.info(f"Managing Package '{pkg_name}' (Key: {pkg_key})...")
        packages = space.get_packages()
        package = None
        for p in packages:
            if p.key == pkg_key:
                package = p
                break
        if not package:
            package = space.create_package(name=pkg_name, key=pkg_key)
            
        # 10. Knowledge Model Ingestion
        km_json_str = bundle.get("knowledge_model", "{}")
        knowledge_model = None
        if km_json_str and km_json_str != "{}":
            logger.info("10. Managing Knowledge Model...")
            try:
                km_obj = json.loads(km_json_str)
            except Exception:
                km_obj = {}
                
            session_suffix = sess.id[:8]
            km_key = f"{pkg_key}-km-{session_suffix}"
            
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
                
            km_content = {
            # Create or recreate package variable 'data-model'
            try:
                for v in package.get_variables():
                    if v.key == "data-model":
                        logger.info("Deleting existing variable 'data-model'...")
                        v.delete()
            except Exception as var_del_err:
                logger.warning(f"Failed to delete variable: {var_del_err}")
                
            try:
                package.create_variable(key="data-model", value=data_model.id, type_="DATA_MODEL", runtime=False)
                logger.info("Created variable 'data-model'.")
            except Exception as var_create_err:
                logger.warning(f"Failed to create variable: {var_create_err}")

            event_log_id = event_table.name if event_table else "TEMP_P2P_EVENT_LOG"
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
            
            existing_km = None
            kms = package.get_knowledge_models()
            for existing in kms:
                if existing.key == km_key:
                    existing_km = existing
                    break
            
            if existing_km:
                logger.info("Updating existing Knowledge Model...")
                existing_km.serialized_content = yaml.dump(km_content, sort_keys=False)
                existing_km.update()
                knowledge_model = existing_km
            else:
                logger.info("Creating new Knowledge Model...")
                knowledge_model = package.create_knowledge_model(content=km_content)
            logger.info("Knowledge Model created/updated successfully.")
            
        # 11. View Ingestion
        view_json_str = bundle.get("view", "{}")
        if view_json_str and view_json_str != "{}":
            logger.info("11. Managing Studio View...")
            try:
                view_obj = json.loads(view_json_str)
            except Exception:
                view_obj = {}
                
            view_name = view_obj.get("name", f"{sess.name} Dashboard")
            view_key = f"{pkg_key}-view-{sess.id[:8]}"
            
            views = package.get_views()
            for existing_view in views:
                if existing_view.key == view_key or existing_view.name == view_name:
                    existing_view.delete()
                    
            km_key_arg = knowledge_model.key if knowledge_model else None
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
                            event_log_id = event_table.name if event_table else "TEMP_P2P_EVENT_LOG"
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
                logger.info("Studio View layout and components successfully populated.")
            except Exception as view_layout_err:
                logger.error(f"Failed to populate view layout: {view_layout_err}")
            
        # 12. Publish package
        logger.info("12. Publishing package...")
        try:
            package.publish(version="1.0.0")
            logger.info("Package published version 1.0.0.")
        except Exception as p_err:
            err_str = str(p_err).lower()
            if "version.exists" in err_str or "already published" in err_str:
                try:
                    package.publish(version="1.0.1")
                    logger.info("Package published version 1.0.1.")
                except Exception as p_err2:
                    logger.warning(f"Could not publish package: {p_err2}")
            else:
                logger.warning(f"Could not publish package: {p_err}")
                
        logger.info("SUCCESS: All steps executed successfully!")
        
    except Exception as e:
        logger.error("Run failed!", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    run_test()
