# RAG Chatbot

Next.js + FastAPI + OpenAI + ChromaDB を使用した RAG (Retrieval-Augmented Generation) チャットボット

## 🚀 機能

- **ドキュメントアップロード**: PDF、Markdown、テキストファイルのアップロード
- **自動インデックス化**: アップロードされたドキュメントの自動ベクトル化とChromaDBへの格納
- **RAG チャット**: ドキュメントベースの質問応答システム
- **ソース表示**: 回答の根拠となる文書の表示
- **モダンUI**: TailwindCSSを使用したレスポンシブデザイン

## 📁 プロジェクト構造

```
rag-chatbot/
├── frontend/                 # Next.js フロントエンド
│   ├── app/                 # App Router
│   ├── components/          # React コンポーネント
│   ├── lib/                 # ユーティリティ
│   └── types/               # TypeScript 型定義
├── backend/                 # FastAPI バックエンド
│   ├── main.py             # FastAPI アプリケーション
│   ├── config.py           # 設定ファイル
│   ├── rag_service.py      # RAG サービス
│   └── requirements.txt    # Python 依存関係
├── data/                   # ドキュメント保存ディレクトリ
├── scripts/                # 便利スクリプト
├── tests/                  # テストファイル
└── env.example             # 環境変数サンプル
```

## 🛠️ セットアップ

### 1. 環境変数の設定

```bash
# 環境変数ファイルをコピー
cp env.example .env

# .env ファイルを編集して OpenAI API キーを設定
nano .env
```

必要な環境変数:
- `OPENAI_API_KEY`: OpenAI API キー
- `NEXT_PUBLIC_API_BASE_URL`: バックエンドURL (デフォルト: http://localhost:8000)

### 2. バックエンドのセットアップ

```bash
cd backend

# Python仮想環境を作成
python3 -m venv venv

# 仮想環境をアクティベート
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 依存関係をインストール
pip install -r requirements.txt
```

### 3. フロントエンドのセットアップ

```bash
cd frontend

# 依存関係をインストール
npm install
```

## 🚀 実行方法

### 方法1: 開発スクリプトを使用（推奨）

```bash
# プロジェクトルートで実行
./scripts/dev.sh
```

### 方法2: 手動で起動

#### バックエンド起動
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

#### フロントエンド起動
```bash
cd frontend
npm run dev
```

## 📱 アクセス

- **フロントエンド**: http://localhost:3000
- **バックエンド**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs

## 🔧 使用方法

1. **ドキュメントのアップロード**
   - 左サイドバーのファイルアップロード機能を使用
   - 対応形式: PDF (.pdf), Markdown (.md, .markdown), テキスト (.txt), Excel (.xlsx), スプレッドシート (.csv, .tsv)

2. **インデックス作成**
   - 「インデックス再作成」ボタンをクリック
   - アップロードされたドキュメントがベクトル化され、ChromaDBに格納されます

3. **チャット**
   - 右側のチャットエリアでドキュメントについて質問
   - AIが関連する文書を検索して回答を生成
   - 回答の根拠となる文書も表示されます

## ⚙️ 設定

### RAG設定 (backend/config.py)

- `RAG_EMBEDDING_MODEL`: 埋め込みモデル (デフォルト: text-embedding-3-small)
- `RAG_EMBEDDING_PROVIDER`: `openai` か `huggingface` を指定（デフォルト: `openai`）
- `HF_EMBEDDING_MODEL`: Hugging Face の埋め込みモデル名（例: `sentence-transformers/all-MiniLM-L6-v2`）
- `RAG_CHAT_MODEL`: チャットモデル (デフォルト: gpt-4o-mini)
- `RAG_CHAT_PROVIDER`: `openai` または `gemini`（デフォルト: `openai`）
- `GEMINI_API_KEY`: Google Generative AI のAPIキー
- `GEMINI_MODEL`: Geminiモデル名（例: `gemini-1.5-flash`）
- `RAG_TOP_K`: 検索する類似文書数 (デフォルト: 4)
- `RAG_CHUNK_SIZE`: テキスト分割サイズ (デフォルト: 800)
- `RAG_CHUNK_OVERLAP`: チャンク間のオーバーラップ (デフォルト: 100)

#### Gemini を使う場合の設定例（.env）
```bash
RAG_CHAT_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-1.5-flash
```

#### OpenAI を使わず埋め込みもローカルにする例（.env）
```bash
RAG_EMBEDDING_PROVIDER=huggingface
HF_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## 🧪 テスト

```bash
cd backend
source venv/bin/activate
pytest ../tests/
```

## 🔍 トラブルシューティング

### よくある問題

1. **OpenAI API キーエラー**
   - `.env` ファイルに正しい API キーが設定されているか確認
   - API キーに十分なクレジットがあるか確認

2. **CORS エラー**
   - バックエンドが正しく起動しているか確認
   - フロントエンドの `NEXT_PUBLIC_API_BASE_URL` が正しく設定されているか確認

3. **ポート競合**
   - ポート 3000 または 8000 が他のプロセスで使用されていないか確認
   - `lsof -i :3000` または `lsof -i :8000` で確認

4. **ファイルアップロードエラー**
   - ファイル形式が対応しているか確認 (.pdf, .md, .txt, .markdown)
   - ファイルサイズが適切か確認

5. **インデックス化エラー**
   - `data/` ディレクトリにファイルが存在するか確認
   - ファイルが破損していないか確認

## 📚 技術スタック

- **フロントエンド**: Next.js 14, React 18, TypeScript, TailwindCSS
- **バックエンド**: FastAPI, Python 3.11+
- **AI/ML**: OpenAI API, LangChain
- **ベクトルDB**: ChromaDB
- **開発ツール**: Uvicorn, ESLint, Prettier

## 🤝 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。

## 🙏 謝辞

- OpenAI の API とモデル
- LangChain コミュニティ
- ChromaDB チーム
- Next.js と FastAPI の開発者

