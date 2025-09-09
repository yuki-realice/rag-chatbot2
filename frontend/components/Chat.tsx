'use client';

import { useState, useRef, useEffect } from 'react';
import { ChatMessage, Source } from '../types';
import { chat, getLeadStatusClass } from '../lib/api';

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [debugInfo, setDebugInfo] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    console.log('🚀 チャット送信開始:', inputMessage);
    setDebugInfo('送信中...');

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: inputMessage,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      console.log('📡 API呼び出し開始...');
      setDebugInfo('API呼び出し中...');
      
      const response = await chat(inputMessage);
      console.log('✅ API応答受信:', response);
      setDebugInfo('応答受信完了');

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: response.answer || response.message || '応答が空です',
        role: 'assistant',
        timestamp: new Date(),
        sources: response.sources,
        items: response.items,
      };
      
      setMessages(prev => [...prev, assistantMessage]);
      setDebugInfo('');
    } catch (error) {
      console.error('❌ チャットエラー:', error);
      
      let errorMessage = 'Unknown error';
      let debugMessage = '';

      if (error instanceof Error) {
        errorMessage = error.message;
        debugMessage = `エラー詳細: ${error.message}`;
      }

      // ネットワークエラーの詳細チェック
      if (errorMessage.includes('fetch')) {
        debugMessage += '\nネットワーク接続を確認してください';
      }
      if (errorMessage.includes('500')) {
        debugMessage += '\nサーバーエラーが発生しました';
      }
      if (errorMessage.includes('404')) {
        debugMessage += '\nAPIエンドポイントが見つかりません';
      }

      const errorChatMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: `❌ エラーが発生しました: ${errorMessage}`,
        role: 'assistant',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorChatMessage]);
      setDebugInfo(debugMessage);
    } finally {
      setIsLoading(false);
      console.log(' チャット処理完了');
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="surface">
        {/* ヘッダー */}
        <div className="p-6">
          <h2 className="text-[20px] font-semibold tracking-[-0.01em]" style={{ color: '#0b0b0d' }}>RAG チャット</h2>
          <p className="text-[13px] mt-1" style={{ color: '#444' }}>企業データベースから正確に抽出します</p>
          
          {/* デバッグ情報表示 */}
          {debugInfo && (
            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs" style={{ color: '#666' }}>
              <strong>デバッグ:</strong> {debugInfo}
            </div>
          )}
        </div>
        <div className="hr" />

        {/* メッセージ */}
        <div className="h-[60vh] overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-16" style={{ color: '#444' }}>
              <p>企業名を入力して、リードステータスを確認しましょう</p>
            </div>
          ) : (
            messages.map((message) => {
              const isUser = message.role === 'user';
              return (
                <div key={message.id} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className="max-w-[78%] rounded-2xl px-4 py-3 border"
                    style={{
                      background: '#ffffff',
                      borderColor: 'rgba(0,0,0,0.10)',
                      boxShadow: '0 6px 18px rgba(0,0,0,0.10)',
                      color: '#0b0b0d',
                    }}
                  >
                    {/* LLMの回答を常に表示 */}
                    <div className="whitespace-pre-wrap text-[15px] leading-[1.55]" style={{ color: '#0b0b0d' }}>
                      {message.content}
                    </div>

                    {/* 参考情報がある場合のみ表示 */}
                    {message.sources && message.sources.length > 0 && (
                      <div className="mt-3 pt-3" style={{ borderTop: '1px solid rgba(0,0,0,0.08)' }}>
                        <p className="text-[12px] font-medium mb-2" style={{ color: '#444' }}>参考</p>
                        <div className="space-y-1">
                          {message.sources.map((source: Source, index: number) => (
                            <div key={index} className="text-[12px]" style={{ color: '#444' }}>
                              <span className="font-medium" style={{ color: '#0b0b0d' }}>{source.source}</span>
                              <span className="opacity-80"> — {source.content}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="text-[11px] mt-2" style={{ color: '#444' }}>
                      {formatTimestamp(message.timestamp)}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="hr" />
        {/* 入力エリア */}
        <div className="p-6">
          <form onSubmit={handleSubmit} className="flex items-center gap-3">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="企業名を入力してください"
              disabled={isLoading}
              className="input"
            />
            <button
              type="submit"
              disabled={isLoading || !inputMessage.trim()}
              className="btn-primary"
            >
              {isLoading ? '送信中...' : '送信'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}