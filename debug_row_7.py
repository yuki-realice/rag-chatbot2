"""行7の詳細データ調査スクリプト（修正版）"""

import sys
import os

# パスの設定
backend_path = '/Users/yuki/Desktop/rag chatbot2/backend'
sys.path.insert(0, backend_path)

try:
    # 必要なモジュールをインポート
    from config import Config
    from gemini import GeminiEmbeddings
    from langchain_community.vectorstores import Chroma
    from langchain.schema import Document
    import chromadb
    from pathlib import Path
    
    def debug_row_7():
        print("🔍 行7の詳細データ調査")
        print("=" * 60)
        
        try:
            # ChromaDBクライアントを直接作成
            config = Config()
            chroma_client = chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))
            collection = chroma_client.get_collection("leads")
            
            # 行7の全データを取得
            results = collection.get(
                where={"excel_row": 7},
                include=["metadatas", "documents"]
            )
            
            if not results or not results.get("metadatas"):
                print("❌ 行7のデータが見つかりません")
                return
            
            print(f"📊 行7の総セル数: {len(results['metadatas'])}")
            
            # 各セルの詳細を表示
            for i, (meta, doc) in enumerate(zip(results["metadatas"], results["documents"])):
                print(f"\n🔸 セル {i+1}:")
                print(f"   列名: {meta.get('column_name', 'N/A')}")
                print(f"   セル値: {meta.get('cell_value', 'N/A')}")
                print(f"   Document内容: '{doc}'")
                print(f"   企業名: {meta.get('company', 'N/A')}")
                print(f"   ステータス: {meta.get('lead_status', 'N/A')}")
                if i >= 4:  # 最初の5セルのみ表示
                    print(f"   ... 他 {len(results['metadatas'])-5} セル")
                    break
            
            # 統合テスト用データ作成
            print(f"\n🔧 統合テスト:")
            
            # セルデータを列順にソート
            cell_data = []
            for meta, doc in zip(results["metadatas"], results["documents"]):
                cell_data.append({
                    "column_index": meta.get("column_index", 999),
                    "column_name": meta.get("column_name", ""),
                    "cell_value": meta.get("cell_value", ""),
                    "content": doc,
                    "metadata": meta
                })
            
            cell_data.sort(key=lambda x: x["column_index"])
            
            # 統合コンテンツを手動作成
            row_parts = []
            for cell in cell_data[:10]:  # 最初の10セルのみ
                col_name = cell["column_name"]
                cell_value = cell["cell_value"]
                if col_name and cell_value:
                    row_parts.append(f"{col_name}: {cell_value}")
            
            integrated_content = " | ".join(row_parts)
            print(f"   統合後内容: '{integrated_content}'")
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            import traceback
            traceback.print_exc()
    
    if __name__ == "__main__":
        debug_row_7()
        
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    print("   必要なモジュールが見つかりません")
except Exception as e:
    print(f"❌ 予期しないエラー: {e}")
    import traceback
    traceback.print_exc()
