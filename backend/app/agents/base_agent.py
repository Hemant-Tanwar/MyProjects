import json
import boto3
import logging
from botocore.exceptions import ClientError
from app.config import AWS_REGION, BEDROCK_MODEL_ID

logger = logging.getLogger(__name__)

class BaseAgent:
    def __init__(self, name: str):
        self.name = name
        try:
            self.client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
            self.is_mock = False
        except Exception as e:
            logger.warning(f"Could not initialize Bedrock client: {str(e)}. Running in mock mode.")
            self.client = None
            self.is_mock = True

    def invoke(self, system_prompt: str, prompt: str) -> tuple[str, str]:
        """
        Invokes AWS Bedrock with system and user prompts using the Converse API.
        Returns:
            (response_text, actual_model_used)
        """
        if self.is_mock or not self.client:
            return self._mock_response(prompt), "mock-agent"

        # Try designated model using the Converse API
        try:
            response = self.client.converse(
                modelId=BEDROCK_MODEL_ID,
                messages=[
                    {
                        "role": "user",
                        "content": [{"text": prompt}]
                    }
                ],
                system=[
                    {"text": system_prompt}
                ],
                inferenceConfig={
                    "maxTokens": 4000,
                    "temperature": 0.2
                }
            )
            output_text = response["output"]["message"]["content"][0]["text"]
            return output_text, BEDROCK_MODEL_ID
        except ClientError as e:
            # Fallback model in case the target model fails
            fallback_model = "meta.llama3-1-8b-instruct-v1:0"
            logger.warning(f"Bedrock converse failed for {BEDROCK_MODEL_ID}: {str(e)}. Retrying with {fallback_model}...")
            try:
                response = self.client.converse(
                    modelId=fallback_model,
                    messages=[
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ],
                    system=[
                        {"text": system_prompt}
                    ],
                    inferenceConfig={
                        "maxTokens": 4000,
                        "temperature": 0.2
                    }
                )
                output_text = response["output"]["message"]["content"][0]["text"]
                return output_text, fallback_model
            except Exception as ex:
                logger.error(f"Fallback model also failed: {str(ex)}. Using mock fallback.")
                return self._mock_response(prompt), "mock-fallback"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}. Using mock fallback.")
            return self._mock_response(prompt), "mock-fallback"

    def _mock_response(self, prompt: str) -> str:
        """Fallback mock generator representing the agents if Bedrock calls fail."""
        raise NotImplementedError("Each specialized agent must implement a mock fallback generator.")
