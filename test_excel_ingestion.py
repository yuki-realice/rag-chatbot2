#!/usr/bin/env python3
"""
Excel データの RAG システム取り込みテスト

実際の ExcelIngestor クラスを使用してデータベースへの取り込み処理をテストします。
"""

import sys
import os
from pathlib import Path

# backend モジュールを import するためのパス設定
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from backend.ingest_excel import ExcelIngestor
    from backend.config import Config
    print("✅ モジュールのインポートに成功しました")
except ImportError as e:
    print(f"❌ モジュールのインポートに失敗: {e}")
    sys.exit(1)

def test_excel_ingestor():
    """ExcelIngestorを使った実際の取り込みテスト"""
    print("=" * 60)
    print("Excel RAGシステム取り込みテスト")
    print("=" * 60)
    
    try:
        # 設定確認
        config = Config()
        print(f"📁 データディレクトリ: {config.DATA_DIR}")
        print(f"📊 Chromaストアディレクトリ: {config.CHROMA_STORE_DIR}")
        print(f"🔑 Gemini APIキー設定: {'あり' if config.GEMINI_API_KEY else 'なし'}")
        
        if not config.GEMINI_API_KEY:
            print("⚠️  Gemini APIキーが設定されていません。設定なしでテストを続行します...")
            print("   実際の埋め込み処理はスキップされる可能性があります。")
        
        # エクセルファイルパス
        excel_file = "/Users/yuki/Desktop/rag chatbot2/backend/data/docs/rag用_架電リスト.xlsx"
        
        print(f"\n📁 処理対象ファイル: {excel_file}")
        
        # ExcelIngestorを作成（APIキーがなくても基本的な処理はテスト可能）
        try:
            ingestor = ExcelIngestor()
            print("✅ ExcelIngestorの初期化に成功")
        except ValueError as e:
            if "GEMINI_API_KEY" in str(e):
                print("⚠️  Gemini APIキーエラー。.envファイルを確認してください。")
                print("   代替として、基本的なExcel読み込み処理のみテストします。")
                return test_excel_loading_only(excel_file)
            else:
                raise
        
        # ファイル取り込み実行
        print(f"\n🔄 ファイル取り込み開始...")
        result = ingestor.ingest_excel_file(excel_file)
        
        print(f"📊 取り込み結果:")
        print(f"  ステータス: {result.get('status', 'N/A')}")
        print(f"  メッセージ: {result.get('message', 'N/A')}")
        print(f"  処理レコード数: {result.get('processed_records', 'N/A')}")
        print(f"  総チャンク数: {result.get('total_chunks', 'N/A')}")
        print(f"  コレクション: {result.get('collection', 'N/A')}")
        
        # コレクション統計の取得
        if result.get("status") == "success":
            print(f"\n📊 コレクション統計取得中...")
            stats = ingestor.get_collection_stats()
            print(f"  コレクション名: {stats.get('collection_name', 'N/A')}")
            print(f"  総ドキュメント数: {stats.get('total_documents', 'N/A')}")
            
            # サンプルメタデータの表示
            sample_metadata = stats.get('sample_metadata', [])
            if sample_metadata:
                print(f"  サンプルメタデータ:")
                for i, meta in enumerate(sample_metadata[:3]):
                    company = meta.get('company', 'N/A')
                    status = meta.get('lead_status', 'N/A')
                    row_id = meta.get('row_id', 'N/A')
                    print(f"    {i+1}. 企業名: {company}, ステータス: {status}, 行: {row_id}")
        
        return result.get("status") == "success"
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_excel_loading_only(excel_file):
    """APIキーなしでのExcel読み込み処理のみテスト"""
    print("\n📊 Excel読み込み処理のみテスト")
    
    try:
        # ExcelIngestorのインスタンス化をスキップして、直接読み込み処理をテスト
        import pandas as pd
        
        # Excelファイルの基本チェック
        path = Path(excel_file)
        if not path.exists():
            print(f"❌ ファイルが見つかりません: {excel_file}")
            return False
        
        # シート情報取得
        xl_file = pd.ExcelFile(str(path), engine='openpyxl')
        sheet_names = xl_file.sheet_names
        print(f"📋 利用可能シート: {sheet_names}")
        
        # 最初のシートでテスト
        sheet_name = sheet_names[0]
        df_raw = pd.read_excel(str(path), sheet_name=sheet_name, engine='openpyxl', dtype=str, header=None)
        df_raw = df_raw.fillna("")
        
        print(f"✅ Excel読み込み成功")
        print(f"📐 データサイズ: {df_raw.shape[0]} 行 × {df_raw.shape[1]} 列")
        
        # データサンプル表示
        if len(df_raw) >= 2:
            header_row = df_raw.iloc[0].tolist()
            first_data_row = df_raw.iloc[1].tolist()
            
            print(f"🏷️  ヘッダー: {header_row[:8]}...")  # 最初の8列のみ表示
            print(f"📝 データ例: {first_data_row[:8]}...")  # 最初の8列のみ表示
        
        return True
        
    except Exception as e:
        print(f"❌ Excel読み込みエラー: {e}")
        return False

def main():
    """メイン関数"""
    print("🧪 Excel RAGシステム取り込みテスト")
    print()
    
    success = test_excel_ingestor()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 RAGシステム取り込みテストが正常に完了しました！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  テストが完了しましたが、一部で問題が発生した可能性があります。")
        print("=" * 60)

if __name__ == "__main__":
    main()
