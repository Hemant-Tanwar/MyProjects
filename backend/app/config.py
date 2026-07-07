import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./celonis_orchestrator.db")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "meta.llama3-1-70b-instruct-v1:0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_ID = os.getenv("GEMINI_MODEL_ID", "gemini-3.1-flash-lite")

# Roles definition
ROLES = ["Business User", "Process Analyst", "Admin", "Reviewer"]

# Celonis integration config
CELONIS_URL = os.getenv("CELONIS_URL", "https://wbd8lqn9-2026-06-12.training.celonis.cloud/")
CELONIS_API_TOKEN = os.getenv("CELONIS_API_TOKEN", "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs")
