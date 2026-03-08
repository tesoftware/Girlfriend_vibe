import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    def __init__(self, config_path="config.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.active_provider = self.config["llm"]["active_provider"]

    def reload_config(self):
        with open("config.json", "r", encoding="utf-8") as f:
            self.config = json.load(f)
        self.active_provider = self.config["llm"]["active_provider"]

    def set_provider(self, provider):
        self.active_provider = provider
        self.config["llm"]["active_provider"] = provider
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def chat(self, prompt, system_prompt=None):
        if self.active_provider == "minimax":
            return self._chat_minimax(prompt, system_prompt)
        elif self.active_provider == "openai":
            return self._chat_openai(prompt, system_prompt)
        elif self.active_provider == "anthropic":
            return self._chat_anthropic(prompt, system_prompt)
        elif self.active_provider == "ollama":
            return self._chat_ollama(prompt, system_prompt)
        elif self.active_provider == "custom":
            return self._chat_custom(prompt, system_prompt)
        else:
            raise ValueError(f"Unknown provider: {self.active_provider}")

    def _chat_minimax(self, prompt, system_prompt=None):
        """Use requests to call MiniMax API"""
        load_dotenv(override=True)
        api_key = os.getenv("MINIMAX_API_KEY")

        if not api_key:
            raise ValueError("MINIMAX_API_KEY must be set in .env file")

        provider_config = self.config["llm"]["providers"]["minimax"]
        model = provider_config.get("model", "MiniMax-Text-01")
        base_url = provider_config.get("base_url", "https://api.minimaxi.com/v1")

        url = f"{base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        response = requests.post(url, headers=headers, json=payload)
        result = response.json()

        if "error" in result:
            raise ValueError(f"MiniMax API Error: {result['error']}")

        if "base_resp" in result and result["base_resp"].get("status_code") != 0:
            status_msg = result["base_resp"].get("status_msg", "Unknown error")
            raise ValueError(f"MiniMax API Error: {status_msg}")

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise ValueError(f"Unexpected response format: {result}")

    def _chat_openai(self, prompt, system_prompt=None):
        """Use requests to call OpenAI API"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set")

        provider_config = self.config["llm"]["providers"]["openai"]
        model = provider_config.get("model", "gpt-4o")
        base_url = provider_config.get("base_url", "https://api.openai.com/v1")

        url = f"{base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        return result["choices"][0]["message"]["content"]

    def _chat_anthropic(self, prompt, system_prompt=None):
        """Use requests to call Anthropic API"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set")

        provider_config = self.config["llm"]["providers"]["anthropic"]
        model = provider_config.get("model", "claude-3-5-sonnet-20241022")

        url = "https://api.anthropic.com/v1/messages"

        headers = {
            "x-api-key": api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        messages = [{"role": "user", "content": prompt}]

        payload = {
            "model": model,
            "max_tokens": 2000,
            "messages": messages,
        }

        if system_prompt:
            payload["system"] = system_prompt

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        return result["content"][0]["text"]

    def _chat_custom(self, prompt, system_prompt=None):
        """自定义大模型，从 .env 读取 CUSTOM_BASEURL、CUSTOM_APIKEY、CUSTOM_MODEL，使用 OpenAI 兼容接口"""
        load_dotenv(override=True)
        base_url = (os.getenv("CUSTOM_BASEURL") or "").rstrip("/")
        api_key = os.getenv("CUSTOM_APIKEY") or ""
        model = os.getenv("CUSTOM_MODEL") or ""

        if not base_url or not model:
            raise ValueError("请在 .env 中配置 CUSTOM_BASEURL 和 CUSTOM_MODEL")
        if not api_key:
            raise ValueError("请在 .env 中配置 CUSTOM_APIKEY")

        url = f"{base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        if "error" in result:
            raise ValueError(f"Custom API Error: {result['error']}")
        raise ValueError(f"Unexpected response format: {result}")

    def _chat_ollama(self, prompt, system_prompt=None):
        """Use requests to call Ollama API，URL 与模型从 .env 的 OLLAMA_BASE_URL、OLLAMA_MODEL 读取，未设置时回退到 config.json"""
        load_dotenv(override=True)
        base_url = os.getenv("OLLAMA_BASE_URL") or ""
        model = os.getenv("OLLAMA_MODEL") or ""
        if not base_url or not model:
            provider_config = self.config["llm"]["providers"].get("ollama", {})
            base_url = base_url or provider_config.get("base_url", "http://127.0.0.1:11434")
            model = model or provider_config.get("model", "llama3.2")

        base_url = base_url.rstrip("/")
        url = f"{base_url}/api/chat"

        headers = {
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if "message" in result and "content" in result["message"]:
            return result["message"]["content"]
        else:
            raise ValueError(f"Unexpected response format: {result}")

    def test_connection(self):
        try:
            response = self.chat("Hello, please respond with 'Connection successful!'")
            return {"success": True, "message": response}
        except Exception as e:
            return {"success": False, "message": str(e)}
