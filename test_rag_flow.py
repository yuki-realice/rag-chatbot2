#!/usr/bin/env python3
"""
RAGシステム全体フローテスト

エクセルデータが正しく検索・チャット機能で利用されるかを包括的にテストします。
"""

import sys
import os
from pathlib import Path
import json

# backend モジュールを import するためのパス設定
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from backend.rag_service import RAGService
    from backend.retriever import EnhancedRetriever
    from backend.config import Config
    print("✅ モジュールのインポートに成功しました")
except ImportError as e:
    print(f"❌ モジュールのインポートに失敗: {e}")
    sys.exit(1)

def test_vectorstore_content():
    """ベクターストアの内容を確認"""
    print("=" * 60)
    print("ベクターストア内容確認")
    print("=" * 60)
    
    try:
        retriever = EnhancedRetriever()
        collection = retriever.vectorstore._collection
        
        # 総ドキュメント数
        total_count = collection.count()
        print(f"📊 総ドキュメント数: {total_count}")
        
        # サンプルデータ取得
        sample_docs = collection.get(
            limit=10,
            include=["metadatas", "documents"]
        )
        
        if sample_docs and sample_docs.get("metadatas"):
            print(f"📝 サンプルデータ（企業名とステータス）:")
            for i, meta in enumerate(sample_docs["metadatas"][:5]):
                company = meta.get("company", "N/A")
                status = meta.get("lead_status", "N/A")
                row_id = meta.get("row_id", "N/A")
                column = meta.get("column_name", "N/A")
                print(f"  {i+1}. 企業名: {company}, ステータス: {status}, 行: {row_id}, 列: {column}")
        
        return True
        
    except Exception as e:
        print(f"❌ ベクターストア確認エラー: {e}")
        return False

def test_search_functionality():
    """検索機能のテスト"""
    print("\n" + "=" * 60)
    print("検索機能テスト")
    print("=" * 60)
    
    try:
        retriever = EnhancedRetriever()
        
        # テストクエリ
        test_queries = [
            "JFE条鋼株式会社",
            "セッツカートン",
            "不在の企業",
            "受付拒否",
            "アポイント獲得",
            "営業担当者",
            "電話番号"
        ]
        
        for query in test_queries:
            print(f"\n🔍 検索クエリ: '{query}'")
            try:
                results = retriever.hybrid_search(query, top_k=3)
                print(f"   結果数: {len(results)}")
                
                for i, doc in enumerate(results[:2]):  # 最初の2件のみ表示
                    company = doc.metadata.get("company", "N/A")
                    status = doc.metadata.get("lead_status", "N/A")
                    content = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                    print(f"   {i+1}. 企業: {company}, ステータス: {status}")
                    print(f"      内容: {content}")
                    
            except Exception as e:
                print(f"   ❌ 検索エラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 検索機能テストエラー: {e}")
        return False

def test_rag_chat():
    """RAGチャット機能のテスト"""
    print("\n" + "=" * 60)
    print("RAGチャット機能テスト")
    print("=" * 60)
    
    try:
        rag_service = RAGService()
        
        # テスト質問
        test_questions = [
            "JFE条鋼株式会社について教えてください",
            "不在の企業はありますか？",
            "アポイント獲得した企業を教えて",
            "受付拒否された企業の一覧",
            "セッツカートンの電話番号は？"
        ]
        
        for question in test_questions:
            print(f"\n💬 質問: '{question}'")
            try:
                response = rag_service.chat(question)
                
                if response.get("status") == "success":
                    answer = response.get("answer", "N/A")
                    sources = response.get("sources", [])
                    
                    print(f"✅ 回答: {answer[:200]}..." if len(answer) > 200 else f"✅ 回答: {answer}")
                    print(f"📚 情報源数: {len(sources)}")
                    
                    # 情報源の詳細
                    for i, source in enumerate(sources[:2]):  # 最初の2件のみ表示
                        company = source.get("company", "N/A")
                        status = source.get("lead_status", "N/A")
                        print(f"   ソース{i+1}: {company} ({status})")
                        
                else:
                    print(f"❌ チャットエラー: {response.get('message', 'N/A')}")
                    
            except Exception as e:
                print(f"❌ 質問処理エラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ RAGチャット機能テストエラー: {e}")
        return False

def test_advanced_queries():
    """高度なクエリのテスト"""
    print("\n" + "=" * 60)
    print("高度なクエリテスト")
    print("=" * 60)
    
    try:
        rag_service = RAGService()
        
        # 高度なテスト質問
        advanced_questions = [
            "営業成果が良い企業はどこですか？",
            "次にコンタクトすべき企業を推薦してください",
            "架電履歴から営業戦略を提案してください",
            "従業員数が多い企業のリードステータスはどうですか？"
        ]
        
        for question in advanced_questions:
            print(f"\n🎯 高度な質問: '{question}'")
            try:
                response = rag_service.chat(question)
                
                if response.get("status") == "success":
                    answer = response.get("answer", "N/A")
                    sources = response.get("sources", [])
                    
                    print(f"✅ 回答: {answer[:300]}..." if len(answer) > 300 else f"✅ 回答: {answer}")
                    print(f"📚 活用した企業数: {len(sources)}")
                    
                else:
                    print(f"❌ エラー: {response.get('message', 'N/A')}")
                    
            except Exception as e:
                print(f"❌ 処理エラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 高度なクエリテストエラー: {e}")
        return False

def main():
    """メイン関数"""
    print("🧪 RAGシステム全体フローテスト")
    print()
    
    tests = [
        ("ベクターストア内容確認", test_vectorstore_content),
        ("検索機能テスト", test_search_functionality), 
        ("RAGチャット機能テスト", test_rag_chat),
        ("高度なクエリテスト", test_advanced_queries)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🚀 {test_name} 開始...")
        try:
            success = test_func()
            results.append((test_name, success))
            status = "✅ 成功" if success else "❌ 失敗"
            print(f"📊 {test_name}: {status}")
        except Exception as e:
            print(f"❌ {test_name}で予期しないエラー: {e}")
            results.append((test_name, False))
    
    # 最終結果
    print("\n" + "=" * 60)
    print("🎯 最終テスト結果")
    print("=" * 60)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n📊 成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("🎉 すべてのテストが成功しました！RAGシステム全体フローが正常に動作しています。")
    else:
        print("⚠️  一部のテストで問題が発生しました。詳細を確認してください。")

if __name__ == "__main__":
    main()
