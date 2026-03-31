import httpx
from typing import Optional


class GroqClient:
    """Groq client wrapper using httpx with OpenAI-compatible API format.

    This adapter calls Groq's chat completion endpoint which is compatible with
    OpenAI's API format.
    """

    def __init__(self, api_key: str, api_url: str = "https://api.groq.com/openai/v1", model: str = "mixtral-8x7b-32768"):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(timeout=30.0)

    def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate a response using the Groq API with chat completions."""
        url = f"{self.api_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Convert the prompt to OpenAI-compatible message format
        # The prompt contains SYSTEM: and USER: prefixes, so parse it
        messages = []
        lines = prompt.split('\n')
        current_role = None
        current_content = []
        
        for line in lines:
            if line.startswith('SYSTEM:'):
                if current_content:
                    messages.append({"role": current_role, "content": '\n'.join(current_content).strip()})
                    current_content = []
                current_role = "system"
                current_content.append(line[7:].strip())
            elif line.startswith('ASSISTANT:'):
                if current_content:
                    messages.append({"role": current_role, "content": '\n'.join(current_content).strip()})
                    current_content = []
                current_role = "assistant"
                current_content.append(line[10:].strip())
            elif line.startswith('USER:'):
                if current_content:
                    messages.append({"role": current_role, "content": '\n'.join(current_content).strip()})
                    current_content = []
                current_role = "user"
                current_content.append(line[5:].strip())
            else:
                if current_role:
                    current_content.append(line)
        
        if current_content:
            messages.append({"role": current_role, "content": '\n'.join(current_content).strip()})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        resp = self._client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # Extract the response from standard OpenAI format
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            choice = data["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
        
        return str(data)
