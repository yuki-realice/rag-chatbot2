#!/usr/bin/env python3
"""
Excelファイルの全行とベクトルストア保存状況の包括的検証スクリプト
"""

import sys
import os
import pandas as pd
from pathlib import Path

# backend モジュールを import するためのパス設定
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    from backend.retriever import EnhancedRetriever
    from backend.config import Config
    from backend.ingest_excel import ExcelIngestor
    from backend.rag_service import RAGService
    from backend.utils.name_normalize import normalize_name, build_name_variants
    print("✅ モジュールのインポートに成功しました")
except ImportError as e:
    print(f"❌ モジュールのインポートに失敗: {e}")
    sys.exit(1)

def analyze_excel_file():
    """Excelファイルの詳細分析"""
    excel_file = "/Users/yuki/Desktop/rag chatbot2/backend/data/docs/rag用_架電リスト.xlsx"
    
    print("=" * 60)
    print("Excelファイル詳細分析")
    print("=" * 60)
    
    try:
        # ファイル基本情報
        path = Path(excel_file)
        if not path.exists():
            print(f"❌ ファイルが見つかりません: {excel_file}")
            return None, None
        
        print(f"📁 ファイル: {path.name}")
        print(f"📊 サイズ: {path.stat().st_size / 1024:.1f} KB")
        
        # Excel読み込み（生データ）
        xl_file = pd.ExcelFile(str(path), engine='openpyxl')
        sheet_names = xl_file.sheet_names
        print(f"📋 シート: {sheet_names}")
        
        # 最初のシート読み込み
        sheet_name = sheet_names[0]
        df_raw = pd.read_excel(str(path), sheet_name=sheet_name, engine='openpyxl', dtype=str, header=None)
        df_raw = df_raw.fillna("")
        
        print(f"📐 生データサイズ: {df_raw.shape[0]} 行 × {df_raw.shape[1]} 列")
        
        # ヘッダー処理（ExcelIngestorと同じ処理）
        if len(df_raw) < 2:
            print("❌ データ不足")
            return None, None
            
        header_row = df_raw.iloc[0].tolist()
        print(f"🏷️  ヘッダー行: {header_row[:8]}...")
        
        # 処理済みヘッダー作成
        processed_header = []
        for i, cell_value in enumerate(header_row):
            if cell_value and cell_value.strip():
                processed_header.append(cell_value.strip())
            else:
                col_letter = chr(ord('A') + i)
                processed_header.append(f"列{col_letter}")
        
        # データ部分取得
        df = df_raw.iloc[1:].copy()
        df.columns = processed_header
        
        # 列名標準化
        df = df.rename(columns={
            "企業名": "company_name",
            "会社名": "company_name", 
            "ステータス": "lead_status",
            "リードステータス": "lead_status"
        })
        
        print(f"📊 処理後のデータサイズ: {len(df)} 行")
        print(f"📋 列名: {list(df.columns)[:8]}...")
        
        return df, processed_header
        
    except Exception as e:
        print(f"❌ Excelファイル分析エラー: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def analyze_data_processing(df):
    """データ処理の詳細分析（ExcelIngestorのロジックをシミュレート）"""
    print("\n" + "=" * 60)
    print("データ処理分析")
    print("=" * 60)
    
    if df is None:
        return {}
    
    # row_id列を付与（ExcelIngestorと同じ処理）
    df = df.reset_index().assign(row_id=lambda d: d.index + 2)
    
    columns = list(df.columns)
    
    # 企業名列とリードステータス列を特定
    company_col = None
    lead_status_col = None
    
    if "company_name" in columns:
        company_col = "company_name"
    else:
        company_col = columns[0] if len(columns) > 0 else None
        
    if "lead_status" in columns:
        lead_status_col = "lead_status"
    else:
        lead_status_col = columns[6] if len(columns) > 6 else None
    
    print(f"🏢 企業名列: '{company_col}'")
    print(f"📊 リードステータス列: '{lead_status_col}'")
    
    # 各行の処理状況を分析
    valid_rows = 0
    skipped_rows = 0
    skipped_reasons = {}
    valid_companies = set()
    
    print(f"\n📝 行別処理状況分析:")
    print(f"{'行番号':<6} {'企業名':<30} {'処理状況':<15} {'理由'}")
    print("-" * 80)
    
    for idx, row in df.iterrows():
        excel_row_num = int(row['row_id'])
        company = str(row[company_col]).strip() if company_col else ""
        
        # ExcelIngestorと同じ条件でチェック
        skip_reason = None
        
        if not company or company.lower() in ['nan', 'none', ''] or company == company_col:
            skip_reason = "企業名無効"
            skipped_rows += 1
            skipped_reasons[skip_reason] = skipped_reasons.get(skip_reason, 0) + 1
        else:
            valid_rows += 1
            valid_companies.add(company)
            skip_reason = "処理成功"
        
        # 最初の50行の詳細表示
        if excel_row_num <= 51:  # ヘッダー行+50行
            status = "✅ 処理" if skip_reason == "処理成功" else "❌ スキップ"
            print(f"{excel_row_num:<6} {company[:28]:<30} {status:<15} {skip_reason}")
    
    print(f"\n📊 処理統計:")
    print(f"  総データ行数: {len(df)}")
    print(f"  有効行数: {valid_rows}")
    print(f"  スキップ行数: {skipped_rows}")
    print(f"  ユニーク企業数: {len(valid_companies)}")
    
    if skipped_reasons:
        print(f"\n❌ スキップ理由別統計:")
        for reason, count in skipped_reasons.items():
            print(f"  {reason}: {count}行")
    
    return {
        "total_rows": len(df),
        "valid_rows": valid_rows,
        "skipped_rows": skipped_rows, 
        "unique_companies": len(valid_companies),
        "companies": valid_companies,
        "skipped_reasons": skipped_reasons
    }

def analyze_vectorstore():
    """ベクトルストアの内容分析"""
    print("\n" + "=" * 60)
    print("ベクトルストア内容分析")
    print("=" * 60)
    
    try:
        retriever = EnhancedRetriever()
        collection = retriever.vectorstore._collection
        
        # 総ドキュメント数
        total_count = collection.count()
        print(f"📊 総ドキュメント数: {total_count}")
        
        if total_count == 0:
            print("❌ ベクトルストアが空です")
            return {}
        
        # 全データ取得
        all_docs = collection.get(
            limit=total_count,
            include=["metadatas"]
        )
        
        # 企業別統計
        companies = set()
        row_ids = set()
        lead_statuses = {}
        
        if all_docs and all_docs.get("metadatas"):
            for meta in all_docs["metadatas"]:
                company = meta.get("company", "")
                row_id = meta.get("row_id", "")
                lead_status = meta.get("lead_status", "")
                
                if company:
                    companies.add(company)
                if row_id:
                    row_ids.add(row_id)
                if lead_status:
                    lead_statuses[lead_status] = lead_statuses.get(lead_status, 0) + 1
        
        print(f"📈 ベクトルストア統計:")
        print(f"  ユニーク企業数: {len(companies)}")
        print(f"  ユニーク行ID数: {len(row_ids)}")
        print(f"  行ID範囲: {min(row_ids) if row_ids else 'N/A'} - {max(row_ids) if row_ids else 'N/A'}")
        
        print(f"\n📊 リードステータス分布:")
        for status, count in sorted(lead_statuses.items()):
            print(f"  {status}: {count}件")
        
        return {
            "total_documents": total_count,
            "unique_companies": len(companies),
            "unique_rows": len(row_ids),
            "companies": companies,
            "row_ids": row_ids,
            "lead_statuses": lead_statuses
        }
        
    except Exception as e:
        print(f"❌ ベクトルストア分析エラー: {e}")
        import traceback
        traceback.print_exc()
        return {}

def test_daiou_package_search():
    """大王パッケージ株式会社の検索詳細テスト"""
    print("\n" + "=" * 60)
    print("大王パッケージ株式会社 検索詳細テスト")
    print("=" * 60)
    
    try:
        retriever = EnhancedRetriever()
        collection = retriever.vectorstore._collection
        
        # 1. ベクトルストアに「大王パッケージ」が保存されているか直接確認
        print("🔍 1. ベクトルストア直接確認:")
        all_docs = collection.get(
            limit=1000,
            include=["metadatas", "documents"]
        )
        
        daiou_found = False
        if all_docs and all_docs.get("metadatas"):
            for i, meta in enumerate(all_docs["metadatas"]):
                company = meta.get("company", "")
                if "大王" in company or "パッケージ" in company:
                    daiou_found = True
                    doc_content = all_docs["documents"][i] if i < len(all_docs["documents"]) else ""
                    print(f"  ✅ 発見: {company}")
                    print(f"     行ID: {meta.get('row_id', 'N/A')}")
                    print(f"     ステータス: {meta.get('lead_status', 'N/A')}")
                    print(f"     正規化名: {meta.get('company_name_norm', 'N/A')}")
                    print(f"     バリアント: {meta.get('company_name_variants', 'N/A')[:100]}...")
                    print(f"     内容: {doc_content[:100]}...")
        
        if not daiou_found:
            print("  ❌ ベクトルストアに「大王パッケージ」を含む企業が見つかりません")
            return
        
        # 2. 企業名正規化テスト
        print(f"\n🔧 2. 企業名正規化テスト:")
        test_names = [
            "大王パッケージ株式会社",
            "大王パッケージ",
            "ダイオウパッケージ株式会社",
            "ダイオウパッケージ"
        ]
        
        for name in test_names:
            normalized = normalize_name(name)
            variants = build_name_variants(name)
            print(f"  '{name}'")
            print(f"    正規化: '{normalized}'")
            print(f"    バリアント: {variants[:3]}...")
        
        # 3. 各種検索テスト
        print(f"\n🔍 3. 各種検索テスト:")
        search_queries = [
            "大王パッケージ株式会社",
            "大王パッケージ", 
            "ダイオウパッケージ",
            "大王",
            "パッケージ"
        ]
        
        for query in search_queries:
            print(f"\n  クエリ: '{query}'")
            
            # ハイブリッド検索
            try:
                results = retriever.hybrid_search(query, top_k=3)
                print(f"    ハイブリッド検索結果: {len(results)}件")
                for i, doc in enumerate(results[:2]):
                    company = doc.metadata.get("company", "N/A")
                    status = doc.metadata.get("lead_status", "N/A")
                    print(f"      {i+1}. 企業: {company}, ステータス: {status}")
            except Exception as e:
                print(f"    ❌ ハイブリッド検索エラー: {e}")
            
            # ベクトル検索のみ
            try:
                vector_results = retriever._vector_search(query, None, None, 3)
                print(f"    ベクトル検索結果: {len(vector_results)}件")
                for i, doc in enumerate(vector_results[:2]):
                    company = doc.metadata.get("company", "N/A")
                    print(f"      {i+1}. 企業: {company}")
            except Exception as e:
                print(f"    ❌ ベクトル検索エラー: {e}")
        
        # 4. RAGチャット機能テスト
        print(f"\n💬 4. RAGチャット機能テスト:")
        try:
            rag_service = RAGService()
            chat_queries = [
                "大王パッケージ株式会社について教えてください",
                "大王パッケージの情報はありますか？"
            ]
            
            for query in chat_queries:
                print(f"\n  質問: '{query}'")
                response = rag_service.chat(query)
                
                if response.get("status") == "success":
                    answer = response.get("answer", "")
                    sources = response.get("sources", [])
                    print(f"    ✅ 回答: {answer[:200]}...")
                    print(f"    📚 情報源数: {len(sources)}")
                    for source in sources[:2]:
                        print(f"       - {source.get('source', 'N/A')[:100]}...")
                else:
                    print(f"    ❌ エラー: {response.get('message', 'N/A')}")
                    
        except Exception as e:
            print(f"    ❌ RAGチャットテストエラー: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 大王パッケージ検索テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_results(excel_stats, vectorstore_stats):
    """ExcelとベクトルストアのデータS比較"""
    print("\n" + "=" * 60)
    print("データ比較分析")
    print("=" * 60)
    
    if not excel_stats or not vectorstore_stats:
        print("❌ 比較データが不足しています")
        return
    
    excel_companies = excel_stats.get("companies", set())
    vector_companies = vectorstore_stats.get("companies", set())
    
    print(f"📊 データ比較:")
    print(f"  Excel有効行数: {excel_stats.get('valid_rows', 0)}")
    print(f"  ベクトルストア行数: {vectorstore_stats.get('unique_rows', 0)}")
    print(f"  Excelユニーク企業数: {len(excel_companies)}")
    print(f"  ベクトルストアユニーク企業数: {len(vector_companies)}")
    
    # 一致率計算
    if excel_companies and vector_companies:
        common_companies = excel_companies & vector_companies
        missing_in_vector = excel_companies - vector_companies
        extra_in_vector = vector_companies - excel_companies
        
        match_rate = len(common_companies) / len(excel_companies) * 100
        
        print(f"\n✅ データ一致性:")
        print(f"  一致企業数: {len(common_companies)}")
        print(f"  一致率: {match_rate:.1f}%")
        
        if missing_in_vector:
            print(f"\n❌ ベクトルストアに未保存の企業 ({len(missing_in_vector)}社):")
            for company in sorted(list(missing_in_vector)[:10]):
                print(f"    - {company}")
            if len(missing_in_vector) > 10:
                print(f"    ... 他 {len(missing_in_vector) - 10}社")
        
        if extra_in_vector:
            print(f"\n⚠️  Excelにない企業がベクトルストアに存在 ({len(extra_in_vector)}社):")
            for company in sorted(list(extra_in_vector)[:5]):
                print(f"    - {company}")

def main():
    """メイン関数"""
    print("🔍 Excel-ベクトルストア包括検証ツール")
    print()
    
    # 1. Excelファイル分析
    df, header = analyze_excel_file()
    
    # 2. データ処理分析  
    excel_stats = analyze_data_processing(df)
    
    # 3. ベクトルストア分析
    vectorstore_stats = analyze_vectorstore()
    
    # 4. 比較分析
    compare_results(excel_stats, vectorstore_stats)
    
    # 5. 大王パッケージ検索詳細テスト
    test_daiou_package_search()
    
    print("\n" + "=" * 60)
    print("🎉 包括検証完了")
    print("=" * 60)

if __name__ == "__main__":
    main()
