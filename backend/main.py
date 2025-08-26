from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, cast
import os
import shutil
from pathlib import Path

from config import Config
from rag_service import RAGService

app = FastAPI(title="RAG Chatbot API", version="1.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 設定とサービスの初期化
config = Config()
rag_service = RAGService()

# データディレクトリの作成
data_dir = Path(config.DATA_DIR)
data_dir.mkdir(exist_ok=True)

# Pydanticモデル
class ChatRequest(BaseModel):
    message: str

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

@app.get("/")
async def root():
    return {"message": "RAG Chatbot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """ファイルをアップロードしてdataディレクトリに保存"""
    try:
        # filename の存在チェック（pyright用の型絞り込み）
        if file.filename is None:
            raise HTTPException(
                status_code=400,
                detail="Filename is required"
            )
        filename = cast(str, file.filename)
        
        # ファイル拡張子のチェック
        file_extension = Path(filename).suffix.lower()
        if file_extension not in config.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {config.ALLOWED_EXTENSIONS}"
            )
        
        # ファイルを保存
        file_path = data_dir / filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return UploadResponse(
            status="success",
            message=f"File {filename} uploaded successfully",
            filename=filename
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest", response_model=IngestResponse)
async def ingest_documents():
    """dataディレクトリ内のドキュメントをインデックス化"""
    try:
        result = rag_service.ingest_documents()
        return IngestResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """チャット応答を生成"""
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        result = rag_service.chat(request.message)
        return ChatResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=config.BACKEND_PORT,
        reload=True
    )

