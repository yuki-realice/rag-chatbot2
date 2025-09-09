#!/bin/bash

# プロジェクトIDを設定（実際のプロジェクトIDに変更してください）
PROJECT_ID="ragbot-dev-2025-471207"

# バックエンドのURLを設定（実際のバックエンドのCloud Run URLに変更してください）
BACKEND_URL="https://backend-334537300106.asia-northeast1.run.app/"

# 環境変数を設定
export NEXT_PUBLIC_BACKEND_URL="https://backend-334537300106.asia-northeast1.run.app"

echo "�� フロントエンドをCloud Runにデプロイ中..."

# Cloud Buildを実行
gcloud builds submit --config cloudbuild.yaml --project $PROJECT_ID

echo "✅ デプロイ完了！"
echo "フロントエンドURL: https://rag-chatbot-frontend-[hash]-uc.a.run.app"
