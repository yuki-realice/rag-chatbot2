import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from pydantic.v1 import SecretStr
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from config import Config
import pandas as pd

class RAGService:
    def __init__(self):
        self.config = Config()
        
        # Gemini APIキーチェック
        if not self.config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY が設定されていません。.envファイルに設定してください。")
        
        # Gemini埋め込みモデルの初期化
        print(f"INFO: Using Gemini embeddings: {self.config.GEMINI_EMBEDDING_MODEL}")
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=self.config.GEMINI_EMBEDDING_MODEL,
            google_api_key=SecretStr(self.config.GEMINI_API_KEY),
            task_type=None,
            client_options=None,
            transport=None
        )
        
        # Geminiチャットモデルの初期化
        print(f"INFO: Using Gemini for chat: {self.config.GEMINI_CHAT_MODEL}")
        self.llm = ChatGoogleGenerativeAI(
            model=self.config.GEMINI_CHAT_MODEL,
            google_api_key=SecretStr(self.config.GEMINI_API_KEY),
            temperature=0.1,
            client_options=None,
            transport=None,
            client=None
        )
        
        # ChromaDB初期化（絶対パスを使用）
        persist_dir = str(Path(self.config.CHROMA_STORE_DIR).resolve())
        self.vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )
        
        # テキスト分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.RAG_CHUNK_SIZE,
            chunk_overlap=self.config.RAG_CHUNK_OVERLAP,
            length_function=self._simple_len,
        )
    
    def _simple_len(self, text: str) -> int:
        """シンプルな文字数ベースのトークン数計算（Gemini用）"""
        # 日本語の場合、おおよそ1文字=1トークンとして計算
        return len(text)
    
    def _load_document(self, file_path: str) -> str:
        """ドキュメントを読み込み"""
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
            # CSV/TSV の読み込み
            delimiter = '\t' if path.suffix.lower() == '.tsv' else (self.config.SPREADSHEET_DELIMITER or ',')
            try:
                df = pd.read_csv(str(path), sep=delimiter, dtype=str, keep_default_na=False)
            except Exception as e:
                raise ValueError(f"Failed to read spreadsheet file {path.name}: {e}")
            text = self._dataframe_to_text(df)
            return text
        elif path.suffix.lower() in ['.xlsx', '.xls']:
            # Excel の読み込み（openpyxl エンジン）
            try:
                print(f"DEBUG: Reading Excel file: {path.name}")
                df = pd.read_excel(str(path), engine='openpyxl', dtype=str)
                print(f"DEBUG: Excel read successful, shape: {df.shape}")
                # NaN を空文字へ
                df = df.fillna("")
            except ImportError as e:
                raise ValueError(f"pandas or openpyxl not available: {e}")
            except Exception as e:
                raise ValueError(f"Failed to read Excel file {path.name}: {e}")
            text = self._dataframe_to_text(df)
            return text
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

    def _dataframe_to_text(self, df: pd.DataFrame) -> str:
        """DataFrame を RAG 用のプレーンテキストに変換する。
        SPREADSHEET_TEXT_COLUMNS が設定されていれば、指定列のみを結合して行テキスト化。
        未設定なら全列を対象にする。
        """
        print(f"DEBUG: DataFrame shape: {df.shape}")
        print(f"DEBUG: DataFrame columns: {list(df.columns)}")
        
        # 列選択
        columns_env = (self.config.SPREADSHEET_TEXT_COLUMNS or '').strip()
        if columns_env:
            requested_columns = [c.strip() for c in columns_env.split(',') if c.strip()]
            existing_columns = [c for c in requested_columns if c in df.columns]
            # 存在しない列は無視（全て存在しなければ全列）
            use_columns = existing_columns if len(existing_columns) > 0 else list(df.columns)
        else:
            use_columns = list(df.columns)
        
        print(f"DEBUG: Using columns: {use_columns}")

        # 文字列化（構造化されたフォーマットで各行を変換）
        df_selected = df[use_columns].astype(str)
        row_texts = []
        for _, row in df_selected.iterrows():
            # 構造化されたテキスト形式で企業情報を作成
            row_data = []
            for col in use_columns:
                value = row[col]
                # 安全な文字列変換と処理
                str_value = str(value) if value is not None else ""
                if str_value.strip() and str_value != 'nan':
                    clean_value = str_value.strip()
                    row_data.append(f"{col}: {clean_value}")
            
            if row_data:  # 空でない行のみ追加
                row_text = " | ".join(row_data)
                row_texts.append(row_text)
        
        result_text = "\n".join(row_texts)
        print(f"DEBUG: Generated text length: {len(result_text)} characters")
        print(f"DEBUG: First 200 chars: {result_text[:200]}")
        return result_text
    
    def ingest_documents(self, file_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """ドキュメントをインデックス化"""
        try:
            if file_paths is None:
                # dataディレクトリ内の全ファイルを処理（拡張子は大文字小文字を無視）
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
                    
                    # メタデータを準備
                    metadata = [{"source": file_path, "chunk_id": i} for i in range(len(chunks))]
                    
                    # ベクトルストアに追加
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
            
            return {
                "status": "success",
                "message": f"Processed {len(processed_files)} files, {total_chunks} chunks",
                "processed_files": processed_files,
                "total_chunks": total_chunks
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}


    def chat(self, message: str) -> Dict[str, Any]:
        """チャット応答を生成"""
        try:
            # まず候補を広めに取得（MMR対応 or 通常検索）
            candidate_k = max(self.config.RAG_CANDIDATE_K, self.config.RAG_TOP_K)
            if getattr(self.config, "RAG_USE_MMR", True):
                # MMR（最大限の関連性と多様性）
                docs = self.vectorstore.max_marginal_relevance_search(
                    message,
                    k=self.config.RAG_TOP_K,
                    fetch_k=candidate_k,
                    lambda_mult=self.config.RAG_MMR_DIVERSITY,
                )
            else:
                docs = self.vectorstore.similarity_search(
                    message,
                    k=candidate_k,
                )
            
            # Chromaコレクションが空（ドキュメント未インデックス化）の場合に備えて早期リターン
            try:
                stats = self.vectorstore._collection.count()
                if not stats or int(stats) == 0:
                    # 自動インデックス化を試行
                    ingest_result = self.ingest_documents()
                    # 再度検索を試みる
                    candidate_k = max(self.config.RAG_CANDIDATE_K, self.config.RAG_TOP_K)
                    if getattr(self.config, "RAG_USE_MMR", True):
                        docs = self.vectorstore.max_marginal_relevance_search(
                            message,
                            k=self.config.RAG_TOP_K,
                            fetch_k=candidate_k,
                            lambda_mult=self.config.RAG_MMR_DIVERSITY,
                        )
                    else:
                        docs = self.vectorstore.similarity_search(
                            message,
                            k=candidate_k,
                        )
                    if not docs:
                        return {
                            "status": "warning",
                            "message": "インデックスが空です。左のアップロード→インデックス再作成を実行してください。",
                            "answer": "該当する情報は見つかりませんでした",
                            "sources": []
                        }
            except Exception:
                # 内部API形状が変わっている場合は無視して通常フロー
                pass

            if not docs:
                # ベクトル検索で0件の場合、簡易キーワード検索でフォールバック
                try:
                    all_items = self.vectorstore._collection.get(include=["documents", "metadatas"], limit=100000)
                    all_docs = (all_items.get("documents") or [])
                    all_metas = (all_items.get("metadatas") or [])
                except Exception:
                    all_docs, all_metas = [], []

                def _keyword_score(text: str, query: str) -> int:
                    if not text or not query:
                        return 0
                    # 日本語向けに、句読点・スペースで簡易分割し、部分一致の総数でスコア化
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
                    return {
                        "status": "warning",
                        "message": "該当する情報は見つかりませんでした",
                        "answer": "該当する情報は見つかりませんでした",
                        "sources": []
                    }
            
            # 検索結果をそのまま使用（再ランキングはGeminiに任せる）
            reranked_docs = docs[: self.config.RAG_TOP_K]

            # トークン上限に合わせてコンテキストを整形
            budget = max(256, getattr(self.config, "RAG_MAX_CONTEXT_TOKENS", 2000))
            selected = []
            used = 0
            for d in reranked_docs:
                t = self._simple_len(d.page_content)
                if used + t > budget:
                    continue
                selected.append(d)
                used += t

            if not selected:
                selected = reranked_docs[:1]

            context = "\n\n".join([doc.page_content for doc in selected])
            
            # プロンプトを構築（SYSTEM_PROMPT + USER_PROMPT テンプレート）
            system_instructions = getattr(self.config, "RAG_SYSTEM_INSTRUCTIONS", "")
            user_prompt = (
                f"質問: {message}\n\n"
                f"コンテキスト:\n{context}\n\n"
                "上記コンテキストに基づいて、質問に答えてください。"
            )
            prompt = f"{system_instructions}\n\n{user_prompt}"

            # LLMで回答生成
            response = self.llm.invoke(prompt)
            answer = response.content
            
            # ソース情報を準備
            sources = []
            for doc in selected:
                source = doc.metadata.get("source", "Unknown")
                sources.append({
                    "source": source,
                    "content": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                })
            
            return {
                "status": "success",
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}


    def prune_index_except(self, keep_filename_contains: str) -> Dict[str, Any]:
        """メタデータのsourceに含まれるファイルパスのうち、特定の文字列を含まないものを削除
        keep_filename_contains に一致するもののみ残し、それ以外を削除する。
        """
        try:
            # Chromaのメタデータクエリを利用して、対象外ドキュメントのidsを取得
            # まず全件から候補を取得（Chromaは直接NOT検索が弱いので、段階的に絞る）
            results = self.vectorstore._collection.get(include=["metadatas", "ids"], limit=100000)
            metadatas = results.get("metadatas", []) or []
            ids = results.get("ids", []) or []

            delete_ids = []
            for item_id, md in zip(ids, metadatas):
                src = (md or {}).get("source", "")
                # ファイル名ベースで判定
                base = os.path.basename(str(src))
                if keep_filename_contains not in base:
                    delete_ids.append(item_id)

            if not delete_ids:
                return {"status": "success", "message": "削除対象はありません", "deleted": 0}

            # 実削除
            self.vectorstore._collection.delete(ids=delete_ids)
            return {"status": "success", "message": f"{len(delete_ids)} 件を削除しました", "deleted": len(delete_ids)}
        except Exception as e:
            return {"status": "error", "message": str(e)}
