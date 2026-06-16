"""Runs the default Accounts Payable pipeline for testing. See run_pipeline.py for generic usage."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from run_pipeline import run

run(
    session_name="Accounts Payable Direct Push",
    requirement="Procurement accounts payable monitoring. Identify duplicate invoice payments."
)
