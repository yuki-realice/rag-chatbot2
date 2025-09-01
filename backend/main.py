from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, cast, Dict, Any
import os
import shutil
from pathlib import Path

from .config import Config
from .rag_service import RAGService
from .ingest_excel import ExcelIngestor
from .retriever import EnhancedRetriever
import time
import random
import re
import pandas as pd

app = FastAPI(title="RAG Chatbot API", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 設定とサービスの初期化
config = Config()
rag_service = None
excel_ingestor = None
enhanced_retriever = None

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の初期化処理"""
    global rag_service, excel_ingestor, enhanced_retriever
    try:
        rag_service = RAGService()
        excel_ingestor = ExcelIngestor()
        enhanced_retriever = EnhancedRetriever()
        print("INFO: All services initialized successfully")
    except Exception as e:
        print(f"ERROR: Failed to initialize services: {e}")
        raise

# データディレクトリの作成
data_dir = Path(config.DATA_DIR)
data_dir.mkdir(exist_ok=True)

# Pydanticモデル
class ChatRequest(BaseModel):
    message: str

class CompanyInfo(BaseModel):
    company: str
    lead_status: str
    source_id: str

class AskResponse(BaseModel):
    status: str
    answer: Optional[str] = None
    items: Optional[List[CompanyInfo]] = None
    sources: Optional[List[str]] = None
    message: Optional[str] = None
    reason: Optional[str] = None
    meta: Optional[dict] = None

class ChatResponse(BaseModel):
    status: str
    answer: Optional[str] = None
    sources: Optional[List[dict]] = None
    message: Optional[str] = None

class IngestResponse(BaseModel):
    status: str
    message: str
    processed_files: Optional[List[str]] = None
    total_chunks: Optional[int] = None

class UploadResponse(BaseModel):
    status: str
    message: str
    filename: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    row_id: Optional[int] = None

class CompanyByRowResponse(BaseModel):
    status: str
    company_data: Optional[Dict[str, Any]] = None
    row_id: Optional[int] = None
    message: Optional[str] = None

def parse_row_from_cell(cell: str) -> int:
    """
    セル参照（例：A2, B10）から行番号を抽出
    Args:
        cell: セル参照文字列（例："A2", "B10"）
    Returns:
        int: 行番号
    Raises:
        ValueError: 不正なセル参照の場合
    """
    if not cell:
        raise ValueError("セル参照が空です")
    
    # 文字と数字を分離（例：A2 -> ['A', '2']）
    match = re.match(r'^([A-Z]+)(\d+)$', cell.upper())
    if not match:
        raise ValueError(f"不正なセル参照形式: {cell}")
    
    col_letters, row_str = match.groups()
    try:
        row_num = int(row_str)
        if row_num < 1:
            raise ValueError(f"行番号は1以上である必要があります: {row_num}")
        return row_num
    except ValueError as e:
        raise ValueError(f"行番号の解析に失敗しました: {row_str}") from e

@app.get("/")
async def root():
    return {"message": "RAG Chatbot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Gemini ヘルスチェック
@app.get("/gemini/health")
async def gemini_health():
    return {"ok": bool(os.getenv("GEMINI_API_KEY"))}

@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """ファイルをアップロードしてdataディレクトリに保存"""
    try:
        if file.filename is None:
            raise HTTPException(status_code=400, detail="Filename is required")
        filename = cast(str, file.filename)

        # 本文読み取りと空チェック
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")

        # ファイル拡張子のチェック
        file_extension = Path(filename).suffix.lower()
        if file_extension not in config.ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {config.ALLOWED_EXTENSIONS}")

        # 保存
        file_path = data_dir / filename
        with open(file_path, "wb") as f:
            f.write(content)

        print(f"INFO: POST /upload -> 200 (saved: {filename})")
        return UploadResponse(status="success", message=f"File {filename} uploaded successfully", filename=filename)

    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: POST /upload -> 500 ({e})")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest", response_model=IngestResponse)
async def ingest_documents():
    try:
        if rag_service is None:
            return JSONResponse(status_code=500, content={"error": "RAG service not initialized", "detail": "Service initialization failed"})
        result = rag_service.ingest_documents()
        print(f"INFO: POST /ingest -> 200")
        return IngestResponse(**result)
    except Exception as e:
        print(f"ERROR: POST /ingest -> 500 ({e})")
        return JSONResponse(status_code=500, content={"error": "Ingestion failed", "detail": str(e)})

@app.post("/search")
async def search(req: SearchRequest):
    """埋め込み検索 + LLM フォールバック"""
    try:
        q = (req.query or "").strip()
        if not q:
            return JSONResponse(status_code=400, content={"error": "query is required"})

        if enhanced_retriever is None:
            return JSONResponse(status_code=500, content={"error": "retriever not initialized"})

        # 1) 類似度検索（緩めの閾値、上位3件）
        docs = enhanced_retriever.hybrid_search(q, row_id_filter=req.row_id, top_k=5, score_threshold=0.60)
        top_docs = docs[:3]

        # 2) レスポンス形成
        results = [
            {
                "content": d.page_content,
                "metadata": d.metadata,
            }
            for d in top_docs
        ]

        # 3) LLMへのプロンプト構築
        from langchain_google_genai import ChatGoogleGenerativeAI
        from pydantic.v1 import SecretStr
        
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY が設定されていません")
            
        llm = ChatGoogleGenerativeAI(
            model=config.GEMINI_CHAT_MODEL,
            google_api_key=SecretStr(config.GEMINI_API_KEY),
            temperature=0.2,
            top_p=0.9,
            client_options=None,
            transport=None,
            client=None,
        )

        if results:
            context = "\n\n".join([r["content"] for r in results])
            prompt = (
                "あなたは営業支援AIです。以下の社内ドキュメントに基づいて、ユーザーの質問に日本語で簡潔に回答してください。"\
                "\n\n【質問】\n" + q + "\n\n【社内ドキュメント】\n" + context + "\n\n【要件】\n- 根拠となる情報のみを使用\n- 不明な点は不明と述べる\n- 箇条書きで要点を整理"
            )
            answer = llm.invoke(prompt).content
            print("INFO: POST /search -> 200 (with results)")
            return {"status": "ok", "results": results, "answer": answer}
        else:
            # 4) フォールバック（一般知識で補足回答）
            prompt = (
                "アップロードされたドキュメントから該当情報は見つかりませんでした。"\
                "以下の質問に対して、一般知識の範囲で日本語で簡潔に補足回答してください。"\
                "\n\n【質問】\n" + q + "\n\n【要件】\n- 具体的かつ実用的な提案\n- 根拠が弱い場合は前提条件を明示"
            )
            answer = llm.invoke(prompt).content
            print("INFO: POST /search -> 200 (fallback)")
            return {"status": "ok", "results": [], "answer": answer, "fallback": True}

    except Exception as e:
        print(f"ERROR: POST /search -> 500 ({e})")
        return JSONResponse(status_code=500, content={"error": "Search failed", "detail": str(e)})

@app.post("/api/ask", response_model=AskResponse)
async def ask(request: ChatRequest):
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        if enhanced_retriever is None:
            return JSONResponse(status_code=500, content={"error": "Enhanced retriever not initialized", "detail": "Service initialization failed"})
        result = await enhanced_chat_with_retry(request.message)
        print("INFO: POST /api/ask -> 200")
        return AskResponse(**result)
    except Exception as e:
        print(f"ERROR: POST /api/ask -> 500 ({e})")
        return JSONResponse(status_code=500, content={"error": "Ask failed", "detail": str(e)})

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        if rag_service is None:
            return JSONResponse(status_code=500, content={"error": "RAG service not initialized", "detail": "Service initialization failed"})
        result = rag_service.chat(request.message)
        print("INFO: POST /chat -> 200")
        return ChatResponse(**result)
    except Exception as e:
        print(f"ERROR: POST /chat -> 500 ({e})")
        return JSONResponse(status_code=500, content={"error": "Chat failed", "detail": str(e)})

class PruneRequest(BaseModel):
    keep_contains: str

class PruneResponse(BaseModel):
    status: str
    message: str
    deleted: Optional[int] = None

@app.post("/prune-index", response_model=PruneResponse)
async def prune_index(req: PruneRequest):
    try:
        if not req.keep_contains:
            raise HTTPException(status_code=400, detail="keep_contains is required")
        if rag_service is None:
            return JSONResponse(status_code=500, content={"error": "RAG service not initialized", "detail": "Service initialization failed"})
        result = rag_service.prune_index_except(req.keep_contains)
        print("INFO: POST /prune-index -> 200")
        return PruneResponse(**result)
    except Exception as e:
        print(f"ERROR: POST /prune-index -> 500 ({e})")
        return JSONResponse(status_code=500, content={"error": "Prune operation failed", "detail": str(e)})

async def enhanced_chat_with_retry(message: str, max_retries: int = 3) -> Dict[str, Any]:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from pydantic.v1 import SecretStr
    
    for attempt in range(max_retries):
        try:
            if enhanced_retriever is None:
                return {"status": "error", "answer": None, "items": [], "sources": [], "message": "検索サービスが初期化されていません。", "reason": "service_not_initialized", "meta": {"search_attempt": attempt + 1}}
            # row_idパラメータは将来の拡張用（現在はNone）
            docs = enhanced_retriever.hybrid_search(message, row_id_filter=None)
            if not docs:
                return {"status": "error", "answer": None, "items": [], "sources": [], "message": "関連する社内ドキュメントが見つかりませんでした。", "reason": "no_context", "meta": {"search_attempt": attempt + 1}}
            context_parts = []
            items = []
            sources = []
            for i, doc in enumerate(docs, 1):
                company = doc.metadata.get("company", "Unknown")
                lead_status = doc.metadata.get("lead_status", "未設定")
                
                # 行統合ドキュメントの場合
                if doc.metadata.get("row_type") == "integrated_row":
                    excel_row = doc.metadata.get("excel_row", "?")
                    matched_columns = doc.metadata.get("matched_columns", [])
                    source_id = f"行{excel_row}_統合"
                    
                    items.append({
                        "company": company, 
                        "lead_status": lead_status, 
                        "source_id": source_id,
                        "row_info": f"行{excel_row}（マッチ列: {', '.join(matched_columns)}）"
                    })
                    sources.append(f"{company} - 行{excel_row} ({lead_status})")
                    
                    # 行全体の内容を表示（マッチした列を強調）
                    context_parts.append(f"{i}. 【行{excel_row}の全情報】\n{doc.page_content}")
                else:
                    # 従来のセル単位ドキュメント
                    source_id = doc.metadata.get("row_id", f"doc_{i}")
                    cell_pos = doc.metadata.get("cell_position_info", "")
                    
                    items.append({
                        "company": company, 
                        "lead_status": lead_status, 
                        "source_id": source_id,
                        "cell_info": cell_pos
                    })
                    sources.append(f"{company} - {cell_pos} ({lead_status})")
                    context_parts.append(f"{i}. {doc.page_content}")
            context = "\n".join(context_parts)
            system_instruction = """あなたは営業支援AIアシスタントです。架電リストの企業データベースから情報を抽出し、営業活動を支援してください。

【重要な指示】
- 与えられたコンテキストのみを根拠に回答してください
- 回答には必ず「企業名」と「リードステータス」を含めてください
- 根拠が不十分な場合は「わからない」と明記してください
- 推測や憶測は避け、事実のみを提供してください

【回答形式】
企業名: [企業名]
リードステータス: [ステータス]
その他の情報: [関連情報]"""
            user_prompt = f"""【質問】
{message}

【企業データベース情報】
{context}

上記の情報を基に、質問に対して正確に回答してください。"""
            if not config.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY が設定されていません")
            llm = ChatGoogleGenerativeAI(
                model=config.GEMINI_CHAT_MODEL, 
                google_api_key=SecretStr(config.GEMINI_API_KEY), 
                temperature=0.2, 
                top_p=0.9, 
                client_options=None, 
                transport=None, 
                client=None
            )
            response = llm.invoke(f"{system_instruction}\n\n{user_prompt}")
            answer = response.content
            return {"status": "ok", "answer": answer, "items": items, "sources": sources, "message": None, "reason": None, "meta": {"documents_found": len(docs), "search_attempt": attempt + 1, "llm_model": config.GEMINI_CHAT_MODEL}}
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "5" in error_msg[:1] or "timeout" in error_msg.lower():
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"WARNING: LLM エラー（試行 {attempt + 1}/{max_retries}）: {error_msg}")
                    print(f"INFO: {wait_time:.2f}秒待機後にリトライします...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {"status": "error", "answer": None, "items": [], "sources": [], "message": "LLMサービスが利用できません。しばらく後に再試行してください。", "reason": "llm_unavailable", "meta": {"max_retries_exceeded": True, "last_error": error_msg}}
            else:
                return {"status": "error", "answer": None, "items": [], "sources": [], "message": f"処理中にエラーが発生しました: {error_msg}", "reason": "processing_error", "meta": {"error": error_msg}}
    return {"status": "error", "answer": None, "items": [], "sources": [], "message": "予期しないエラーが発生しました", "reason": "unknown_error", "meta": {}}


@app.post("/ingest-excel")
async def ingest_excel():
    """Excel ファイルをインデックス化"""
    try:
        if excel_ingestor is None:
            return JSONResponse(
                status_code=500,
                content={"error": "Excel ingestor not initialized", "detail": "Service initialization failed"}
            )
        
        # Excel ファイルパスの構築
        excel_path = Path(config.DATA_DIR) / "docs" / "rag用_架電リスト.xlsx"
        
        if not excel_path.exists():
            return JSONResponse(
                status_code=404,
                content={"error": "Excel file not found", "detail": f"Excel ファイルが見つかりません: {excel_path}"}
            )
        
        # Excel データの取り込み（最初のシートを自動選択）
        result = excel_ingestor.ingest_excel_file(
            str(excel_path)
        )
        
        return result
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Excel ingestion failed", "detail": str(e)}
        )


@app.get("/search-stats")
async def get_search_stats():
    """検索統計情報を取得"""
    try:
        if enhanced_retriever is None:
            return JSONResponse(
                status_code=500,
                content={"error": "Enhanced retriever not initialized", "detail": "Service initialization failed"}
            )
        
        stats = enhanced_retriever.get_search_statistics()
        return stats
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Stats retrieval failed", "detail": str(e)}
        )

@app.get("/company/by-cell", response_model=CompanyByRowResponse)
async def get_company_by_cell(cell: str):
    """
    セル参照（例：A2）から企業データを取得
    Args:
        cell: セル参照文字列（例："A2", "B10"）
    Returns:
        その行の企業データ
    """
    try:
        # セル参照から行番号を抽出
        try:
            row_id = parse_row_from_cell(cell)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Excelファイルを読み込み
        excel_path = Path(config.DATA_DIR) / "docs" / "rag用_架電リスト.xlsx"
        if not excel_path.exists():
            raise HTTPException(status_code=404, detail=f"Excelファイルが見つかりません: {excel_path}")
        
        try:
            # Excelファイルを読み込み（結合セル対応）
            df_raw = pd.read_excel(str(excel_path), engine='openpyxl', dtype=str, header=None)
            df_raw = df_raw.fillna("")
            
            if len(df_raw) < 2:
                raise HTTPException(status_code=400, detail="Excelファイルのデータが不十分です")
            
            # ヘッダー処理
            header_row = df_raw.iloc[0].tolist()
            processed_header = []
            for i, cell_value in enumerate(header_row):
                if cell_value and cell_value.strip():
                    processed_header.append(cell_value.strip())
                else:
                    col_letter = chr(ord('A') + i)
                    processed_header.append(f"列{col_letter}")
            
            # データ部分を取得（2行目以降）
            df = df_raw.iloc[1:].copy()
            df.columns = processed_header
            
            # row_id列を付与
            df = df.reset_index().assign(row_id=lambda d: d.index + 2)
            
            # 指定された行番号のデータを検索
            matching_rows = df[df['row_id'] == row_id]
            
            if matching_rows.empty:
                raise HTTPException(status_code=404, detail=f"行番号 {row_id} のデータが見つかりません")
            
            # 最初にマッチした行を取得
            row_data = matching_rows.iloc[0]
            
            # 結果を辞書形式で整理
            company_data = {}
            for col_name in df.columns:
                if col_name != 'index':  # reset_indexで作られたindexカラムは除外
                    value = row_data[col_name]
                    if pd.notna(value) and str(value).strip() and str(value) != 'nan':
                        company_data[col_name] = str(value).strip()
            
            print(f"INFO: GET /company/by-cell -> 200 (cell={cell}, row_id={row_id})")
            return CompanyByRowResponse(
                status="success",
                company_data=company_data,
                row_id=row_id,
                message=f"行 {row_id} のデータを正常に取得しました"
            )
            
        except Exception as e:
            print(f"ERROR: Excelファイル処理エラー: {e}")
            raise HTTPException(status_code=500, detail=f"Excelファイルの処理中にエラーが発生しました: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR: GET /company/by-cell -> 500 ({e})")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=config.BACKEND_PORT, reload=True)

