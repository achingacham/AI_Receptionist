import httpx


class LLMClient:
    """httpx wrapper for any OpenAI-compatible chat completions endpoint.

    Works with Groq, Azure OpenAI's unified /openai/v1 surface, or any other
    provider that implements the OpenAI chat completions API format.
    """

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.groq.com/openai/v1",
        model: str = "mixtral-8x7b-32768",
    ):
        self.api_key = api_key
        self.api_url = api_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(timeout=30.0)
        # GPT-5/reasoning-tier models reject "max_tokens" (want "max_completion_tokens")
        # and reject a non-default "temperature". Detected lazily on first request and
        # cached on the instance so later calls skip straight to the working payload.
        self._token_param = "max_tokens"
        self._send_temperature = True

    def generate(self, prompt: str, max_tokens: int = 1024) -> str:
        """Generate a response using the chat completions endpoint."""
        url = f"{self.api_url}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        # Convert the prompt to OpenAI-compatible message format
        # The prompt contains SYSTEM: and USER: prefixes, so parse it
        messages = []
        lines = prompt.split("\n")
        current_role = None
        current_content = []

        for line in lines:
            if line.startswith("SYSTEM:"):
                if current_content:
                    messages.append(
                        {"role": current_role, "content": "\n".join(current_content).strip()}
                    )
                    current_content = []
                current_role = "system"
                current_content.append(line[7:].strip())
            elif line.startswith("ASSISTANT:"):
                if current_content:
                    messages.append(
                        {"role": current_role, "content": "\n".join(current_content).strip()}
                    )
                    current_content = []
                current_role = "assistant"
                current_content.append(line[10:].strip())
            elif line.startswith("USER:"):
                if current_content:
                    messages.append(
                        {"role": current_role, "content": "\n".join(current_content).strip()}
                    )
                    current_content = []
                current_role = "user"
                current_content.append(line[5:].strip())
            else:
                if current_role:
                    current_content.append(line)

        if current_content:
            messages.append({"role": current_role, "content": "\n".join(current_content).strip()})

        def build_payload() -> dict:
            payload = {
                "model": self.model,
                "messages": messages,
                self._token_param: max_tokens,
            }
            if self._send_temperature:
                payload["temperature"] = 0.7
            return payload

        resp = self._client.post(url, json=build_payload(), headers=headers)
        # Retry once per known incompatibility (GPT-5/reasoning-tier models reject
        # "max_tokens" and non-default "temperature"); cache the fix on the instance.
        for _ in range(2):
            if resp.status_code != 400:
                break
            try:
                param = resp.json().get("error", {}).get("param")
            except ValueError:
                break
            if param == "max_tokens" and self._token_param == "max_tokens":
                self._token_param = "max_completion_tokens"
            elif param == "temperature" and self._send_temperature:
                self._send_temperature = False
            else:
                break
            resp = self._client.post(url, json=build_payload(), headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # Extract the response from standard OpenAI format
        if "choices" in data and isinstance(data["choices"], list) and data["choices"]:
            choice = data["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]

        return str(data)
