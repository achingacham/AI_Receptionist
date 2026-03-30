import httpx
from typing import Optional


class GroqClient:
    """Simple Groq client wrapper using httpx.

    This is a lightweight adapter that calls a Groq REST-style generate endpoint.
    The exact endpoint path and response shape may vary depending on Groq's API
    version; these defaults are configurable via `api_url` and `model`.
    """

    def __init__(self, api_key: str, api_url: str = "https://api.groq.com/v1", model: str = "groq-small"):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(timeout=30.0)

    def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        url = f"{self.api_url}/models/{self.model}/generate"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {"input": prompt, "max_output_tokens": max_tokens}
        resp = self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # Attempt to extract the textual output from known response shapes.
        if isinstance(data, dict):
            if "outputs" in data and isinstance(data["outputs"], list) and data["outputs"]:
                out0 = data["outputs"][0]
                if isinstance(out0, dict):
                    return out0.get("content") or out0.get("text") or str(out0)
            if "text" in data:
                return data["text"]
        return str(data)
