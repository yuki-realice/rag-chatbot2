import os
from typing import List
import httpx

GEMINI_EMBED_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"

class GeminiEmbeddingError(Exception):
    pass


def _get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise GeminiEmbeddingError("GEMINI_API_KEY が設定されていません。.env を確認してください。")
    return key


def embed_content(text: str) -> List[float]:
    """Call Gemini Embeddings API (text-embedding-004:embedContent)."""
    api_key = _get_api_key()
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }
    payload = {
        "model": "models/text-embedding-004",
        "content": {
            "parts": [{"text": text}]
        },
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(GEMINI_EMBED_ENDPOINT, headers=headers, json=payload)
            if resp.status_code != 200:
                raise GeminiEmbeddingError(
                    f"Gemini embed error: {resp.status_code} {resp.text}"
                )
            data = resp.json()
            embedding = (data.get("embedding") or {})
            values = embedding.get("values") or embedding.get("value")
            if not isinstance(values, list):
                raise GeminiEmbeddingError("Invalid embedding response shape")
            return values  # type: ignore[return-value]
    except httpx.HTTPError as e:
        raise GeminiEmbeddingError(f"HTTP error: {e}") from e


class GeminiEmbeddings:
    """LangChain互換の埋め込みクラス（embed_documents / embed_query）。"""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [embed_content(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return embed_content(text)
