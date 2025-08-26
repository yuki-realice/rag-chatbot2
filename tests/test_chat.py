import pytest
import sys
import os
from pathlib import Path

# バックエンドディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from rag_service import RAGService

class TestChat:
    def setup_method(self):
        """テスト前のセットアップ"""
        self.rag_service = RAGService()
    
    def test_chat_empty_message(self):
        """空のメッセージでのチャットテスト"""
        result = self.rag_service.chat("")
        assert result["status"] in ["warning", "error"]
    
    def test_chat_without_documents(self):
        """ドキュメントがない状態でのチャットテスト"""
        # ベクトルストアが空の場合のテスト
        result = self.rag_service.chat("テストメッセージ")
        # 結果は警告またはエラーになる可能性がある
        assert "status" in result
    
    def test_chat_response_structure(self):
        """チャット応答の構造テスト"""
        result = self.rag_service.chat("テストメッセージ")
        
        # 基本的な構造チェック
        assert "status" in result
        
        if result["status"] == "success":
            assert "answer" in result
            assert "sources" in result
            assert isinstance(result["sources"], list)
        elif result["status"] == "warning":
            assert "message" in result
        elif result["status"] == "error":
            assert "message" in result
    
    def test_chat_with_valid_message(self):
        """有効なメッセージでのチャットテスト"""
        test_message = "これはテスト用の質問です。"
        result = self.rag_service.chat(test_message)
        
        # 結果が辞書形式であることを確認
        assert isinstance(result, dict)
        assert "status" in result

if __name__ == "__main__":
    pytest.main([__file__])

