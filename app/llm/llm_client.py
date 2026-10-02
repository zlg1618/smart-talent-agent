"""大模型客户端。

同时支持本地 Ollama 与任意 OpenAI 兼容云 API。
模型不可用时返回 None，由上层回退到规则引擎，保证项目可离线演示。
"""

import json
import re
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage

from app.config.settings import get_settings


class LLMClient:
    def __init__(self):
        self.settings = get_settings()
        self._chat = None
        self._init_error: str | None = None
        self._build()

    def _build(self):
        provider = (self.settings.llm_provider or "").lower()
        try:
            if provider == "ollama":
                from langchain_ollama import ChatOllama

                self._chat = ChatOllama(
                    base_url=self.settings.ollama_base_url,
                    model=self.settings.ollama_model,
                    temperature=self.settings.llm_temperature,
                )
            elif provider in ("openai_compatible", "openai", "cloud"):
                from langchain_openai import ChatOpenAI

                if not self.settings.openai_api_key:
                    self._init_error = "未配置 OPENAI_API_KEY"
                    return
                self._chat = ChatOpenAI(
                    api_key=self.settings.openai_api_key,
                    base_url=self.settings.openai_base_url,
                    model=self.settings.openai_model,
                    temperature=self.settings.llm_temperature,
                    timeout=self.settings.llm_timeout,
                )
            else:
                self._init_error = f"未知的 llm_provider：{provider}"
        except Exception as exc:  # 依赖未安装或初始化失败
            self._init_error = str(exc)
            self._chat = None

    @property
    def error(self) -> str | None:
        return self._init_error

    def available(self) -> bool:
        """客户端是否构建成功（不代表服务一定可达）。"""
        return self._chat is not None

    def probe(self) -> dict:
        """探测模型服务是否真实可达。

        本地 Ollama 做一次轻量接口探测；云 API 不做探测，避免无效请求。
        """
        provider = (self.settings.llm_provider or "").lower()
        if provider != "ollama":
            return {"reachable": None, "detail": "云 API 不做探测，实际调用时校验"}

        try:
            import httpx

            url = self.settings.ollama_base_url.rstrip("/") + "/api/tags"
            resp = httpx.get(url, timeout=3)
            return {
                "reachable": resp.status_code == 200,
                "detail": f"HTTP {resp.status_code}",
            }
        except Exception as exc:
            return {"reachable": False, "detail": str(exc)}

    def invoke(self, system_prompt: str, user_prompt: str) -> str | None:
        """调用模型，失败返回 None。"""
        if not self._chat:
            return None
        try:
            resp = self._chat.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            )
            content = getattr(resp, "content", None)
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            return content
        except Exception:
            return None

    def invoke_json(self, system_prompt: str, user_prompt: str) -> dict | None:
        """调用模型并解析 JSON，失败返回 None。"""
        raw = self.invoke(system_prompt, user_prompt)
        if not raw:
            return None
        return extract_json(raw)


def extract_json(text: str) -> dict | None:
    """从模型输出中提取第一个 JSON 对象，兼容 ```json 代码块。"""
    if not text:
        return None

    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()

    candidates = []
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None


@lru_cache
def get_llm_client() -> LLMClient:
    return LLMClient()
