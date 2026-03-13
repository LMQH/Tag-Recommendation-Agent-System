"""
Qwen API 客户端：
- Embedding: OpenAI compatible-mode（openai SDK）
- Rerank: DashScope rerank HTTP 接口（requests）
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import requests
from openai import OpenAI

from search_data.config import (
    QWEN_API_KEY,
    QWEN_BASE_URL,
    QWEN_EMBEDDING_MODEL,
    QWEN_RERANK_BASE_URL,
    QWEN_RERANK_INSTRUCT,
    QWEN_RERANK_MODEL,
    QWEN_RERANK_PATH,
)


class QwenConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmbeddingResult:
    model: str
    embeddings: list[list[float]]

    @property
    def dim(self) -> int:
        return len(self.embeddings[0]) if self.embeddings else 0


class QwenEmbeddingClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or QWEN_API_KEY
        self.base_url = base_url or QWEN_BASE_URL
        self.model = model or QWEN_EMBEDDING_MODEL
        if not self.api_key:
            raise QwenConfigError(
                "缺少 Qwen API Key：请设置环境变量 DASHSCOPE_API_KEY，或在本机私密文件写入 key（默认 ~/.config/yzh/dashscope_api_key，"
                "也可用环境变量 DASHSCOPE_API_KEY_FILE 指定文件路径）。"
            )
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def embed_texts(self, texts: Sequence[str]) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(model=self.model, embeddings=[])
        # DashScope embedding 对 batch size 有上限（你遇到的是 <=10）
        max_batch = 10
        all_embeddings: list[list[float]] = []
        used_model = self.model
        for i in range(0, len(texts), max_batch):
            chunk = list(texts[i : i + max_batch])
            resp = self._client.embeddings.create(model=self.model, input=chunk)
            used_model = resp.model
            # OpenAI 兼容：resp.data[i].embedding
            all_embeddings.extend([item.embedding for item in resp.data])
        return EmbeddingResult(model=used_model, embeddings=all_embeddings)

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text]).embeddings[0]


@dataclass(frozen=True)
class RerankItem:
    index: int
    score: float


@dataclass(frozen=True)
class RerankResult:
    model: str
    items: list[RerankItem]


class QwenRerankClient:
    """
    说明：
    - DashScope 的 rerank 通常不是 OpenAI compatible 接口，走独立 HTTP。
    - 这里采用常见的请求格式：
        POST {base_url}{path}
        Authorization: Bearer <DASHSCOPE_API_KEY>
        {
          "model": "qwen3-rerank",
          "input": { "query": "...", "documents": ["...", "..."] }
        }
    - 如果你们实际接口字段有差异，只需要改这里的 payload/解析即可。
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        path: Optional[str] = None,
        model: Optional[str] = None,
        instruct: Optional[str] = None,
        timeout_s: int = 30,
    ):
        self.api_key = api_key or QWEN_API_KEY
        self.base_url = (base_url or QWEN_RERANK_BASE_URL).rstrip("/")
        self.path = path or QWEN_RERANK_PATH
        self.model = model or QWEN_RERANK_MODEL
        self.instruct = instruct or QWEN_RERANK_INSTRUCT
        self.timeout_s = timeout_s
        if not self.api_key:
            raise QwenConfigError(
                "缺少 Qwen API Key：请设置环境变量 DASHSCOPE_API_KEY，或在本机私密文件写入 key（默认 ~/.config/yzh/dashscope_api_key，"
                "也可用环境变量 DASHSCOPE_API_KEY_FILE 指定文件路径）。"
            )

    def rerank(self, query: str, documents: Sequence[str]) -> RerankResult:
        if not documents:
            return RerankResult(model=self.model, items=[])

        url = f"{self.base_url}{self.path}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        # OpenAI 兼容 rerank 端点（你给的 curl 示例）：/compatible-api/v1/reranks
        # payload:
        # {
        #   "model": "qwen3-rerank",
        #   "documents": ["...", "..."],
        #   "query": "...",
        #   "top_n": 2,
        #   "instruct": "..."
        # }
        if "/compatible-api/v1/reranks" in self.path or self.path.rstrip("/").endswith("/reranks"):
            payload: dict[str, Any] = {
                "model": self.model,
                "documents": list(documents),
                "query": query,
                "top_n": min(len(documents), 50),
                "instruct": self.instruct,
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout_s)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"qwen3-rerank 请求失败 (HTTP {resp.status_code}) url={url} body={resp.text}"
                )
            data = resp.json()
        else:
            # 兼容旧 services 风格（如果你后续要切回去）
            payload = {
                "model": self.model,
                "task": "text-rerank",
                "input": {"query": query, "documents": list(documents)},
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout_s)
            if resp.status_code >= 400:
                raise RuntimeError(
                    f"qwen3-rerank 请求失败 (HTTP {resp.status_code}) url={url} body={resp.text}"
                )
            data = resp.json()

        # 兼容几种可能返回：results / output.results
        results = None
        if isinstance(data, dict):
            if "results" in data:
                results = data.get("results")
            elif "output" in data and isinstance(data["output"], dict) and "results" in data["output"]:
                results = data["output"]["results"]

        if results is None:
            raise RuntimeError(f"无法解析 rerank 响应：{data}")

        items: list[RerankItem] = []
        for r in results:
            # 常见字段：index / relevance_score 或 score
            idx = r.get("index")
            score = r.get("relevance_score", r.get("score"))
            if idx is None or score is None:
                continue
            items.append(RerankItem(index=int(idx), score=float(score)))

        # 有些接口可能返回已排序，这里不强依赖，调用方可以再次排序
        return RerankResult(model=data.get("model", self.model), items=items)

