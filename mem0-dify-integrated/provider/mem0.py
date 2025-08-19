from typing import Any
import httpx

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class Mem0Provider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            # Get API configuration
            api_key = credentials.get("mem0_api_key", "")
            api_url = credentials.get("mem0_api_url", "http://localhost:8000")

            if not api_url or api_url.strip() == "":
                api_url = "http://localhost:8000"

            api_url = api_url.rstrip("/")

            # Prepare headers
            headers = {"Content-Type": "application/json"}

            # Add authorization header only if API key is provided
            if api_key and api_key.strip():
                headers["Authorization"] = f"Token {api_key}"

            # Test API connection with a simple search
            test_payload = {
                "query": "validation_test",
                "user_id": "validation_test",
                "limit": 1
            }

            response = httpx.post(
                f"{api_url}/v2/memories/search/",
                json=test_payload,
                headers=headers,
                timeout=10
            )

            # Check if the response is successful
            if response.status_code not in [200, 404]:  # 404 is OK if no memories found
                raise Exception(f"API returned status code {response.status_code}: {response.text}")

        except Exception as e:
            raise ToolProviderCredentialValidationError(f"Failed to validate Mem0 credentials: {str(e)}")
