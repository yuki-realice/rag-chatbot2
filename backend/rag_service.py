import os
import tiktoken
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from openai import OpenAI
import openai as openai_module
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic.v1 import SecretStr
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from config import Config
import pandas as pd

class RAGService:
    def __init__(self):
        self.config = Config()
        self.client = OpenAI(api_key=self.config.OPENAI_API_KEY)

        # 埋め込みプロバイダを選択（APIキー未設定時は自動でHuggingFaceへフォールバック）
        provider = getattr(self.config, "RAG_EMBEDDING_PROVIDER", "openai").lower()
        if provider == "openai" and not self.config.OPENAI_API_KEY:
            print("WARN: OPENAI_API_KEY が未設定のため、HuggingFace埋め込みへ自動切替します")
            provider = "huggingface"

        if provider == "huggingface":
            self._use_hf_embeddings()
        else:
            print(f"INFO: Using OpenAI embeddings: {self.config.RAG_EMBEDDING_MODEL}")
            self.embeddings = OpenAIEmbeddings(
                model=self.config.RAG_EMBEDDING_MODEL,
                api_key=self.config.OPENAI_API_KEY
            )
        # チャットプロバイダの選択
        chat_provider = getattr(self.config, "RAG_CHAT_PROVIDER", "openai").lower()
        if chat_provider == "gemini":
            if not self.config.GEMINI_API_KEY:
                print("WARN: GEMINI_API_KEY が未設定です。OpenAIにフォールバックします。")
                self.llm = ChatOpenAI(
                    model=self.config.RAG_CHAT_MODEL,
                    api_key=self.config.OPENAI_API_KEY,
                    temperature=0.1
                )
            else:
                print(f"INFO: Using Gemini for chat: {self.config.GEMINI_MODEL}")
                self.llm = ChatGoogleGenerativeAI(
                    model=self.config.GEMINI_MODEL,
                    google_api_key=SecretStr(self.config.GEMINI_API_KEY),
                    temperature=0.1,
                    client=None,
                    client_options=None,
                    transport=None
                )
        else:
            self.llm = ChatOpenAI(
                model=self.config.RAG_CHAT_MODEL,
                api_key=self.config.OPENAI_API_KEY,
                temperature=0.1
            )
        
        # ChromaDB初期化
        self.vectorstore = Chroma(
            persist_directory=self.config.CHROMA_STORE_DIR,
            embedding_function=self.embeddings
        )
        
        # テキスト分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.RAG_CHUNK_SIZE,
            chunk_overlap=self.config.RAG_CHUNK_OVERLAP,
            length_function=self._tiktoken_len,
        )
    
    def _tiktoken_len(self, text: str) -> int:
        """tiktokenを使用してトークン数を計算"""
        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(text))
    
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

        # 文字列化（各セルを空白で連結、各行を改行で連結）
        # すべて文字列型に変換し、空文字を許容
        df_selected = df[use_columns].astype(str)
        row_texts = df_selected.apply(lambda row: ' '.join([v for v in row if isinstance(v, str) and len(v) > 0]).strip(), axis=1)
        # 空行は除外
        row_texts = [t for t in row_texts.tolist() if t]
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
                    
                    # ベクトルストアに追加（OpenAIの429等が出たらHFへフォールバックして再試行）
                    try:
                        self.vectorstore.add_texts(
                            texts=chunks,
                            metadatas=metadata
                        )
                    except Exception as add_err:
                        err_msg = str(add_err)
                        if (
                            isinstance(add_err, getattr(openai_module, "RateLimitError", Exception))
                            or "insufficient_quota" in err_msg
                            or "You exceeded your current quota" in err_msg
                        ):
                            print("WARN: OpenAI embeddings failed due to quota. Falling back to HuggingFace and retrying once...")
                            self._use_hf_embeddings(reinit_vectorstore=True)
                            self.vectorstore.add_texts(
                                texts=chunks,
                                metadatas=metadata
                            )
                        else:
                            raise
                    
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

    def _use_hf_embeddings(self, reinit_vectorstore: bool = False) -> None:
        """HuggingFace埋め込みへ切替し、必要に応じてChromaのembedding_functionも更新する"""
        print(f"INFO: Using HuggingFace embeddings: {self.config.HF_EMBEDDING_MODEL}")
        self.embeddings = HuggingFaceEmbeddings(model_name=self.config.HF_EMBEDDING_MODEL)
        if reinit_vectorstore:
            # 既存のベクトルストアを同じ永続ディレクトリで再初期化
            self.vectorstore = Chroma(
                persist_directory=self.config.CHROMA_STORE_DIR,
                embedding_function=self.embeddings
            )
    
    def chat(self, message: str) -> Dict[str, Any]:
        """チャット応答を生成"""
        try:
            # 類似検索
            docs = self.vectorstore.similarity_search(
                message,
                k=self.config.RAG_TOP_K
            )
            
            if not docs:
                return {
                    "status": "warning",
                    "message": "関連する文書が見つかりませんでした。",
                    "answer": "申し訳ございませんが、関連する文書が見つかりませんでした。",
                    "sources": []
                }
            
            # コンテキストを構築
            context = "\n\n".join([doc.page_content for doc in docs])
            
            # プロンプトを構築
            prompt = f"""以下の文書を参考にして、ユーザーの質問に答えてください。

参考文書:
{context}

ユーザーの質問: {message}

回答は日本語で、参考文書の内容に基づいて具体的に答えてください。
参考文書に含まれていない情報については、その旨を明記してください。"""

            # LLMで回答生成
            response = self.llm.invoke(prompt)
            answer = response.content
            
            # ソース情報を準備
            sources = []
            for doc in docs:
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

