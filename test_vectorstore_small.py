#!/usr/bin/env python3
"""
ベクターストア保存の小規模テスト

エクセルファイルの最初の5行のみを使用してベクターストア保存が正常に動作するかテストします。
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

def create_small_test_file():
    """テスト用の小規模エクセルファイルを作成"""
    import pandas as pd
    
    # 元のファイルから最初の数行を読み取り
    original_file = "/Users/yuki/Desktop/rag chatbot2/backend/data/docs/rag用_架電リスト.xlsx"
    
    try:
        # 元ファイルの最初の6行（ヘッダー+5行のデータ）を読み込み
        df_original = pd.read_excel(original_file, sheet_name=0, nrows=6, engine='openpyxl')
        
        # テスト用ファイルとして保存
        test_file = "/Users/yuki/Desktop/rag chatbot2/test_sample.xlsx"
        df_original.to_excel(test_file, index=False, engine='openpyxl')
        
        print(f"✅ テスト用ファイル作成: {test_file}")
        print(f"📊 データサイズ: {len(df_original)} 行")
        
        return test_file
        
    except Exception as e:
        print(f"❌ テストファイル作成エラー: {e}")
        return None

def test_vectorstore_save():
    """ベクターストア保存テスト"""
    print("=" * 60)
    print("ベクターストア保存テスト（小規模）")
    print("=" * 60)
    
    # 設定確認
    config = Config()
    print(f"🔑 Gemini APIキー設定: {'あり' if config.GEMINI_API_KEY else 'なし'}")
    
    if not config.GEMINI_API_KEY:
        print("⚠️  Gemini APIキーが設定されていません。")
        print("   .envファイルを確認してください。")
        return False
    
    # テスト用ファイル作成
    test_file = create_small_test_file()
    if not test_file:
        return False
    
    try:
        # ExcelIngestorを初期化
        print(f"\n🔄 ExcelIngestor初期化中...")
        ingestor = ExcelIngestor()
        print("✅ ExcelIngestor初期化完了")
        
        # 既存のテストデータをクリア
        print(f"\n🧹 既存データクリア中...")
        try:
            collection = ingestor.vectorstore._collection
            # テストデータのみ削除（row_id 2-7の範囲）
            for row_id in range(2, 8):
                results = collection.get(where={"row_id": row_id})
                if results and results.get("ids"):
                    collection.delete(ids=results["ids"])
                    print(f"  削除: row_id {row_id}")
        except Exception as e:
            print(f"  クリア時の警告: {e}")
        
        # ファイル取り込み実行
        print(f"\n🔄 ファイル取り込み開始...")
        print(f"📁 対象: {test_file}")
        
        result = ingestor.ingest_excel_file(test_file)
        
        print(f"\n📊 取り込み結果:")
        print(f"  ステータス: {result.get('status', 'N/A')}")
        print(f"  メッセージ: {result.get('message', 'N/A')}")
        print(f"  処理レコード数: {result.get('processed_records', 'N/A')}")
        print(f"  総チャンク数: {result.get('total_chunks', 'N/A')}")
        
        if result.get("status") == "success":
            # ベクターストア確認
            print(f"\n🔍 ベクターストア確認中...")
            stats = ingestor.get_collection_stats()
            print(f"  総ドキュメント数: {stats.get('total_documents', 'N/A')}")
            
            # 保存されたデータのサンプル表示
            sample_metadata = stats.get('sample_metadata', [])
            if sample_metadata:
                print(f"  ✅ 保存データサンプル:")
                for i, meta in enumerate(sample_metadata[:3]):
                    company = meta.get('company', 'N/A')
                    status = meta.get('lead_status', 'N/A')
                    variants = meta.get('company_name_variants', 'N/A')
                    print(f"    {i+1}. 企業名: {company}")
                    print(f"       ステータス: {status}")
                    print(f"       バリアント: {variants[:50]}..." if len(str(variants)) > 50 else f"       バリアント: {variants}")
            
            print(f"\n🎉 ベクターストア保存テスト成功！")
            return True
        else:
            print(f"\n❌ 取り込み失敗: {result.get('message', 'N/A')}")
            return False
            
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # テストファイルをクリーンアップ
        try:
            if test_file and Path(test_file).exists():
                Path(test_file).unlink()
                print(f"🧹 テストファイル削除: {test_file}")
        except Exception as e:
            print(f"⚠️  テストファイル削除失敗: {e}")

def main():
    """メイン関数"""
    print("🧪 ベクターストア保存テスト（小規模）")
    print()
    
    success = test_vectorstore_save()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 ベクターストア保存テストが正常に完了しました！")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ ベクターストア保存テストで問題が発生しました。")
        print("=" * 60)

if __name__ == "__main__":
    main()
