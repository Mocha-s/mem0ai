import json
import logging
import os
import warnings
from typing import Dict, List, Optional

from openai import OpenAI

from mem0.configs.llms.base import BaseLlmConfig
from mem0.llms.base import LLMBase
from mem0.memory.utils import extract_json


class OpenAILLM(LLMBase):
    def __init__(self, config: Optional[BaseLlmConfig] = None):
        super().__init__(config)

        # Configuration now handles environment variables, so we use config values directly
        # The model default is already set in BaseLlmConfig (gpt-4o-mini)

        if os.environ.get("OPENROUTER_API_KEY"):  # Use OpenRouter
            self.client = OpenAI(
                api_key=os.environ.get("OPENROUTER_API_KEY"),
                base_url=self.config.openrouter_base_url
                or os.getenv("OPENROUTER_API_BASE")
                or "https://openrouter.ai/api/v1",
            )
        else:
            # Use configuration values which already handle environment variables
            api_key = self.config.api_key
            base_url = self.config.openai_base_url

            # Deprecation warning for old environment variable (only if not using new one)
            if os.environ.get("OPENAI_API_BASE") and not os.environ.get("OPENAI_BASE_URL"):
                warnings.warn(
                    "The environment variable 'OPENAI_API_BASE' is deprecated and will be removed in the 0.1.80. "
                    "Please use 'OPENAI_BASE_URL' instead.",
                    DeprecationWarning,
                )

            self.client = OpenAI(api_key=api_key, base_url=base_url)

        # Validate connection if API key is provided
        if self.config.api_key:
            self._validate_connection()

    def _validate_connection(self):
        """Validate the connection to the API endpoint"""
        try:
            # Try to list models to validate connection
            # This is a lightweight operation that verifies API key and endpoint
            self.client.models.list()
        except Exception as e:
            # Log warning but don't fail initialization
            warnings.warn(
                f"Failed to validate connection to {self.config.openai_base_url}: {e}. "
                "This may indicate an invalid API key or unreachable endpoint.",
                UserWarning
            )

    def _parse_response(self, response, tools):
        """
        Process the response based on whether tools are used or not.

        Args:
            response: The raw response from API.
            tools: The list of tools provided in the request.

        Returns:
            str or dict: The processed response.
        """
        if tools:
            processed_response = {
                "content": response.choices[0].message.content,
                "tool_calls": [],
            }

            if response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    try:
                        arguments_str = extract_json(tool_call.function.arguments)
                        parsed_arguments = json.loads(arguments_str)
                        processed_response["tool_calls"].append(
                            {
                                "name": tool_call.function.name,
                                "arguments": parsed_arguments,
                            }
                        )
                    except json.JSONDecodeError as e:
                        logging.warning(f"JSON解析失败，跳过此工具调用: {e}")
                        logging.warning(f"原始参数: {tool_call.function.arguments}")
                        # 尝试使用原始字符串作为fallback
                        try:
                            processed_response["tool_calls"].append(
                                {
                                    "name": tool_call.function.name,
                                    "arguments": {"raw_content": tool_call.function.arguments},
                                }
                            )
                        except Exception:
                            # 如果仍然失败，跳过这个工具调用
                            continue

            return processed_response
        else:
            return response.choices[0].message.content

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        response_format=None,
        tools: Optional[List[Dict]] = None,
        tool_choice: str = "auto",
    ):
        """
        Generate a JSON response based on the given messages using OpenAI.

        Args:
            messages (list): List of message dicts containing 'role' and 'content'.
            response_format (str or object, optional): Format of the response. Defaults to "text".
            tools (list, optional): List of tools that the model can call. Defaults to None.
            tool_choice (str, optional): Tool choice method. Defaults to "auto".

        Returns:
            json: The generated response.
        """
        params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
        }

        if os.getenv("OPENROUTER_API_KEY"):
            openrouter_params = {}
            if self.config.models:
                openrouter_params["models"] = self.config.models
                openrouter_params["route"] = self.config.route
                params.pop("model")

            if self.config.site_url and self.config.app_name:
                extra_headers = {
                    "HTTP-Referer": self.config.site_url,
                    "X-Title": self.config.app_name,
                }
                openrouter_params["extra_headers"] = extra_headers

            params.update(**openrouter_params)

        if response_format:
            params["response_format"] = response_format
        if tools:  # TODO: Remove tools if no issues found with new memory addition logic
            params["tools"] = tools
            params["tool_choice"] = tool_choice

        response = self.client.chat.completions.create(**params)
        return self._parse_response(response, tools)
