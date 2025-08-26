import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # === OpenAI設定 ===
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # === RAG設定 ===
    RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
    RAG_CHAT_MODEL = os.getenv("RAG_CHAT_MODEL", "gpt-4o-mini")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
    RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
    
    # === サーバー設定 ===
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
    
    # === ファイル設定 ===
    DATA_DIR = "./data/docs"        # ドキュメントの保存先
    CHROMA_STORE_DIR = "./chroma_store"
    
    # === 許可された拡張子 ===
    ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".markdown", ".csv", ".xlsx", ".tsv"}

    # === スプレッドシート取り込み設定 ===
    # 読み込む列を指定（例: "title,body,notes"）。空なら全列を読み込む。
    SPREADSHEET_TEXT_COLUMNS = os.getenv("SPREADSHEET_TEXT_COLUMNS", "")
    # 区切り文字（CSV=`,`、TSV=`\t`）
    SPREADSHEET_DELIMITER = os.getenv("SPREADSHEET_DELIMITER", ",")
