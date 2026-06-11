import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./celonis_orchestrator.db")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "meta.llama3-1-70b-instruct-v1:0")

# Roles definition
ROLES = ["Business User", "Process Analyst", "Admin", "Reviewer"]
