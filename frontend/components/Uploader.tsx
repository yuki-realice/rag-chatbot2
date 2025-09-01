'use client';

import { useState } from 'react';
import { ingestExcel } from '../lib/api';

interface UploaderProps {
  onUploadSuccess: () => void;
}

export default function Uploader({ onUploadSuccess }: UploaderProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [isIngesting, setIsIngesting] = useState(false);
  const [message, setMessage] = useState('');

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setMessage('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result?.error || result?.message || 'アップロードに失敗しました');
      }

      setMessage(`✅ ${result.message}`);
      onUploadSuccess();
    } catch (error) {
      setMessage(`❌ アップロードエラー: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsUploading(false);
    }
  };

  const handleIngest = async () => {
    setIsIngesting(true);
    setMessage('');

    try {
      const response = await fetch('/api/ingest', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result?.error || result?.message || 'インデックス化に失敗しました');
      }

      setMessage(`✅ ${result.message}`);
      onUploadSuccess();
    } catch (error) {
      setMessage(`❌ インデックス化エラー: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsIngesting(false);
    }
  };

  const handleIngestExcel = async () => {
    setIsIngesting(true);
    setMessage('');

    try {
      const result = await ingestExcel();
      setMessage(`✅ ${result.message}`);
      onUploadSuccess();
    } catch (error) {
      setMessage(`❌ Excel インデックス化エラー: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsIngesting(false);
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-xl font-semibold mb-4">ドキュメント管理</h2>
      
      {/* ファイルアップロード */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          ドキュメントをアップロード
        </label>
        <div className="flex items-center space-x-4">
          <input
            type="file"
            accept=".pdf,.md,.txt,.markdown,.xlsx,.csv,.tsv"
            onChange={handleFileUpload}
            disabled={isUploading}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          {isUploading && (
            <div className="text-blue-600">アップロード中...</div>
          )}
        </div>
      </div>

      {/* インデックス再作成 */}
      <div className="mb-4 space-y-2">
        <button
          onClick={handleIngest}
          disabled={isIngesting}
          className="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          {isIngesting ? 'インデックス化中...' : 'アップロードファイルをインデックス化'}
        </button>
        <button
          onClick={handleIngestExcel}
          disabled={isIngesting}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-md transition-colors"
        >
          {isIngesting ? 'Excel 取り込み中...' : 'Excel ファイルを取り込み'}
        </button>
      </div>

      {/* メッセージ表示 */}
      {message && (
        <div className={`p-3 rounded-md text-sm ${
          message.startsWith('✅') 
            ? 'bg-green-50 text-green-800 border border-green-200' 
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {message}
        </div>
      )}

      {/* ヘルプテキスト */}
      <div className="mt-4 text-sm text-gray-600">
        <p className="mb-2">対応ファイル形式:</p>
        <ul className="list-disc list-inside space-y-1">
          <li>PDF (.pdf)</li>
          <li>Markdown (.md, .markdown)</li>
          <li>テキスト (.txt)</li>
          <li>Excel (.xlsx)</li>
          <li>スプレッドシート (.csv, .tsv)</li>
        </ul>
      </div>
    </div>
  );
}

