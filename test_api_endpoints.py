#!/usr/bin/env python3
"""
APIエンドポイント連携テスト

フロントエンドとバックエンド間のAPI通信が正しく動作するかをテストします。
"""

import requests
import json
import time
import sys
from typing import Dict, Any

# APIベースURL
BASE_URL = "http://localhost:8000"

def test_health_check():
    """ヘルスチェックAPIのテスト"""
    print("=" * 60)
    print("ヘルスチェックAPIテスト")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ ヘルスチェック成功")
            print(f"   ステータス: {data.get('status', 'N/A')}")
            print(f"   サービス: {data.get('services', {})}")
            return True
        else:
            print(f"❌ ヘルスチェック失敗 (status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 接続エラー: {e}")
        return False

def test_chat_api():
    """チャットAPIのテスト"""
    print("\n" + "=" * 60)
    print("チャットAPIテスト")
    print("=" * 60)
    
    test_messages = [
        "JFE条鋼株式会社について教えてください",
        "不在の企業はありますか？",
        "アポイント獲得した企業を教えて",
        "営業成果の良い企業はどこですか？"
    ]
    
    success_count = 0
    
    for i, message in enumerate(test_messages):
        print(f"\n💬 テスト{i+1}: '{message}'")
        
        try:
            payload = {"message": message}
            response = requests.post(
                f"{BASE_URL}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "N/A")
                sources = data.get("sources", [])
                
                print(f"✅ 成功 (status: {response.status_code})")
                print(f"   回答: {answer[:100]}..." if len(answer) > 100 else f"   回答: {answer}")
                print(f"   情報源数: {len(sources)}")
                success_count += 1
                
            else:
                print(f"❌ 失敗 (status: {response.status_code})")
                print(f"   レスポンス: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ リクエストエラー: {e}")
    
    print(f"\n📊 チャットAPIテスト結果: {success_count}/{len(test_messages)} 成功")
    return success_count == len(test_messages)

def test_search_api():
    """検索APIのテスト"""
    print("\n" + "=" * 60)
    print("検索APIテスト")
    print("=" * 60)
    
    test_queries = [
        "JFE条鋼",
        "セッツカートン",
        "不在",
        "受付拒否",
        "アポイント獲得"
    ]
    
    success_count = 0
    
    for i, query in enumerate(test_queries):
        print(f"\n🔍 検索テスト{i+1}: '{query}'")
        
        try:
            payload = {"query": query, "limit": 3}
            response = requests.post(
                f"{BASE_URL}/search",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                
                print(f"✅ 成功 (status: {response.status_code})")
                print(f"   検索結果数: {len(results)}")
                
                for j, result in enumerate(results[:2]):  # 最初の2件のみ表示
                    company = result.get("metadata", {}).get("company", "N/A")
                    status = result.get("metadata", {}).get("lead_status", "N/A")
                    content = result.get("content", "N/A")
                    print(f"   結果{j+1}: {company} ({status})")
                    print(f"          内容: {content[:80]}..." if len(content) > 80 else f"          内容: {content}")
                
                success_count += 1
                
            else:
                print(f"❌ 失敗 (status: {response.status_code})")
                print(f"   レスポンス: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ リクエストエラー: {e}")
    
    print(f"\n📊 検索APIテスト結果: {success_count}/{len(test_queries)} 成功")
    return success_count == len(test_queries)

def test_company_api():
    """企業情報APIのテスト"""
    print("\n" + "=" * 60)
    print("企業情報APIテスト")
    print("=" * 60)
    
    try:
        # セル情報でのクエリテスト
        params = {"phone": "03-5777-3811"}  # JFE条鋼の電話番号
        response = requests.get(
            f"{BASE_URL}/company/by-cell",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            companies = data.get("companies", [])
            
            print(f"✅ 企業検索成功")
            print(f"   見つかった企業数: {len(companies)}")
            
            for company in companies[:3]:  # 最初の3件のみ表示
                name = company.get("company_name", "N/A")
                status = company.get("lead_status", "N/A") 
                phone = company.get("phone", "N/A")
                print(f"   企業: {name}, ステータス: {status}, 電話: {phone}")
            
            return True
        else:
            print(f"❌ 企業検索失敗 (status: {response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
        return False

def test_stats_api():
    """統計APIのテスト"""
    print("\n" + "=" * 60)
    print("統計APIテスト")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/search-stats", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            total_docs = data.get("total_documents", 0)
            sample_metadata = data.get("sample_metadata", [])
            
            print(f"✅ 統計取得成功")
            print(f"   総ドキュメント数: {total_docs}")
            print(f"   サンプルメタデータ数: {len(sample_metadata)}")
            
            return True
        else:
            print(f"❌ 統計取得失敗 (status: {response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ リクエストエラー: {e}")
        return False

def main():
    """メイン関数"""
    print("🧪 APIエンドポイント連携テスト")
    print("🚀 バックエンドサーバーが http://localhost:8000 で起動していることを確認してください")
    print()
    
    # サーバー起動確認
    print("📡 サーバー接続確認中...")
    time.sleep(2)
    
    tests = [
        ("ヘルスチェックAPI", test_health_check),
        ("チャットAPI", test_chat_api),
        ("検索API", test_search_api),
        ("企業情報API", test_company_api),
        ("統計API", test_stats_api)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🚀 {test_name}テスト 開始...")
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
    print("🎯 APIテスト最終結果")
    print("=" * 60)
    
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    
    for test_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {test_name}")
    
    print(f"\n📊 成功率: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
    
    if success_count == total_count:
        print("🎉 すべてのAPIテストが成功しました！フロントエンドとの連携準備完了です。")
    else:
        print("⚠️  一部のAPIテストで問題が発生しました。")
        print("   バックエンドサーバーが起動していることを確認してください:")
        print("   cd backend && python -m uvicorn main:app --reload --port 8000")

if __name__ == "__main__":
    main()
