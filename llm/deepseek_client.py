import os
from typing import Optional

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class DeepSeekClient:
    """
    A client for interacting with the DeepSeek API.

    This client provides a safe, reusable way to interact with DeepSeek models
    through the OpenAI-compatible API, handling authentication, configuration,
    and graceful degradation in case of missing credentials or API failures.
    """

    def __init__(self, api_key: Optional[str] = None, default_model: str = "deepseek-chat"):
        """
        Initialize the DeepSeekClient.

        Args:
            api_key (Optional[str]): The DeepSeek API key. If not provided, it will attempt
                                     to read the DEEPSEEK_API_KEY environment variable.
            default_model (str): The default model to use for requests.
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.default_model = default_model
        self.base_url = "https://api.deepseek.com/v1"

    def explain(self, prompt: str, model: str = "deepseek-chat") -> str:
        """
        Send a prompt to the LLM and return the explanation.

        Args:
            prompt (str): The prompt or question to send to the LLM.
            model (str): The model to use. Defaults to deepseek-chat.

        Returns:
            str: The LLM's response text, or a clear fallback message if the request fails.
        """
        if not self.api_key:
            return (
                "LLM Explanation unavailable: DEEPSEEK_API_KEY is missing. "
                "Please add your API key to the .env file to enable this feature."
            )

        model_to_use = model or self.default_model

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model_to_use,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }

        response = None
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()

            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                return "LLM Explanation failed: Invalid response format from DeepSeek."

        except requests.exceptions.Timeout:
            return "LLM Explanation failed: The request to DeepSeek timed out. Please try again later."
        except requests.exceptions.RequestException as e:
            error_details = str(e)
            if response is not None and hasattr(response, "text"):
                try:
                    error_data = response.json()
                    if "error" in error_data and "message" in error_data["error"]:
                        error_details = error_data["error"]["message"]
                except ValueError:
                    pass
            return f"LLM Explanation failed: An error occurred while contacting DeepSeek API. Details: {error_details}"
        except Exception as e:
            return f"LLM Explanation failed: An unexpected error occurred. Details: {str(e)}"
