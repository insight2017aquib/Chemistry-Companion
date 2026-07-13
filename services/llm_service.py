import os
import requests
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

OPENROUTER_PROVIDER = "openrouter"
DEEPSEEK_PROVIDER = "deepseek"
DEFAULT_PROVIDER = OPENROUTER_PROVIDER

OPENROUTER_DEFAULT_MODEL = "deepseek/deepseek-v4-flash:free"
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"
OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
DEEPSEEK_API_KEY_ENV = "DEEPSEEK_API_KEY"

PROVIDER_ALIASES = {
    "openrouter": OPENROUTER_PROVIDER,
    "open-router": OPENROUTER_PROVIDER,
    "deepseek": DEEPSEEK_PROVIDER,
    "deepseek-ai": DEEPSEEK_PROVIDER,
}


def _normalize_provider(provider: Optional[str] = None) -> str:
    selected_provider = provider or os.getenv("LLM_PROVIDER")
    if not selected_provider:
        selected_provider = DEEPSEEK_PROVIDER if os.getenv(DEEPSEEK_API_KEY_ENV) else DEFAULT_PROVIDER
    return PROVIDER_ALIASES.get(selected_provider.strip().lower(), selected_provider.strip().lower())


def _extract_error_details(response: Optional[requests.Response], fallback: str) -> str:
    if response is None or not hasattr(response, "text"):
        return fallback

    try:
        error_data = response.json()
        if "error" in error_data and "message" in error_data["error"]:
            return error_data["error"]["message"]
    except ValueError:
        pass

    return fallback


class OpenRouterClient:
    """
    A client for interacting with the OpenRouter API.
    
    This client is designed to provide a safe, reusable way to interact with LLM models
    via OpenRouter, handling authentication, configuration, and graceful degradation
    in case of missing credentials or API failures.
    """

    def __init__(self, api_key: Optional[str] = None, default_model: Optional[str] = None):
        """
        Initialize the OpenRouterClient.

        Args:
            api_key (Optional[str]): The OpenRouter API key. If not provided, it will attempt
                                     to read the OPENROUTER_API_KEY environment variable.
            default_model (str): The default model to use for requests.
        """
        self.api_key = api_key or os.getenv(OPENROUTER_API_KEY_ENV)
        self.default_model = default_model or os.getenv("OPENROUTER_MODEL", OPENROUTER_DEFAULT_MODEL)
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    def explain(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Send a prompt to the LLM and return the explanation.

        Args:
            prompt (str): The prompt or question to send to the LLM.
            model (Optional[str]): The model to use. Defaults to the client's default_model.

        Returns:
            str: The LLM's response text, or a clear fallback message if the request fails.
        """
        if not self.api_key:
            return (
                f"LLM Explanation unavailable: {OPENROUTER_API_KEY_ENV} is missing. "
                "Please add your API key to the .env file to enable this feature."
            )

        model_to_use = model or self.default_model

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",  # Required by OpenRouter for ranking
            "X-Title": "Chemistry Companion",  # Required by OpenRouter for ranking
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
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                return "LLM Explanation failed: Invalid response format from OpenRouter."
                
        except requests.exceptions.Timeout:
            return "LLM Explanation failed: The request to OpenRouter timed out. Please try again later."
        except requests.exceptions.RequestException as e:
            # Catching generic request exceptions (including HTTP errors, connection errors, etc.)
            error_details = _extract_error_details(response, str(e))
            return f"LLM Explanation failed: An error occurred while contacting OpenRouter API. Details: {error_details}"
        except Exception as e:
            return f"LLM Explanation failed: An unexpected error occurred. Details: {str(e)}"


class UnsupportedLLMProviderClient:
    """
    Fallback client returned when LLM_PROVIDER is set to an unsupported provider.
    """

    def __init__(self, provider: str):
        self.provider = provider

    def explain(self, prompt: str, model: Optional[str] = None) -> str:
        return (
            f"LLM Explanation unavailable: unsupported LLM provider '{self.provider}'. "
            "Set LLM_PROVIDER to 'openrouter' or 'deepseek'."
        )


class LLMClient:
    """
    Provider-selecting LLM client.

    Set LLM_PROVIDER=openrouter or LLM_PROVIDER=deepseek to choose the backend.
    The public explain(...) interface stays consistent across providers.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
    ):
        """
        Initialize a provider-specific LLM client.

        Args:
            provider (Optional[str]): Provider name. Defaults to the LLM_PROVIDER
                                      environment variable, then OpenRouter.
            api_key (Optional[str]): API key override for the selected provider.
            default_model (Optional[str]): Default model override for the selected provider.
        """
        self.provider = _normalize_provider(provider)
        self.client = self._build_client(api_key=api_key, default_model=default_model)

    def _build_client(self, api_key: Optional[str], default_model: Optional[str]):
        if self.provider == DEEPSEEK_PROVIDER:
            from llm.deepseek_client import DeepSeekClient

            return DeepSeekClient(
                api_key=api_key or os.getenv(DEEPSEEK_API_KEY_ENV),
                default_model=default_model or os.getenv("DEEPSEEK_MODEL", DEEPSEEK_DEFAULT_MODEL),
            )

        if self.provider == OPENROUTER_PROVIDER:
            return OpenRouterClient(api_key=api_key, default_model=default_model)

        return UnsupportedLLMProviderClient(self.provider)

    def explain(self, prompt: str, model: Optional[str] = None) -> str:
        """
        Send a prompt to the selected LLM provider and return the explanation.
        """
        if model is None:
            return self.client.explain(prompt)

        return self.client.explain(prompt, model=model)


def get_llm_client(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    default_model: Optional[str] = None,
) -> LLMClient:
    """
    Build a configured LLM client using a provider string or the LLM_PROVIDER env var.
    """
    return LLMClient(provider=provider, api_key=api_key, default_model=default_model)
