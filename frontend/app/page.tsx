'use client';

import { useState } from 'react';
import Uploader from '../components/Uploader';
import Chat from '../components/Chat';
import LeadStatusSearch from '../components/LeadStatusSearch';

export default function Home() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [activeTab, setActiveTab] = useState<'legacy' | 'leads'>('leads');

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

        {/* タブ切り替え */}
        <div className="flex justify-center mb-8">
          <div className="flex bg-white rounded-lg shadow-sm border p-1">
            <button
              onClick={() => setActiveTab('leads')}
              className={`px-6 py-2 rounded-md font-medium transition-colors ${
                activeTab === 'leads'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              企業検索
            </button>
            <button
              onClick={() => setActiveTab('legacy')}
              className={`px-6 py-2 rounded-md font-medium transition-colors ${
                activeTab === 'legacy'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              従来チャット
            </button>
          </div>
        </div>

        {/* メインコンテンツ */}
        {activeTab === 'leads' ? (
          /* 企業検索画面 */
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* 左サイドバー - アップローダー & 統計 */}
            <div className="lg:col-span-1">
              <Uploader onUploadSuccess={handleUploadSuccess} />
            </div>

            {/* メインエリア - 企業検索 */}
            <div className="lg:col-span-3">
              <LeadStatusSearch key={refreshKey} />
            </div>
          </div>
        ) : (
          /* 従来のチャット画面 */
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
        )}

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

