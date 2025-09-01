#!/usr/bin/env python3
"""
row_id機能のテストスクリプト
セル参照から行番号を取得し、その行のデータのみを検索するテスト
"""

import requests
import json
import sys

# バックエンドのURL
BACKEND_URL = "http://localhost:8000"

def test_parse_row_from_cell():
    """セル参照解析のテスト"""
    print("=== セル参照解析テスト ===")
    
    # バックエンドのparse_row_from_cell相当の処理をテスト
    test_cases = [
        ("A2", 2),
        ("B10", 10),
        ("Z100", 100),
        ("AA1", 1),
    ]
    
    for cell, expected_row in test_cases:
        try:
            # セル参照から行番号を抽出（正規表現）
            import re
            match = re.match(r'^([A-Z]+)(\d+)$', cell.upper())
            if match:
                row_num = int(match.group(2))
                if row_num == expected_row:
                    print(f"✓ {cell} -> {row_num}")
                else:
                    print(f"✗ {cell} -> {row_num} (期待値: {expected_row})")
            else:
                print(f"✗ {cell} -> 解析失敗")
        except Exception as e:
            print(f"✗ {cell} -> エラー: {e}")

def test_company_by_cell_api():
    """企業データ取得APIのテスト"""
    print("\n=== 企業データ取得APIテスト ===")
    
    test_cells = ["A2", "A3", "A4", "A999"]  # A999は存在しない行
    
    for cell in test_cells:
        try:
            response = requests.get(
                f"{BACKEND_URL}/company/by-cell",
                params={"cell": cell},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ {cell} -> 行{data.get('row_id', '?')}: {data.get('message', '')}")
                if data.get('company_data'):
                    company_name = list(data['company_data'].values())[0] if data['company_data'] else "不明"
                    print(f"   企業名: {company_name}")
            elif response.status_code == 404:
                print(f"- {cell} -> 404: データが見つかりません")
            elif response.status_code == 400:
                print(f"✗ {cell} -> 400: {response.json().get('detail', '不正なリクエスト')}")
            else:
                print(f"✗ {cell} -> {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ {cell} -> 接続エラー: {e}")
        except Exception as e:
            print(f"✗ {cell} -> エラー: {e}")

def test_search_with_row_filter():
    """行フィルタ付きRAG検索のテスト"""
    print("\n=== 行フィルタ付きRAG検索テスト ===")
    
    test_cases = [
        {"query": "企業情報", "row_id": 2, "description": "行2に限定した検索"},
        {"query": "企業情報", "row_id": 3, "description": "行3に限定した検索"},
        {"query": "企業情報", "row_id": None, "description": "行フィルタなしの通常検索"},
    ]
    
    for case in test_cases:
        try:
            payload = {"query": case["query"]}
            if case["row_id"] is not None:
                payload["row_id"] = case["row_id"]
            
            response = requests.post(
                f"{BACKEND_URL}/search",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"✓ {case['description']}: {len(results)}件の結果")
                
                # 結果の行番号をチェック
                if case["row_id"] is not None:
                    for i, result in enumerate(results):
                        metadata = result.get("metadata", {})
                        result_row_id = metadata.get("row_id")
                        if result_row_id == case["row_id"]:
                            print(f"   結果{i+1}: 行{result_row_id} ✓")
                        else:
                            print(f"   結果{i+1}: 行{result_row_id} ✗ (期待値: 行{case['row_id']})")
                else:
                    print(f"   通常検索で{len(results)}件取得")
            else:
                print(f"✗ {case['description']}: {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"✗ {case['description']}: 接続エラー: {e}")
        except Exception as e:
            print(f"✗ {case['description']}: エラー: {e}")

def main():
    """メインテスト実行"""
    print("row_id機能の動作確認を開始します...")
    print(f"バックエンドURL: {BACKEND_URL}")
    
    # バックエンドの疎通確認
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ バックエンド接続OK")
        else:
            print(f"✗ バックエンド接続NG: {response.status_code}")
            return
    except Exception as e:
        print(f"✗ バックエンド接続失敗: {e}")
        print("バックエンドが起動していることを確認してください")
        return
    
    # 各テストを実行
    test_parse_row_from_cell()
    test_company_by_cell_api()
    test_search_with_row_filter()
    
    print("\n=== テスト完了 ===")
    print("✓ = 成功, ✗ = 失敗, - = 正常な404応答")

if __name__ == "__main__":
    main()
