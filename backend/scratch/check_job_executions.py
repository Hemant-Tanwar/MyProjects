from pycelonis import get_celonis
import inspect

url = "https://wbd8lqn9-2026-06-12.training.celonis.cloud/"
api_token = "Y2YzNGVjZDktZTY5MC00MDg3LWI0ZmMtZmY1ODFhYjYwMWVjOk5wb0JGWW5sM0ZEZlpNRnRXYWVJR0ErNlp3UnY3dndIMVpYSzJQRVFvTWZs"

try:
    c = get_celonis(base_url=url, api_token=api_token, key_type="USER_KEY")
    pool_name = "Accounts Payable Direct Push"
    pool = [p for p in c.data_integration.get_data_pools() if p.name == pool_name][0]
    job = [j for j in pool.get_jobs() if j.name == f"{pool_name} Data Job"][0]
    
    print("Signature:")
    print(inspect.signature(job._get_execution_detailed_error_log))
    
    # Let's try calling it or check the execution log
    print("\nCalling _get_execution_detailed_error_log:")
    try:
        res = job._get_execution_detailed_error_log()
        print("Detailed Error Log:")
        print(res)
    except Exception as call_err:
        print("Failed to call:", call_err)
        
    print("\nTask executions in data job:")
    try:
        tasks = job._get_task_executions_in_data_job()
        for t in tasks:
            print(t)
    except Exception as t_err:
        print("Failed to call tasks:", t_err)
        
except Exception as e:
    print("Error:", e)
