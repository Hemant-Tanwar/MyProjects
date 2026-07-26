# Celonis Multi-Agent Workflow Orchestrator

An end-to-end multi-agent orchestration application designed to ingest business process requirements, generate database transformations, map data models, define semantic layers (Knowledge Models), design Studio dashboards (Views), and programmatically deploy them directly to **Celonis EMS**.

---

## Architecture

1. **Backend (`/backend`)**:
   - **Framework**: FastAPI (Python 3.10+)
   - **Database**: SQLite (SQLAlchemy ORM)
   - **AI Agents**: Specialized agents for Requirements Analysis, SQL Transformation, Data Modeling, Knowledge Modeling, View Design, and QA Validation.
   - **Cloud Push Integration**: Integrates programmatically with Celonis using `pycelonis`.

2. **Frontend (`/frontend`)**:
   - **Framework**: React (TypeScript + Vite)
   - **Styling**: Modern, premium dark-themed CSS styling with responsive sidebar cockpit views.

---

## Prerequisites

Ensure you have the following installed on your system before starting:

| Tool | Version | Check command |
|------|---------|--------------|
| **Python** | 3.10 or higher | `python3.10 --version` |
| **Node.js** | 18 or higher | `node --version` |
| **NPM** | Latest | `npm --version` |

---

## Step-by-Step Setup Guide

Follow these steps **in order** from your project root directory.

---

### Step 1 — Clone the repository (if not done already)

```bash
git clone <repo-url>
cd hemant_process_mine
```

---

### Step 2 — Create the Python virtual environment

> ⚠️ The `.venv` must be created at the **project root**, not inside `/backend`.

Run this from the **project root**:

```bash
python3.10 -m venv .venv
```

Verify it was created:

```bash
ls .venv/bin/python
```

---

### Step 3 — Install backend Python dependencies

```bash
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r backend/requirements.txt
```

---

### Step 4 — Install the Celonis SDK

```bash
.venv/bin/pip install --extra-index-url=https://pypi.celonis.cloud/ pycelonis
```

---

### Step 5 — Configure environment variables

Create or export the following environment variables (required for AWS Bedrock AI and Celonis Cloud):

```bash
export AWS_DEFAULT_REGION="us-east-1"
export BEDROCK_MODEL_ID="meta.llama3-1-70b-instruct-v1:0"
export CELONIS_URL="https://your-tenant.celonis.cloud/"
export CELONIS_API_TOKEN="your-api-key"
```

> 💡 You can put these in a `.env` file inside the `/backend` folder. The app will pick them up automatically via `python-dotenv`.

---

### Step 6 — Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

You need **two terminal windows** — one for the backend and one for the frontend.

---

### Terminal 1 — Start the Backend

Run from the **project root**:

```bash
cd backend
../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

**Or** activate the venv first, then run:

```bash
source .venv/bin/activate
cd backend
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

✅ Backend is ready when you see:
```
INFO:     Uvicorn running on http://127.0.0.1:8001 (Press CTRL+C to quit)
```

- API docs: `http://127.0.0.1:8001/docs`

---

### Terminal 2 — Start the Frontend

Run from the **project root**:

```bash
cd frontend
npm run dev
```

✅ Frontend is ready when you see:
```
VITE ready in xxx ms
➜  Local:   http://localhost:5173/
```

Open your browser and navigate to **`http://localhost:5173/`** to open the Orchestrator Cockpit.

---

## Quick Reference (Daily Use)

Once the setup is done, use these commands each time you start the project:

**Terminal 1 (Backend):**
```bash
cd /path/to/hemant_process_mine/backend
../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

**Terminal 2 (Frontend):**
```bash
cd /path/to/hemant_process_mine/frontend
npm run dev
```

---

## Production Promotion & Celonis Push

When you click **Promote to Production** inside the QA Validation tab:

1. **Local Exports**: Assets are generated under `/projects/<session_name_slug>/`:
   - `transformations.sql` (Database ETL transformations)
   - `datamodel.json` (Data Model mapping configuration)
   - `knowledge_model.yaml` (Calculated KPIs and filters formatted in **YAML** for Celonis)
   - `studio_view_spec.yaml` (Dashboard interface metadata layout formatted in YAML)
   - `deployment_runbook.md` (Step-by-step instructions)

2. **Celonis Auto-Push**: Connects to the configured Celonis Cloud instance and programmatically creates:
   - Data Pool
   - Data Model inside the Data Pool
   - Data Job and inputs the SQL Transformation script
   - Studio Space
   - Studio Package
   - Knowledge Model (linked to the Data Model ID)
   - Studio View (linked to the Knowledge Model)
   - Automatically publishes the package draft to version `1.0.0` (or `1.0.1` on subsequent runs).

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| `zsh: no such file or directory: ../.venv/bin/uvicorn` | `.venv` not found at project root | Run `python3.10 -m venv .venv` from the project root |
| `source .venv/bin/activate` fails in `backend/` | `.venv` is at root, not in backend | Use `source ../.venv/bin/activate` or run from root |
| `Failed to fetch` in browser | Backend not running or wrong port | Make sure backend is running on port `8001` |
| `pip: command not found` | venv not activated | Use `.venv/bin/pip` explicitly |
| `ModuleNotFoundError: pycelonis` | pycelonis not installed | Run Step 4 again |
