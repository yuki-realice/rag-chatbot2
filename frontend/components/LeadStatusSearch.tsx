'use client';

import { useState, useRef } from 'react';
import { ask, ingestExcel, getSearchStats, type AskResponse, type CompanyInfo, getLocalizedErrorMessage } from '../lib/api';

interface SearchHistory {
  id: string;
  question: string;
  timestamp: Date;
  response: any;
}

export default function LeadStatusSearch() {
  const [question, setQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchHistory, setSearchHistory] = useState<SearchHistory[]>([]);
  const [showSources, setShowSources] = useState(false);
  const [stats, setStats] = useState<any>(null);
  const questionInputRef = useRef<HTMLInputElement>(null);

  const handleSearch = async () => {
    if (!question.trim()) return;

    setIsLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: question.trim() }),
      });
      const data = await res.json();
      setResponse(data);

      const historyItem: SearchHistory = {
        id: Date.now().toString(),
        question: question.trim(),
        timestamp: new Date(),
        response: data,
      };
      setSearchHistory(prev => [historyItem, ...prev.slice(0, 9)]);
      setQuestion('');
    } catch (err: any) {
      console.error('Search error:', err);
      setError(getLocalizedErrorMessage(err));
    } finally {
      setIsLoading(false);
    }
  };

  const handleIngestExcel = async () => {
    setIsIngesting(true);
    setError(null);

    try {
      const result = await ingestExcel();
      if (result.status === 'success') {
        alert(`Excel 取り込み完了！\n処理レコード: ${result.processed_records}\nチャンク数: ${result.total_chunks}`);
        loadStats();
      } else {
        setError(result.message || 'Excel 取り込みに失敗しました');
      }
    } catch (err: any) {
      console.error('Ingest error:', err);
      setError(getLocalizedErrorMessage(err));
    } finally {
      setIsIngesting(false);
    }
  };

  const loadStats = async () => {
    try {
      const statsData = await getSearchStats();
      setStats(statsData);
    } catch (err) {
      console.error('Stats loading error:', err);
    }
  };

  const handleRetry = () => {
    if (question.trim()) {
      handleSearch();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const LeadStatusBadge = ({ status }: { status: string }) => (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium border`}>
      {status}
    </span>
  );

  const ResultsTable = ({ items }: { items: CompanyInfo[] }) => (
    <div className="overflow-x-auto">
      <table className="w-full bg-white border border-gray-200 rounded-lg">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">企業名</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">リードステータス</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ソースID</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {items.map((item, index) => (
            <tr key={index} className="hover:bg-gray-50">
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">{item.company}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap"><LeadStatusBadge status={item.lead_status} /></td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{item.source_id}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="bg-white rounded-lg shadow-sm border p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-gray-900">企業データベース検索</h2>
        <div className="flex gap-2">
          <button onClick={loadStats} className="px-3 py-1 text-sm text-blue-600 hover:text-blue-800">統計更新</button>
          <button onClick={handleIngestExcel} disabled={isIngesting} className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {isIngesting ? 'Excel 取り込み中...' : 'Excel 取り込み'}
          </button>
        </div>
      </div>

      {/* AI回答（フォールバック含む） */}
      {response?.answer && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <h3 className="text-sm font-medium text-blue-800 mb-2">AI 回答</h3>
          <div className="text-sm text-blue-700 whitespace-pre-wrap">{response.answer}</div>
        </div>
      )}

      {/* 企業情報（結果がある場合） */}
      {Array.isArray(response?.results) && response.results.length > 0 && (
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-3">検索結果（{response.results.length}件）</h3>
          {/* 必要に応じて results を CompanyInfo へマッピング可能 */}
        </div>
      )}

      {/* 検索フォーム */}
      <div className="mb-6">
        <div className="flex gap-2">
          <input
            ref={questionInputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="企業名や条件を入力してください"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button onClick={handleSearch} disabled={isLoading || !question.trim()} className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
            {isLoading ? '検索中...' : '検索'}
          </button>
        </div>
      </div>

      {/* エラー表示 */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="text-red-400 mr-3">⚠️</div>
              <div>
                <h4 className="text-sm font-medium text-red-800">エラーが発生しました</h4>
                <p className="text-sm text-red-600 mt-1">{error}</p>
              </div>
            </div>
            <button onClick={handleRetry} className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200">再試行</button>
          </div>
        </div>
      )}

      {/* 検索履歴は変更なし */}
    </div>
  );
}
