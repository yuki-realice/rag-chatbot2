import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# どのカレントディレクトリから実行しても .env を確実に読み込む
# 優先順: backend/.env → プロジェクトルート/.env → カレントディレクトリから探索
_backend_dir_path = Path(__file__).resolve().parent
_backend_env = _backend_dir_path / ".env"
_project_root = Path(__file__).resolve().parents[1]
_project_env = _project_root / ".env"

if _backend_env.exists():
    load_dotenv(_backend_env, override=False)
elif _project_env.exists():
    load_dotenv(_project_env, override=False)
else:
    load_dotenv(find_dotenv(usecwd=True), override=False)

# backend ディレクトリ（このファイルの場所）を基準に相対パスを絶対化するための基準パス
_backend_dir = Path(__file__).resolve().parent

class Config:
    # === Gemini API設定 ===
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-1.5-flash")
    GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "6"))
    RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1200"))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
    # 近傍探索の手法と再ランキング関連
    RAG_USE_MMR = os.getenv("RAG_USE_MMR", "true").lower() == "true"
    RAG_MMR_DIVERSITY = float(os.getenv("RAG_MMR_DIVERSITY", "0.3"))
    RAG_CANDIDATE_K = int(os.getenv("RAG_CANDIDATE_K", "20"))
    # 生成時のコンテキスト制約
    RAG_MAX_CONTEXT_TOKENS = int(os.getenv("RAG_MAX_CONTEXT_TOKENS", "4000"))
    RAG_SYSTEM_INSTRUCTIONS = os.getenv(
        "RAG_SYSTEM_INSTRUCTIONS",
        (
            """
あなたは営業活動を支援する専門のRAGアシスタントです。架電リストの企業データベースから最適な情報を抽出し、営業戦略の立案を支援してください。

【回答の方針】
1. 質問に直接関連する企業情報を優先的に抽出
2. 営業活動に有用な詳細情報（企業規模、業界、連絡先、アポ状況など）を構造化して提示
3. 複数企業に関する情報がある場合は、関連度の高い順に整理
4. 架電履歴やリードステータスがある場合は営業フェーズを明確化

【情報の構造化】
- 企業名: [正式企業名]
- 基本情報: 従業員数、業界、事業内容
- 連絡先: 代表電話、直通番号、担当者名
- 営業状況: リードステータス、架電履歴、アポ取得状況
- 特記事項: 社内メモ、注意点、営業機会

【回答の品質基準】
- 推測や憶測は避け、データに基づく情報のみ提供
- 情報が不完全な場合はその旨を明記
- 営業に直接役立つ実用的な情報を優先
- 企業名と情報源を必ず明記

コンテキストに関連情報がない場合のみ「該当する企業情報は見つかりませんでした」と回答してください。
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
