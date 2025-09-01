#!/usr/bin/env python3
"""
Excel ファイルのテキスト抽出テスト

このスクリプトは指定されたExcelファイルから正しくテキストが抽出されるかテストします。
"""

import pandas as pd
import sys
from pathlib import Path
import traceback

def test_excel_basic_read(file_path: str):
    """基本的なExcel読み込みテスト"""
    print("=" * 60)
    print("基本的なExcel読み込みテスト")
    print("=" * 60)
    
    try:
        path = Path(file_path)
        if not path.exists():
            print(f"❌ エラー: ファイルが見つかりません: {file_path}")
            return False
            
        print(f"📁 ファイルパス: {path}")
        print(f"📊 ファイルサイズ: {path.stat().st_size} bytes")
        
        # シート一覧を取得
        xl_file = pd.ExcelFile(str(path), engine='openpyxl')
        sheet_names = xl_file.sheet_names
        print(f"📋 シート一覧: {sheet_names}")
        
        # 最初のシートを読み込み
        sheet_name = sheet_names[0]
        print(f"\n🔍 '{sheet_name}' シートを読み込み中...")
        
        # 生データで読み込み（ヘッダーなし）
        df_raw = pd.read_excel(str(path), sheet_name=sheet_name, engine='openpyxl', dtype=str, header=None)
        df_raw = df_raw.fillna("")
        
        print(f"✅ 読み込み成功")
        print(f"📐 データサイズ: {df_raw.shape[0]} 行 × {df_raw.shape[1]} 列")
        
        # 最初の5行を表示
        print(f"\n📝 データの最初の5行:")
        for i in range(min(5, len(df_raw))):
            row_data = df_raw.iloc[i].tolist()
            print(f"  行{i+1}: {row_data}")
        
        return True, df_raw, sheet_name
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        traceback.print_exc()
        return False, None, None

def test_header_processing(df_raw, sheet_name):
    """ヘッダー処理テスト"""
    print("\n" + "=" * 60)
    print("ヘッダー処理テスト")
    print("=" * 60)
    
    try:
        if len(df_raw) < 2:
            print(f"❌ データが不十分です（行数: {len(df_raw)}）")
            return False
            
        # ヘッダー行を取得（1行目）
        header_row = df_raw.iloc[0].tolist()
        print(f"🏷️  元のヘッダー行: {header_row}")
        
        # ヘッダー処理（結合セル対応）
        processed_header = []
        for i, cell_value in enumerate(header_row):
            if cell_value and cell_value.strip():
                processed_header.append(cell_value.strip())
            else:
                col_letter = chr(ord('A') + i)
                processed_header.append(f"列{col_letter}")
        
        print(f"🔧 処理後ヘッダー: {processed_header}")
        
        # データ部分を取得（2行目以降）
        data_part = df_raw.iloc[1:].copy()
        data_part.columns = processed_header
        
        # 列名を標準化
        print(f"📊 列名標準化前: {list(data_part.columns)}")
        data_part = data_part.rename(columns={
            "企業名": "company_name",
            "会社名": "company_name",
            "ステータス": "lead_status",
            "リードステータス": "lead_status"
        })
        print(f"📊 列名標準化後: {list(data_part.columns)}")
        
        return True, data_part
        
    except Exception as e:
        print(f"❌ ヘッダー処理エラー: {e}")
        traceback.print_exc()
        return False, None

def test_data_extraction(df):
    """データ抽出テスト"""
    print("\n" + "=" * 60)
    print("データ抽出テスト")
    print("=" * 60)
    
    try:
        print(f"📊 処理対象データ: {len(df)} 行")
        
        # 企業名列とリードステータス列を探す
        columns = list(df.columns)
        company_col = None
        lead_status_col = None
        
        if "company_name" in columns:
            company_col = "company_name"
        else:
            company_col = columns[0] if len(columns) > 0 else None
            print(f"⚠️  company_name列が見つからないため、最初の列({company_col})を使用")
        
        if "lead_status" in columns:
            lead_status_col = "lead_status"
        else:
            lead_status_col = columns[6] if len(columns) > 6 else None
            print(f"⚠️  lead_status列が見つからないため、6番目の列({lead_status_col})を使用")
        
        print(f"🏢 企業名列: {company_col}")
        print(f"📊 リードステータス列: {lead_status_col}")
        
        # 最初の10行のデータを表示
        print(f"\n📝 抽出データサンプル（最初の10行）:")
        extracted_count = 0
        
        for idx, row in df.head(10).iterrows():
            try:
                company = str(row[company_col]).strip() if company_col else ""
                lead_status = str(row[lead_status_col]).strip() if lead_status_col else ""
                
                if company and company.lower() not in ['nan', 'none', '']:
                    extracted_count += 1
                    print(f"  行{idx+2}: 企業名='{company}', ステータス='{lead_status}'")
                    
                    # セルの詳細情報も表示
                    row_dict = row.to_dict()
                    non_empty_cells = {k: v for k, v in row_dict.items() if str(v).strip() and str(v) != 'nan'}
                    print(f"    全セルデータ: {list(non_empty_cells.keys())}")
                    
            except Exception as e:
                print(f"    ❌ 行{idx+2}の処理エラー: {e}")
                continue
        
        print(f"\n✅ 有効なデータ抽出: {extracted_count}/{min(10, len(df))} 行")
        
        return True
        
    except Exception as e:
        print(f"❌ データ抽出エラー: {e}")
        traceback.print_exc()
        return False

def main():
    """メイン関数"""
    # テスト対象ファイル
    excel_file = "/Users/yuki/Desktop/rag chatbot2/backend/data/docs/rag用_架電リスト.xlsx"
    
    print("🧪 Excel ファイル テキスト抽出テスト")
    print(f"📁 対象ファイル: {excel_file}")
    print()
    
    # 1. 基本読み込みテスト
    success, df_raw, sheet_name = test_excel_basic_read(excel_file)
    if not success:
        print("❌ 基本読み込みテストが失敗しました")
        return
    
    # 2. ヘッダー処理テスト
    success, df_processed = test_header_processing(df_raw, sheet_name)
    if not success:
        print("❌ ヘッダー処理テストが失敗しました")
        return
    
    # 3. データ抽出テスト
    success = test_data_extraction(df_processed)
    if not success:
        print("❌ データ抽出テストが失敗しました")
        return
        
    print("\n" + "=" * 60)
    print("🎉 すべてのテストが正常に完了しました！")
    print("=" * 60)

if __name__ == "__main__":
    main()
