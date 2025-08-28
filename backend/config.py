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

# backend ディレクトリ（このファイルの場所）を基準に相対パスを絶対化するための基準パス
_backend_dir = Path(__file__).resolve().parent

class Config:
    # === Gemini API設定 ===
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash")
    GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/embedding-001")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
    RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
    # 近傍探索の手法と再ランキング関連
    RAG_USE_MMR = os.getenv("RAG_USE_MMR", "true").lower() == "true"
    RAG_MMR_DIVERSITY = float(os.getenv("RAG_MMR_DIVERSITY", "0.5"))
    RAG_CANDIDATE_K = int(os.getenv("RAG_CANDIDATE_K", "12"))
    # 生成時のコンテキスト制約
    RAG_MAX_CONTEXT_TOKENS = int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "2000"))
    RAG_SYSTEM_INSTRUCTIONS = os.getenv(
        "RAG_SYSTEM_INSTRUCTIONS",
        (
            """
あなたは営業支援RAGアシスタントです。架電リストの企業情報を基に回答してください。
- 与えられたコンテキストから関連する企業情報を抽出して回答
- 企業名、電話番号、担当者、架電履歴、アポ状況などを整理して提示
- コンテキストに部分的な情報でも含まれていれば、それを活用して回答
- 情報源として企業名や日付を明記
- 完全に関連がない場合のみ「該当情報なし」と回答
"""
        ),
    )
    
    # === サーバー設定 ===
    BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
    
    # === ファイル設定 ===
    # 相対パスが与えられた場合でも、常に backend ディレクトリ基準で絶対パス化する
    DATA_DIR = os.getenv("DATA_DIR", str((_backend_dir / "data/docs").resolve()))
    CHROMA_STORE_DIR = os.getenv("CHROMA_STORE_DIR", str((_backend_dir / "chroma_store").resolve()))
    
    # === 許可された拡張子 ===
    ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".markdown", ".csv", ".xlsx", ".tsv"}

    # === スプレッドシート取り込み設定 ===
    # 読み込む列を指定（例: "title,body,notes"）。空なら全列を読み込む。
    SPREADSHEET_TEXT_COLUMNS = os.getenv("SPREADSHEET_TEXT_COLUMNS", "企業名,代表電話,直通番号,社内メモ,従業員数,架電者,リードステータス,架電ログ")
    # 区切り文字（CSV=`,`、TSV=`\t`）
    SPREADSHEET_DELIMITER = os.getenv("SPREADSHEET_DELIMITER", ",")
