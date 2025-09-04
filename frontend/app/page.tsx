'use client';

import { useState } from 'react';
import Uploader from '../components/Uploader';
import Chat from '../components/Chat';

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUploadSuccess = () => {
    // アップロード成功時にチャットコンポーネントをリフレッシュ
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        {/* ヘッダー */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            企業データベース RAG システム
          </h1>
          <p className="text-gray-600">
            架電リストから企業情報を検索し、営業活動を支援します
          </p>
        </div>

        {/* メインコンテンツ - チャット画面のみ */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 左サイドバー - アップローダー */}
          <div className="lg:col-span-1">
            <Uploader onUploadSuccess={handleUploadSuccess} />
          </div>

          {/* 右サイド - チャット */}
          <div className="lg:col-span-2 h-[600px]">
            <Chat key={refreshKey} />
          </div>
        </div>

        {/* フッター */}
        <div className="mt-12 text-center text-sm text-gray-500">
          <p>
            Powered by Next.js, FastAPI, Gemini 2.5 Flash, and ChromaDB
          </p>
        </div>
      </div>
    </div>
  );
}

