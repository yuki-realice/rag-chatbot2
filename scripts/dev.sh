#!/bin/bash

# RAG Chatbot 開発環境起動スクリプト

echo "🚀 RAG Chatbot 開発環境を起動します..."

# 環境変数ファイルの確認
if [ ! -f ".env" ]; then
    echo "⚠️  .env ファイルが見つかりません。env.example をコピーして設定してください。"
    echo "cp env.example .env"
    exit 1
fi

# バックエンドディレクトリに移動
cd backend

# Python仮想環境の確認と作成
if [ ! -d "venv" ]; then
    echo "📦 Python仮想環境を作成中..."
    python3 -m venv venv
fi

# 仮想環境をアクティベート
echo "🔧 仮想環境をアクティベート中..."
source venv/bin/activate

# 依存関係のインストール
echo "📚 依存関係をインストール中..."
pip install -r requirements.txt

# バックエンドを起動
echo "🔧 バックエンドを起動中... (http://localhost:8000)"
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# バックエンドの起動を待つ
echo "⏳ バックエンドの起動を待機中..."
sleep 5

# フロントエンドディレクトリに移動
cd ../frontend

# 依存関係のインストール
echo "📚 フロントエンド依存関係をインストール中..."
npm install

# フロントエンドを起動
echo "🎨 フロントエンドを起動中... (http://localhost:3000)"
npm run dev &
FRONTEND_PID=$!

echo "✅ 開発環境が起動しました！"
echo "📱 フロントエンド: http://localhost:3000"
echo "🔧 バックエンド: http://localhost:8000"
echo "📖 API ドキュメント: http://localhost:8000/docs"
echo ""
echo "🛑 停止するには Ctrl+C を押してください"

# シグナルハンドラー
trap 'echo "🛑 開発環境を停止中..."; kill $BACKEND_PID $FRONTEND_PID; exit' INT

# プロセスを待機
wait

