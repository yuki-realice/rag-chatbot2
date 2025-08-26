import pytest
import sys
import os
from pathlib import Path

# バックエンドディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from rag_service import RAGService

class TestRAGService:
    def setup_method(self):
        """テスト前のセットアップ"""
        self.rag_service = RAGService()
    
    def test_rag_service_initialization(self):
        """RAGServiceの初期化テスト"""
        assert self.rag_service is not None
        assert self.rag_service.config is not None
        assert self.rag_service.embeddings is not None
        assert self.rag_service.llm is not None
    
    def test_tiktoken_len(self):
        """トークン数計算のテスト"""
        test_text = "これはテスト用のテキストです。"
        token_count = self.rag_service._tiktoken_len(test_text)
        assert isinstance(token_count, int)
        assert token_count > 0
    
    def test_text_splitter(self):
        """テキスト分割のテスト"""
        test_text = "これは長いテキストです。" * 100  # 長いテキストを作成
        chunks = self.rag_service.text_splitter.split_text(test_text)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        
        # 各チャンクが適切なサイズであることを確認
        for chunk in chunks:
            token_count = self.rag_service._tiktoken_len(chunk)
            assert token_count <= self.rag_service.config.RAG_CHUNK_SIZE + 100  # オーバーラップを考慮
    
    def test_ingest_documents_no_files(self):
        """ファイルが存在しない場合のインデックス化テスト"""
        # 存在しないディレクトリを指定
        result = self.rag_service.ingest_documents([])
        assert result["status"] == "warning"
        assert "No documents found" in result["message"]

if __name__ == "__main__":
    pytest.main([__file__])

