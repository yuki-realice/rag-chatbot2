import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic.v1 import SecretStr
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from config import Config
import pandas as pd
from gemini import GeminiEmbeddings
from retriever import EnhancedRetriever

class RAGService:
    def __init__(self):
        self.config = Config()
        
        if not self.config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY が設定されていません。.envファイルに設定してください。")
        
        print(f"INFO: Using Gemini embeddings: {self.config.GEMINI_EMBEDDING_MODEL}")
        self.embeddings = GeminiEmbeddings()
        
        print(f"INFO: Using Gemini for chat: {self.config.GEMINI_CHAT_MODEL}")
        self.llm = ChatGoogleGenerativeAI(
            model=self.config.GEMINI_CHAT_MODEL,
            google_api_key=SecretStr(self.config.GEMINI_API_KEY),
            temperature=0.05,
            top_p=0.9,
            client_options=None,
            transport=None,
            client=None
        )
        
        persist_dir = str(Path(self.config.CHROMA_STORE_DIR).resolve())
        self.vectorstore = Chroma(
            collection_name="leads",  # この行を追加
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.RAG_CHUNK_SIZE,
            chunk_overlap=self.config.RAG_CHUNK_OVERLAP,
            length_function=self._simple_len,
        )
        
        # EnhancedRetrieverを追加
        self.enhanced_retriever = EnhancedRetriever()
    
    def _simple_len(self, text: str) -> int:
        return len(text)
    
    def _load_document(self, file_path: str) -> str:
        path = Path(file_path)
        
        if path.suffix.lower() == '.pdf':
            loader = PyPDFLoader(str(path))
            pages = loader.load()
            return "\n".join([page.page_content for page in pages])
        elif path.suffix.lower() in ['.txt', '.md', '.markdown']:
            loader = TextLoader(str(path))
            document = loader.load()
            return document[0].page_content
        elif path.suffix.lower() in ['.csv', '.tsv']:
            delimiter = '\t' if path.suffix.lower() == '.tsv' else (self.config.SPREADSHEET_DELIMITER or ',')
            try:
                df = pd.read_csv(str(path), sep=delimiter, dtype=str, keep_default_na=False)
            except Exception as e:
                raise ValueError(f"Failed to read spreadsheet file {path.name}: {e}")
            text = self._dataframe_to_text(df)
            return text
        elif path.suffix.lower() in ['.xlsx', '.xls']:
            try:
                print(f"DEBUG: Reading Excel file with merged cell support: {path.name}")
                
                # 結合セル対応の読み込み
                df_raw = pd.read_excel(str(path), engine='openpyxl', dtype=str, header=None)
                df_raw = df_raw.fillna("")
                
                if len(df_raw) < 2:
                    raise ValueError(f"Insufficient data in Excel file: {path.name}")
                
                # ヘッダー処理
                header_row = df_raw.iloc[0].tolist()
                processed_header = []
                for i, cell_value in enumerate(header_row):
                    if cell_value and cell_value.strip():
                        processed_header.append(cell_value.strip())
                    else:
                        col_letter = chr(ord('A') + i)
                        processed_header.append(f"列{col_letter}")
                
                # データ部分の取得
                df = df_raw.iloc[1:].copy()
                df.columns = processed_header
                
                # 結合セルの処理（H-L列対応）
                df = self._process_merged_cells_in_rag(df)
                
                print(f"DEBUG: Excel read successful, shape: {df.shape}")
                print(f"DEBUG: データ行数（ヘッダー除く）: {len(df)}")
                print(f"DEBUG: Processed columns: {list(df.columns)}")
                
            except ImportError as e:
                raise ValueError(f"pandas or openpyxl not available: {e}")
            except Exception as e:
                raise ValueError(f"Failed to read Excel file {path.name}: {e}")
            text = self._dataframe_to_text(df)
            return text
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

    def _dataframe_to_text(self, df: pd.DataFrame) -> str:
        print(f"DEBUG: DataFrame shape: {df.shape}")
        print(f"DEBUG: DataFrame columns: {list(df.columns)}")
        
        columns_env = (self.config.SPREADSHEET_TEXT_COLUMNS or '').strip()
        if columns_env:
            requested_columns = [c.strip() for c in columns_env.split(',') if c.strip()]
            existing_columns = [c for c in requested_columns if c in df.columns]
            use_columns = existing_columns if len(existing_columns) > 0 else list(df.columns)
        else:
            use_columns = list(df.columns)
        
        print(f"DEBUG: Using columns: {use_columns}")

        df_selected = df[use_columns].astype(str)
        row_texts = []
        for idx, row in df_selected.iterrows():
            row_data = []
            for col in use_columns:
                value = row[col]
                str_value = str(value) if value is not None else ""
                # カラム名自体がデータとして含まれていないかチェック
                if str_value.strip() and str_value != 'nan' and str_value != col:
                    clean_value = str_value.strip()
                    row_data.append(f"{col}: {clean_value}")
            if row_data:
                row_text = " | ".join(row_data)
                row_texts.append(row_text)
                row_num = int(idx) + 2 if isinstance(idx, (int, float)) else 2
                print(f"DEBUG: 処理済み行 {row_num}: {row_text[:100]}...")  # Excel行番号で表示
        
        result_text = "\n".join(row_texts)
        print(f"DEBUG: Generated text length: {len(result_text)} characters")
        print(f"DEBUG: First 200 chars: {result_text[:200]}")
        return result_text
    
    def _process_merged_cells_in_rag(self, df: pd.DataFrame) -> pd.DataFrame:
        """RAGService用の結合セル処理"""
        for idx in df.index:
            row = df.loc[idx].copy()
            
            # H列からL列の結合セル対応（0ベースで7-11列）
            h_col_idx = 7  # H列
            l_col_idx = 11  # L列
            
            for i in range(1, len(row)):
                if not str(row.iloc[i]).strip() or str(row.iloc[i]) == 'nan':
                    if str(row.iloc[i-1]).strip() and str(row.iloc[i-1]) != 'nan':
                        # H-L列の範囲内での結合セル処理
                        if h_col_idx <= i-1 <= l_col_idx and h_col_idx <= i <= l_col_idx:
                            row.iloc[i] = row.iloc[i-1]
                            if idx < 5:  # 最初の5行のみログ出力
                                print(f"DEBUG: RAG結合セル処理 - 行{idx+2}, 列{i}: '{row.iloc[i-1]}' を継承")
            
            df.loc[idx] = row
        
        return df
    
    def ingest_documents(self, file_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            if file_paths is None:
                data_dir = Path(self.config.DATA_DIR)
                if not data_dir.exists():
                    return {"status": "error", "message": "Data directory not found"}

                file_paths = []
                for p in data_dir.iterdir():
                    if p.is_file() and p.suffix.lower() in self.config.ALLOWED_EXTENSIONS:
                        file_paths.append(str(p))
                        print(f"DEBUG: Found file for ingestion: {p.name} (extension: {p.suffix.lower()})")
                
                print(f"DEBUG: Total files found for ingestion: {len(file_paths)}")
            
            if not file_paths:
                return {"status": "warning", "message": "No documents found to ingest"}
            
            total_chunks = 0
            processed_files = []
            
            for file_path in file_paths:
                try:
                    print(f"DEBUG: Processing file: {file_path}")
                    content = self._load_document(file_path)
                    print(f"DEBUG: Loaded content length: {len(content)} characters")
                    
                    chunks = self.text_splitter.split_text(content)
                    print(f"DEBUG: Split into {len(chunks)} chunks")
                    
                    metadata = [{"source": file_path, "chunk_id": i} for i in range(len(chunks))]
                    
                    self.vectorstore.add_texts(
                        texts=chunks,
                        metadatas=metadata
                    )
                    
                    total_chunks += len(chunks)
                    processed_files.append(file_path)
                    print(f"DEBUG: Successfully processed {file_path} with {len(chunks)} chunks")
                    
                except Exception as e:
                    print(f"ERROR: Error processing {file_path}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            return {"status": "success", "message": f"Processed {len(processed_files)} files, {total_chunks} chunks", "processed_files": processed_files, "total_chunks": total_chunks}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def chat(self, message: str) -> Dict[str, Any]:
        try:
            candidate_k = max(self.config.RAG_CANDIDATE_K, self.config.RAG_TOP_K)
            if getattr(self.config, "RAG_USE_MMR", True):
                docs = self.enhanced_retriever.hybrid_search(message, top_k=self.config.RAG_TOP_K)
            else:
                docs = self.enhanced_retriever.hybrid_search(message, top_k=candidate_k)
            
            try:
                stats = self.vectorstore._collection.count()
                if not stats or int(stats) == 0:
                    ingest_result = self.ingest_documents()
                    candidate_k = max(self.config.RAG_CANDIDATE_K, self.config.RAG_TOP_K)
                    if getattr(self.config, "RAG_USE_MMR", True):
                        docs = self.enhanced_retriever.hybrid_search(message, top_k=self.config.RAG_TOP_K)
                    else:
                        docs = self.enhanced_retriever.hybrid_search(message, top_k=candidate_k)
                    if not docs:
                        return {"status": "warning", "message": "インデックスが空です。左のアップロード→インデックス再作成を実行してください。", "answer": "該当する情報は見つかりませんでした", "sources": []}
            except Exception:
                pass

            if not docs:
                try:
                    all_items = self.vectorstore._collection.get(include=["documents", "metadatas"], limit=100000)
                    all_docs = (all_items.get("documents") or [])
                    all_metas = (all_items.get("metadatas") or [])
                except Exception:
                    all_docs, all_metas = [], []

                def _keyword_score(text: str, query: str) -> int:
                    if not text or not query:
                        return 0
                    seps = ['\n', '\t', '、', '。', '，', ',', '．', '.', ' ', '　', ';', '：', ':']
                    terms = [query]
                    tmp = query
                    for s in seps:
                        tmp = tmp.replace(s, ' ')
                    terms += [t for t in tmp.split(' ') if t]
                    score = 0
                    for t in terms:
                        score += text.count(t)
                    return score

                scored = []
                for txt, md in zip(all_docs, all_metas):
                    s = _keyword_score(txt or "", message)
                    if s > 0:
                        scored.append((s, txt or "", md or {}))

                if scored:
                    scored.sort(key=lambda x: x[0], reverse=True)
                    top = scored[: self.config.RAG_TOP_K]
                    docs = [Document(page_content=txt, metadata=md) for _, txt, md in top]
                else:
                    return {"status": "warning", "message": "該当する情報は見つかりませんでした", "answer": "該当する情報は見つかりませんでした", "sources": []}
            
            processed_docs = self._process_search_results(docs, message)

            budget = max(256, getattr(self.config, "RAG_MAX_CONTEXT_TOKENS", 4000))
            selected = []
            used = 0
            for d in processed_docs:
                t = self._simple_len(d.page_content)
                if used + t > budget:
                    remaining = budget - used
                    if remaining > 100:
                        partial_content = d.page_content[:remaining] + "..."
                        selected.append(Document(page_content=partial_content, metadata=d.metadata))
                    break
                selected.append(d)
                used += t

            if not selected:
                selected = processed_docs[:1]

            context = self._build_structured_context(selected)
            system_instructions = getattr(self.config, "RAG_SYSTEM_INSTRUCTIONS", "")
            user_prompt = self._build_enhanced_prompt(message, context)
            prompt = f"{system_instructions}\n\n{user_prompt}"

            response = self.llm.invoke(prompt)
            answer = response.content
            
            sources = []
            for doc in selected:
                source = doc.metadata.get("source", "Unknown")
                # 短いcontentの場合は詳細情報を構築
                content = doc.page_content
                if "★row_id" in content and len(content.strip()) < 100:
                    # メタデータから詳細情報を構築
                    company = doc.metadata.get("company", "不明")
                    lead_status = doc.metadata.get("lead_status", "未設定")
                    phone = doc.metadata.get("代表電話", "")
                    direct_phone = doc.metadata.get("直通番号", "")
                    memo = doc.metadata.get("社内メモ", "")
                    call_log = doc.metadata.get("架電ログ", "")
                    
                    # 詳細情報を構築
                    details = [f"企業名: {company}", f"リードステータス: {lead_status}"]
                    if phone: details.append(f"代表電話: {phone}")
                    if direct_phone: details.append(f"直通番号: {direct_phone}")
                    if memo and memo != "nan": details.append(f"社内メモ: {memo}")
                    if call_log and call_log != "nan": details.append(f"架電ログ: {call_log}")
                    
                    content = " | ".join(details)

                sources.append({"source": source, "content": content[:300] + "..." if len(content) > 300 else content})
            
            return {"status": "success", "answer": answer, "sources": sources}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def prune_index_except(self, keep_filename_contains: str) -> Dict[str, Any]:
        try:
            results = self.vectorstore._collection.get(include=["metadatas", "ids"], limit=100000)
            metadatas = results.get("metadatas", []) or []
            ids = results.get("ids", []) or []

            delete_ids = []
            for item_id, md in zip(ids, metadatas):
                src = (md or {}).get("source", "")
                base = os.path.basename(str(src))
                if keep_filename_contains not in base:
                    delete_ids.append(item_id)

            if not delete_ids:
                return {"status": "success", "message": "削除対象はありません", "deleted": 0}

            self.vectorstore._collection.delete(ids=delete_ids)
            return {"status": "success", "message": f"{len(delete_ids)} 件を削除しました", "deleted": len(delete_ids)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _process_search_results(self, docs: List[Document], query: str) -> List[Document]:
        if not docs:
            return docs
        unique_docs = []
        seen_contents = set()
        for doc in docs:
            content_hash = hash(doc.page_content[:100])
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_docs.append(doc)
        def relevance_score(doc: Document) -> float:
            content = doc.page_content.lower()
            query_lower = query.lower()
            score = 0.0
            query_terms = query_lower.split()
            for term in query_terms:
                if term in content:
                    if "企業名:" in content and term in content.split("企業名:")[1].split("|")[0]:
                        score += 3.0
                    elif term in content:
                        score += 1.0
            return score
        unique_docs.sort(key=relevance_score, reverse=True)
        return unique_docs

    def _build_structured_context(self, docs: List[Document]) -> str:
        if not docs:
            return ""
        context_parts = []
        context_parts.append("【企業データベース情報】")
        for i, doc in enumerate(docs, 1):
            content = doc.page_content.strip()
            source = doc.metadata.get("source", "Unknown")
            structured_info = self._structure_company_info(content)
            context_parts.append(f"\n{i}. {structured_info}")
            context_parts.append(f"   [情報源: {source}]")
        return "\n".join(context_parts)

    def _structure_company_info(self, content: str) -> str:
        lines = content.split("|")
        structured = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if value and value != "nan":
                    structured[key] = value
        priority_fields = ["企業名", "代表電話", "直通番号", "従業員数", "リードステータス", "架電者", "架電ログ", "社内メモ"]
        result_parts = []
        for field in priority_fields:
            if field in structured:
                result_parts.append(f"{field}: {structured[field]}")
        for key, value in structured.items():
            if key not in priority_fields:
                result_parts.append(f"{key}: {value}")
        return " | ".join(result_parts)

    def _build_enhanced_prompt(self, query: str, context: str) -> str:
        return f"""【営業支援クエリ】
{query}

{context}

【指示】
上記の企業データベース情報を基に、営業担当者として最適な回答を提供してください。
- 質問に最も関連性の高い企業情報を抽出
- 営業活動に直接役立つ情報を優先的に提示
- 企業名、連絡先、営業状況を明確に整理
- 複数企業の情報がある場合は重要度順に並べる
- データに基づかない推測は避ける

【回答形式】
関連企業の情報を以下の形式で整理して回答してください：

■ 企業名: [企業名]
・基本情報: [従業員数、業界等]
・連絡先: [電話番号、担当者等]
・営業状況: [リードステータス、架電履歴等]
・特記事項: [社内メモ、注意点等]"""
