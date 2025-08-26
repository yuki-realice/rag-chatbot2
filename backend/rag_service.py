import os
import tiktoken
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from config import Config

class RAGService:
    def __init__(self):
        self.config = Config()
        self.client = OpenAI(api_key=self.config.OPENAI_API_KEY)
        self.embeddings = OpenAIEmbeddings(
            model=self.config.RAG_EMBEDDING_MODEL,
            api_key=self.config.OPENAI_API_KEY
        )
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
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")
    
    def ingest_documents(self, file_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """ドキュメントをインデックス化"""
        try:
            if file_paths is None:
                # dataディレクトリ内の全ファイルを処理
                data_dir = Path(self.config.DATA_DIR)
                if not data_dir.exists():
                    return {"status": "error", "message": "Data directory not found"}
                
                file_paths = []
                for ext in self.config.ALLOWED_EXTENSIONS:
                    file_paths.extend(str(p) for p in data_dir.glob(f"*{ext}"))
            
            if not file_paths:
                return {"status": "warning", "message": "No documents found to ingest"}
            
            total_chunks = 0
            processed_files = []
            
            for file_path in file_paths:
                try:
                    content = self._load_document(file_path)
                    chunks = self.text_splitter.split_text(content)
                    
                    # メタデータを準備
                    metadata = [{"source": file_path, "chunk_id": i} for i in range(len(chunks))]
                    
                    # ベクトルストアに追加
                    self.vectorstore.add_texts(
                        texts=chunks,
                        metadatas=metadata
                    )
                    
                    total_chunks += len(chunks)
                    processed_files.append(file_path)
                    
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
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

