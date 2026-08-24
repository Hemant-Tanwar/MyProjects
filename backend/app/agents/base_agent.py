import json
import urllib.request
import urllib.error
import logging
from app.config import GEMINI_API_KEY, GEMINI_MODEL_ID

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        self.api_key = GEMINI_API_KEY
        self.model_id = GEMINI_MODEL_ID
        if not self.api_key:
            logger.warning(f"GEMINI_API_KEY is not configured for {self.name}.")

    def _load_sap_knowledge_base(self) -> dict:
        import os
        paths_to_try = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "Sap_knowledge_base.json")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agents", "Sap_knowledge_base.json")),
            "/Users/hemanttanwar/Documents/hemant_process_mine/backend/app/agents/Sap_knowledge_base.json"
        ]
        for p in paths_to_try:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Error loading Sap_knowledge_base.json: {str(e)}")
        return {}

    def _get_lessons_path(self) -> str:
        import os
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "lessons_learned.json"))

    def _load_lessons_learned(self) -> list:
        import os
        path = self._get_lessons_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading lessons_learned.json: {str(e)}")
        return []

    def save_lesson(self, stage: str, requirement: str, error: str, fix_output: str, rationale: str):
        import os
        path = self._get_lessons_path()
        lessons = self._load_lessons_learned()
        lessons.append({
            "stage": stage,
            "requirement": requirement,
            "error": error,
            "fix_output": fix_output,
            "rationale": rationale
        })
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(lessons, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving lesson: {str(e)}")

    def invoke(self, system_prompt: str, prompt: str) -> tuple[str, str]:
        """
        Invokes Gemini API with system and user prompts using urllib.
        Returns:
            (response_text, actual_model_used)
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        # Find lessons matching the agent's active stage
        agent_stage_map = {
            "Requirement Analyzer Agent": "requirement",
            "Transformation SQL Agent": "sql",
            "Data Model Agent": "data_model",
            "Knowledge Model Agent": "knowledge_model",
            "Celonis Analysis Agent": "analysis",
            "QA Agent": "qa"
        }
        active_stage = agent_stage_map.get(self.name, "")
        lessons = self._load_lessons_learned()
        relevant_lessons = [l for l in lessons if l.get("stage") == active_stage]
        
        if relevant_lessons:
            lessons_prompt = "\n\n=== LESSONS LEARNED FROM PAST ERRORS (CRITICAL FEW-SHOT EXAMPLES) ===\n"
            for idx, l in enumerate(relevant_lessons[-5:]): # last 5 lessons
                lessons_prompt += f"Lesson {idx+1}:\n"
                lessons_prompt += f"- Requirement/Context: {l.get('requirement')}\n"
                lessons_prompt += f"- Encountered Error: {l.get('error')}\n"
                lessons_prompt += f"- Rationale for correction: {l.get('rationale')}\n"
                lessons_prompt += f"- Correct Output to Use: \n{l.get('fix_output')}\n"
                lessons_prompt += "-" * 40 + "\n"
            system_prompt = system_prompt + lessons_prompt

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_id}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_prompt}
                ]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 8192
            }
        }
        
        import time
        max_attempts = 5
        base_delay = 2.0
        
        for attempt in range(1, max_attempts + 1):
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    candidates = res_data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            output_text = parts[0].get("text", "")
                            return output_text, self.model_id
                    
                    raise ValueError(f"Unexpected API response structure: {res_data}")
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8")
                logger.error(f"Gemini API HTTP Error {e.code}: {err_body}")
                
                # Check for rate limit 429 or server overload 503
                if e.code in [429, 503] and attempt < max_attempts:
                    sleep_time = base_delay * (2 ** (attempt - 1))
                    # Check if body contains specific delay details
                    try:
                        err_json = json.loads(err_body)
                        msg = err_json.get("error", {}).get("message", "")
                        # Try to parse delay time from error message
                        import re
                        delay_match = re.search(r"retry in ([\d\.]+)s", msg, re.IGNORECASE)
                        if delay_match:
                            sleep_time = float(delay_match.group(1)) + 0.5
                    except Exception:
                        pass
                    
                    logger.warning(f"Rate limited or server overloaded. Retrying in {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    continue
                
                raise Exception(f"Gemini API HTTP Error {e.code}: {err_body}")
            except Exception as e:
                logger.error(f"Unexpected error invoking Gemini API: {str(e)}")
                raise e

    def _parse_structured_response(self, text: str) -> tuple[str, str]:
        import re
        rationale = "No rationale provided."
        content = ""
        
        # Look for custom tags like ---SQL---, ---MODEL---, etc.
        tags = ["---SPECIFICATION---", "---MODEL---", "---SQL---", "---KM---", "---ANALYSIS---", "---RESPONSE---", "---REPORT---"]
        matching_tag = None
        for t in tags:
            if t in text:
                matching_tag = t
                break
                
        if "---RATIONALE---" in text and matching_tag:
            parts = text.split(matching_tag)
            rationale_part = parts[0].replace("---RATIONALE---", "").strip()
            content_part = parts[1].strip()
            if content_part.startswith("```"):
                lines = content_part.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                content_part = "\n".join(lines).strip()
            return rationale_part, content_part
            
        # Try generic JSON block parse
        try:
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                content = text[start_idx:end_idx+1]
                rationale = text[:start_idx].strip()
                return rationale, content
        except Exception:
            pass
            
        return rationale, text

    def fix_error(self, requirement_spec: str, failing_output: str, error_msg: str, context: dict = None) -> tuple[str, str]:
        """
        Generic self-correction method for any agent to fix its failing output based on error messages.
        """
        context_str = ""
        if context:
            context_str = "\n".join([f"### {k}:\n{v}" for k, v in context.items()])

        system_prompt = (
            f"You are the expert {self.name} self-correction system.\n"
            f"Your job is to fix the failing output of the {self.name}.\n"
            f"Below is the original requirements specification, the failing output, the error message, and the execution context.\n"
            f"Analyze the error carefully, correct the structural, semantic, or syntax issues, and output the corrected rationale and output.\n\n"
            f"=== ORIGINAL SYSTEM PROMPT RULES ===\n"
            f"You must strictly adhere to the role, format, and syntax rules of the {self.name}."
        )

        prompt = (
            f"### Original Requirements:\n{requirement_spec}\n\n"
            f"{context_str}\n\n"
            f"### Failing Output:\n{failing_output}\n\n"
            f"### Execution Error Message:\n{error_msg}\n\n"
            f"Please identify and correct the error in the output."
        )

        response, model_used = self.invoke(system_prompt, prompt)
        rationale, corrected_content = self._parse_structured_response(response)
        return rationale, corrected_content
