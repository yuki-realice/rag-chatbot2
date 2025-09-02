"""
Excel ファイルから企業データを取り込み、RAG システム用にインデックス化するモジュール。
企業名（A列）とリードステータス（G列）を重視し、メタデータとして格納。
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import chromadb
from chromadb.config import Settings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pydantic.v1 import SecretStr
from datetime import datetime
from urllib.parse import urlparse
import httpx
import re
import json

from .config import Config
from .gemini import GeminiEmbeddings
from .utils.name_normalize import normalize_name, build_name_variants


class ExcelIngestor:
    """Excel ファイルを RAG システム用にインデックス化するクラス"""
    
    def __init__(self):
        self.config = Config()
        
        if not self.config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY が設定されていません。.envファイルに設定してください。")
        
        self.embeddings = GeminiEmbeddings()
        
        persist_dir = str(Path(self.config.CHROMA_STORE_DIR).resolve())
        self.vectorstore = Chroma(
            collection_name="leads",
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=80,
            length_function=len,
            separators=["\n\n", "\n", "。", "、", " ", ""]
        )
    
    def ingest_excel_file(
        self, 
        file_path: str, 
        sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            df, actual_sheet_name = self._load_excel_data(file_path, sheet_name)
            if df is None:
                return {"status": "error", "message": "Excel ファイルの読み込みに失敗しました"}
            processed_data = self._preprocess_data(df, actual_sheet_name)
            if not processed_data:
                return {"status": "warning", "message": "処理可能なデータが見つかりませんでした"}
            total_chunks = 0
            for data in processed_data:
                chunks = self._create_documents(data)
                total_chunks += len(chunks)
                self._delete_existing_document(data["excel_row"])
                if chunks:
                    texts = [chunk.page_content for chunk in chunks]
                    metadatas = [chunk.metadata for chunk in chunks]
                    ids = [f"{data['excel_row']}_cell_{data['column_index']}_chunk_{i}" for i in range(len(chunks))]
                    self.vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
                    print(f"DEBUG: ベクターストア追加 - 行{data['excel_row']}: {chunks[0].page_content[:50]}...")
            return {"status": "success", "message": f"処理完了: {len(processed_data)} レコード、{total_chunks} チャンク", "processed_records": len(processed_data), "total_chunks": total_chunks, "collection": "leads"}
        except Exception as e:
            return {"status": "error", "message": f"処理エラー: {str(e)}"}
    
    def _load_excel_data(self, file_path: str, sheet_name: Optional[str]) -> Tuple[Optional[pd.DataFrame], str]:
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"ERROR: ファイルが見つかりません: {file_path}")
                return None, ""
            
            # シート名の自動選択（Noneの場合は最初のシートを使用）
            if sheet_name is None:
                # 最初のシート名を取得
                xl_file = pd.ExcelFile(str(path), engine='openpyxl')
                sheet_name = xl_file.sheet_names[0]
                print(f"INFO: 自動選択されたシート: {sheet_name}")
            
            # 確実に文字列にする
            actual_sheet_name: str = sheet_name or ""
            
            # 結合セルに対応したExcel読み込み
            print(f"INFO: 結合セル対応でExcelファイル読み込み開始: {actual_sheet_name}")
            
            # まず生データで読み込み（ヘッダーなし）
            df_raw = pd.read_excel(str(path), sheet_name=actual_sheet_name, engine='openpyxl', dtype=str, header=None)
            
            # DataFrameかどうかチェック（複数シート読み込み時は辞書になる場合がある）
            if not isinstance(df_raw, pd.DataFrame):
                if isinstance(df_raw, dict):
                    # 辞書の場合は最初の値を取得
                    df_raw = list(df_raw.values())[0]
                    if not isinstance(df_raw, pd.DataFrame):
                        print(f"ERROR: 辞書から取得したデータがDataFrameではありません: {type(df_raw)}")
                        return None, actual_sheet_name
                else:
                    print(f"ERROR: 予期しない型のデータが返されました: {type(df_raw)}")
                    return None, actual_sheet_name
            
            # 型確認後のfillna実行
            df_raw = df_raw.fillna("")
            
            print(f"INFO: 生データ読み込み完了 - 形状: {df_raw.shape}")
            print(f"INFO: 最初の3行:")
            for i in range(min(3, len(df_raw))):
                print(f"  行{i+1}: {list(df_raw.iloc[i])}")
            
            # 1行目をヘッダーとして使用
            if len(df_raw) < 2:
                print(f"ERROR: データが不十分です（行数: {len(df_raw)}）")
                return None, actual_sheet_name
                
            # ヘッダー行を取得（1行目）
            header_row = df_raw.iloc[0].tolist()
            print(f"INFO: 元のヘッダー行: {header_row}")
            
            # H列からL列の結合セル問題に対応
            processed_header = self._process_merged_header(header_row)
            print(f"INFO: 処理後ヘッダー: {processed_header}")
            
            # データ部分を取得（2行目以降）
            if len(df_raw) < 2:
                print(f"WARNING: データ行がありません")
                return None, actual_sheet_name
                
            data_part = df_raw.iloc[1:].copy()
            data_part.columns = processed_header
            
            # 結合セルのデータ処理
            data_part = self._process_merged_cells_data(data_part)
            
            # 列名を標準化
            print(f"INFO: 列名標準化前の列名: {list(data_part.columns)}")
            data_part = data_part.rename(columns={
                "企業名": "company_name",
                "会社名": "company_name",
                "ステータス": "lead_status",
                "リードステータス": "lead_status"
            })
            print(f"INFO: 列名標準化後の列名: {list(data_part.columns)}")
            
            # デバッグ用出力
            print(f"DEBUG: 列名一覧:")
            print(data_part.columns.tolist())
            print(f"DEBUG: データの先頭5行:")
            print(data_part.head())
            
            print(f"INFO: Excel データ読み込み完了 - シート: {actual_sheet_name}, 形状: {data_part.shape}")
            print(f"INFO: 最終列名: {list(data_part.columns)}")
            print(f"INFO: データ行数（ヘッダー除く）: {len(data_part)}")
            
            # サンプルデータの表示
            if len(data_part) > 0:
                print(f"INFO: サンプルデータ（1行目）:")
                for col in data_part.columns:
                    value = data_part.iloc[0][col] if len(data_part) > 0 else ""
                    print(f"  {col}: '{value}'")
            
            return data_part, actual_sheet_name
        except Exception as e:
            print(f"ERROR: Excel ファイル読み込みエラー: {e}")
            import traceback
            traceback.print_exc()
            return None, ""
    
    def _preprocess_data(self, df: pd.DataFrame, sheet_name: str) -> List[Dict[str, Any]]:
        # row_id列を付与（Excelの表示行番号に一致）
        df = df.reset_index().assign(row_id=lambda d: d.index + 2)
        
        processed_data = []
        columns = list(df.columns)
        
        # 列名ベースでマッピング（標準化された列名を使用）
        company_col = None
        lead_status_col = None
        
        # company_name列を探す
        if "company_name" in columns:
            company_col = "company_name"
        else:
            # フォールバック: 最初の列を使用
            company_col = columns[0] if len(columns) > 0 else None
            print(f"WARNING: company_name列が見つからないため、最初の列({company_col})を使用")
        
        # lead_status列を探す
        if "lead_status" in columns:
            lead_status_col = "lead_status"
        else:
            # フォールバック: 6番目の列を使用（従来の動作）
            lead_status_col = columns[6] if len(columns) > 6 else None
            print(f"WARNING: lead_status列が見つからないため、6番目の列({lead_status_col})を使用")
        
        print(f"INFO: 処理対象列 - 企業名: {company_col}, リードステータス: {lead_status_col}")
        print(f"INFO: セル単位処理モードで実行中... (row_id列を付与)")
        
        for idx, row in df.iterrows():
            try:
                company = str(row[company_col]).strip() if company_col else ""
                # row_id を使用（Excel行番号と一致）
                excel_row_num = int(row['row_id'])
                    
                print(f"DEBUG: 行{excel_row_num}処理中 - 企業名列'{company_col}'の値: '{company}'")
                
                # URL検出（企業名が空のときの補完に利用）
                detected_url = self._find_first_url_in_row(row)
                url_domain = self._extract_domain(detected_url) if detected_url else ""
                inferred_company = ""
                company_alias = ""
                if not company or company.lower() in ['nan', 'none', ''] or company == company_col:
                    # URLから企業名を推定（失敗時はドメインのサブドメインをエイリアスに）
                    if detected_url:
                        inferred_company = self._infer_company_from_url(detected_url)
                        if not inferred_company and url_domain:
                            company_alias = self._alias_from_domain(url_domain)
                            inferred_company = company_alias
                    if inferred_company:
                        company = inferred_company
                        print(f"INFO: 行 {excel_row_num}: URLから企業名を推定 -> '{company}' (domain={url_domain})")
                    else:
                        print(f"INFO: スキップ - 行 {excel_row_num}: 企業名が無効でURLからも推定不可")
                        print(f"  行データサンプル: {dict(list(row.items())[:3])}")
                        continue
                    
                lead_status = str(row[lead_status_col]).strip() if lead_status_col else ""
                if lead_status.lower() in ['nan', 'none']:
                    lead_status = "未設定"
                    
                company = self._normalize_company_name(company)
                
                print(f"DEBUG: 行{excel_row_num} - 企業名: '{company}', ステータス: '{lead_status}'")
                
                # セル単位でのデータ処理
                cell_data_list = self._create_cell_data(
                    row=row,
                    columns=columns,
                    sheet_name=sheet_name,
                    excel_row_num=excel_row_num,
                    company=company,
                    lead_status=lead_status,
                    url=detected_url or "",
                    url_domain=url_domain,
                    company_alias=company_alias or self._alias_from_domain(url_domain) if url_domain else ""
                )
                
                if cell_data_list:
                    processed_data.extend(cell_data_list)
                    print(f"INFO: 処理済み - 行 {excel_row_num}: {company} ({lead_status}) - {len(cell_data_list)}セル")
                    
                    # セル詳細をデバッグ出力
                    for cell_data in cell_data_list[:3]:  # 最初の3セルのみ表示
                        print(f"  セル: {cell_data['column_name']} = '{cell_data['cell_value']}'")
                else:
                    print(f"WARNING: 行 {excel_row_num}: セルデータが作成されませんでした")
                    print(f"  企業名: '{company}', 行データ: {dict(list(row.items())[:5])}")
            except Exception as e:
                excel_row_num = int(row.get('row_id', 2) or 2)
                print(f"WARNING: 行 {excel_row_num} の処理をスキップ: {e}")
                continue
        print(f"INFO: 前処理完了 - {len(processed_data)} レコード処理")
        return processed_data
    
    def _normalize_company_name(self, company: str) -> str:
        """既存のコード互換性のため残すが、新しい正規化関数を呼び出す"""
        return normalize_name(company)
    
    def _create_cell_data(self, row: pd.Series, columns: List[str], sheet_name: str, excel_row_num: int, company: str, lead_status: str, url: str = "", url_domain: str = "", company_alias: str = "") -> List[Dict[str, Any]]:
        """各セルを個別のデータとして作成。URLやエイリアス情報も付与"""
        cell_data_list = []
        
        for col_idx, (col_name, value) in enumerate(zip(columns, row)):
            try:
                # 値の正規化
                str_value = str(value).strip()
                if not str_value or str_value.lower() in ['nan', 'none', ''] or str(col_name).startswith('Unnamed:'):
                    continue
                
                # セル固有のID作成
                cell_id = f"{sheet_name}_row_{excel_row_num}_col_{col_idx}_{col_name.replace(' ', '_')}"
                
                # セルデータ作成（詳細情報を含める）
                cell_content = f"【行{excel_row_num}】企業名: {company} | リードステータス: {lead_status} | {col_name}: {str_value}"
                
                cell_data = {
                    "row_id": cell_id,
                    "company": company,
                    "lead_status": lead_status,
                    "sheet": sheet_name,
                    "excel_row": excel_row_num,
                    "column_index": col_idx,
                    "column_name": col_name,
                    "cell_value": str_value,
                    "structured_data": cell_content,
                    "updated_at": datetime.now().isoformat(),
                    "url": url,
                    "url_domain": url_domain,
                    "company_alias": company_alias
                }
                
                cell_data_list.append(cell_data)
                print(f"DEBUG: セル作成 - {cell_id}: {cell_content}")
                
            except Exception as e:
                print(f"WARNING: セル処理エラー - 行 {excel_row_num}, 列 {col_idx}: {e}")
                continue
        
        return cell_data_list
    
    def _process_merged_header(self, header_row: List[str]) -> List[str]:
        """結合セルを考慮したヘッダー処理"""
        processed_header = []
        
        for i, cell_value in enumerate(header_row):
            if cell_value and cell_value.strip():
                # 値があるセル
                processed_header.append(cell_value.strip())
            else:
                # 空のセル（結合セルの可能性）
                col_letter = chr(ord('A') + i)  # A, B, C...
                processed_header.append(f"列{col_letter}")
        
        print(f"DEBUG: ヘッダー処理 - 元: {len(header_row)}列, 処理後: {len(processed_header)}列")
        return processed_header
    
    def _process_merged_cells_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """結合セルのデータを処理"""
        # 各行で結合セルの値を前方・後方に伝播
        for idx in df.index:
            row = df.loc[idx].copy()
            
            # 空の値を前の値で埋める（前方埋め）
            for i in range(1, len(row)):
                if not str(row.iloc[i]).strip() or str(row.iloc[i]) == 'nan':
                    if str(row.iloc[i-1]).strip() and str(row.iloc[i-1]) != 'nan':
                        # 前のセルに値があれば継承（ただし、明らかに異なる列タイプの場合は除く）
                        prev_col = df.columns[i-1]
                        curr_col = df.columns[i]
                        
                        # H列からL列の結合セル対応
                        h_col_idx = ord('H') - ord('A')  # 7
                        l_col_idx = ord('L') - ord('A')  # 11
                        
                        if h_col_idx <= i-1 <= l_col_idx and h_col_idx <= i <= l_col_idx:
                            row.iloc[i] = row.iloc[i-1]
                            print(f"DEBUG: 結合セル処理 - 行{idx+2}, 列{curr_col}: '{row.iloc[i-1]}' を継承")
            
            df.loc[idx] = row
        
        return df
    
    def _create_documents(self, data: Dict[str, Any]) -> List[Document]:
        content = data["structured_data"]
        
        # 企業名の正規化とバリアント生成
        raw_company_name = data["company"]
        normalized_company_name = normalize_name(raw_company_name)
        company_name_variants = build_name_variants(raw_company_name)
        
        base_metadata = {
            "company": data["company"], 
            "company_name_raw": raw_company_name,  # 生の企業名を保存
            "company_name_norm": normalized_company_name,  # 正規化された企業名
            "company_name_variants": "|".join(company_name_variants),  # 検索用バリアント（文字列として保存）
            "lead_status": data["lead_status"], 
            "row_id": data["excel_row"],  # Excel行番号をrow_idとして使用
            "cell_id": data["row_id"],     # セル固有IDは別フィールドに保存
            "sheet": data["sheet"], 
            "excel_row": data["excel_row"], 
            "column_index": data.get("column_index", -1),
            "column_name": data.get("column_name", ""),
            "cell_value": data.get("cell_value", ""),
            "url": data.get("url", ""),
            "url_domain": data.get("url_domain", ""),
            "company_alias": data.get("company_alias", ""),
            "updated_at": data["updated_at"], 
            "source": f"Excel:{data['sheet']}",
            "cell_position": f"行{data['excel_row']}列{data.get('column_name', '')}"
        }
        
        print(f"DEBUG: 企業名正規化 - 生: '{raw_company_name}' → 正規化: '{normalized_company_name}' → バリアント: {len(company_name_variants)}個")
        
        # セル単位では通常チャンク分割は不要だが、値が長い場合に対応
        if len(content) <= 600:
            return [Document(page_content=content, metadata=base_metadata)]
        
        chunks = self.text_splitter.split_text(content)
        documents = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_index"] = i
            chunk_metadata["total_chunks"] = len(chunks)
            documents.append(Document(page_content=chunk, metadata=chunk_metadata))
        return documents
    
    def _delete_existing_document(self, excel_row_num: int):
        try:
            collection = self.vectorstore._collection
            # Excel行番号でフィルタして削除
            results = collection.get(where={"row_id": excel_row_num})
            if results and results.get("ids"):
                collection.delete(ids=results["ids"])
                print(f"INFO: 既存データ削除 - row_id: {excel_row_num}")
        except Exception as e:
            print(f"WARNING: 既存データ削除エラー: {e}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        try:
            collection = self.vectorstore._collection
            count = collection.count()
            sample = collection.get(limit=5, include=["metadatas"])
            return {"status": "success", "collection_name": "leads", "total_documents": count, "sample_metadata": sample.get("metadatas", [])[:3] if sample else []}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _find_first_url_in_row(self, row: pd.Series) -> Optional[str]:
        """行内のセルから最初に見つかったURLを返す"""
        url_regex = re.compile(r"https?://[^\s]+", re.IGNORECASE)
        for value in row.values:
            try:
                text = str(value)
            except Exception:
                continue
            m = url_regex.search(text)
            if m:
                return m.group(0)
        return None

    def _extract_domain(self, url: Optional[str]) -> str:
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            host = parsed.netloc or ""
            if host.startswith("www."):
                host = host[4:]
            return host
        except Exception:
            return ""

    def _alias_from_domain(self, domain: str) -> str:
        if not domain:
            return ""
        # 先頭ラベルを採用（例: settsucarton.co.jp -> settsucarton）
        label = domain.split('.')[0]
        return label.replace('-', '').replace('_', '').strip()

    def _infer_company_from_url(self, url: str) -> str:
        """URLの<title>から企業名らしき文字列を推定（失敗時は空文字）"""
        try:
            with httpx.Client(timeout=5.0, follow_redirects=True) as client:
                r = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code >= 400:
                    return ""
                html = r.text or ""
        except Exception:
            return ""

        # <title>を抽出
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if not m:
            return ""
        title = m.group(1)
        # タイトル整形（区切りで先頭側を優先）
        for sep in ["｜", "|", "-", "‐", "–", "—", "ー", ":"]:
            if sep in title:
                title = title.split(sep)[0]
                break
        title = title.strip()
        if not title:
            return ""
        # 企業名っぽいトークン抽出
        candidate = title
        # 株式会社/有限会社/合同会社のいずれかが含まれていればその前後を採用
        corp_patterns = [r"([^\s]+株式会社)", r"([^\s]+有限会社)", r"([^\s]+合同会社)"]
        for p in corp_patterns:
            mm = re.search(p, candidate)
            if mm:
                return mm.group(1).strip()
        # それ以外は長めの日本語文字列を返す
        mm2 = re.search(r"([ぁ-んァ-ン一-龯]{3,})", candidate)
        if mm2:
            return mm2.group(1).strip()
        return ""