import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# どのカレントディレクトリから実行しても .env を確実に読み込む
# 優先してプロジェクトルートの .env を読み込み、見つからなければ親ディレクトリを辿る
_project_root = Path(__file__).resolve().parents[1]
_dotenv_path = _project_root / ".env"
if _dotenv_path.exists():
    load_dotenv(_dotenv_path, override=False)
else:
    load_dotenv(find_dotenv(usecwd=True), override=False)

class Config:
    # === OpenAI設定 ===
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # === RAG設定 ===
    # 埋め込みプロバイダ: openai | huggingface
    RAG_EMBEDDING_PROVIDER = os.getenv("RAG_EMBEDDING_PROVIDER", "openai")
    RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
    # Hugging Face の埋め込みモデル名（例: all-MiniLM-L6-v2）
    HF_EMBEDDING_MODEL = os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    # チャットプロバイダ: openai | gemini
    RAG_CHAT_PROVIDER = os.getenv("RAG_CHAT_PROVIDER", "openai")
    RAG_CHAT_MODEL = os.getenv("RAG_CHAT_MODEL", "gpt-4o-mini")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
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
