/**
 * バックエンド API との通信を管理するモジュール
 * 新しい企業データベース RAG システム用のAPIラッパー
 */

function assertBackendEnv() {
  if (!process.env.NEXT_PUBLIC_BACKEND_URL) {
    throw new ApiError({ message: 'NEXT_PUBLIC_BACKEND_URL is missing in .env.local', status: 500 });
  }
}

// === 型定義 ===

export interface CompanyInfo {
  company: string;
  lead_status: string;
  source_id: string;
}

export interface AskResponse {
  status: 'ok' | 'error';
  answer: string | null;
  items: CompanyInfo[];
  sources: string[];
  message: string | null;
  reason: string | null;
  meta: Record<string, any>;
}

export interface IngestResponse {
  status: string;
  message: string;
  processed_records?: number;
  total_chunks?: number;
  collection?: string;
}

export interface UploadResponse {
  status: string;
  message: string;
  filename?: string;
}

export interface SearchStats {
  total_documents: number;
  lead_status_distribution: Record<string, number>;
  search_parameters: {
    top_k: number;
    final_k: number;
    score_threshold: number;
    mmr_lambda: number;
  };
}

export interface CompanyByRowResponse {
  status: string;
  company_data?: Record<string, any>;
  row_id?: number;
  message?: string;
}

export interface SearchByRowRequest {
  query: string;
  row_id?: number;
}

export interface ApiErrorPayload {
  message: string;
  status?: number;
  details?: string;
}

// === APIラッパー関数 ===

export async function ask(question: string): Promise<AskResponse> {
  try {
    assertBackendEnv();
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: question }),
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    const data: AskResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error in ask():', error);
    throw new ApiError({ message: error instanceof Error ? error.message : 'API呼び出しエラー', status: error instanceof Error && 'status' in error ? (error as any).status : undefined });
  }
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  try {
    assertBackendEnv();
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    const data: UploadResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error in uploadFile():', error);
    throw new ApiError({ message: error instanceof Error ? error.message : 'ファイルアップロードエラー', status: error instanceof Error && 'status' in error ? (error as any).status : undefined });
  }
}

export async function ingestExcel(): Promise<IngestResponse> {
  try {
    const response = await fetch('/api/reindex', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    const data: IngestResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error in ingestExcel():', error);
    throw new ApiError({ message: error instanceof Error ? error.message : 'Excel取り込みエラー', status: error instanceof Error && 'status' in error ? (error as any).status : undefined });
  }
}

export async function getSearchStats(): Promise<SearchStats> {
  try {
    const response = await fetch('/api/stats', { method: 'GET', headers: { 'Content-Type': 'application/json' } });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    const data: SearchStats = await response.json();
    return data;
  } catch (error) {
    console.error('Error in getSearchStats():', error);
    throw new ApiError({ message: error instanceof Error ? error.message : '統計情報取得エラー', status: error instanceof Error && 'status' in error ? (error as any).status : undefined });
  }
}

export async function chat(message: string): Promise<any> {
  try {
    const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error in chat():', error);
    throw new ApiError({ message: error instanceof Error ? error.message : 'チャットエラー', status: error instanceof Error && 'status' in error ? (error as any).status : undefined });
  }
}

export async function getCompanyByCell(cell: string): Promise<CompanyByRowResponse> {
  try {
    const response = await fetch(`/api/company/by-cell?cell=${encodeURIComponent(cell)}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    const data: CompanyByRowResponse = await response.json();
    return data;
  } catch (error) {
    console.error('Error in getCompanyByCell():', error);
    throw new ApiError({ message: error instanceof Error ? error.message : 'セル指定での企業データ取得エラー', status: error instanceof Error && 'status' in error ? (error as any).status : undefined });
  }
}

export async function searchByRow(query: string, rowId?: number): Promise<any> {
  try {
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, row_id: rowId }),
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error in searchByRow():', error);
    throw new ApiError({ message: error instanceof Error ? error.message : '行指定でのRAG検索エラー', status: error instanceof Error && 'status' in error ? (error as any).status : undefined });
  }
}

// === ユーティリティ関数 ===

/**
 * リードステータスに応じたCSS クラス名を取得
 */
export function getLeadStatusClass(leadStatus: string): string {
  const statusMap: Record<string, string> = {
    'アポイント獲得': 'bg-green-100 text-green-800 border-green-200',
    'リード獲得': 'bg-blue-100 text-blue-800 border-blue-200',
    '未コール': 'bg-yellow-100 text-yellow-800 border-yellow-200',
    '不在': 'bg-gray-100 text-gray-800 border-gray-200',
    '受付拒否': 'bg-red-100 text-red-800 border-red-200',
    '不在情報取得あり': 'bg-purple-100 text-purple-800 border-purple-200',
    'コンタクト結果NG': 'bg-orange-100 text-orange-800 border-orange-200',
    '未設定': 'bg-gray-50 text-gray-600 border-gray-300',
  };

  return statusMap[leadStatus] || statusMap['未設定'];
}

/**
 * リードステータスに応じた表示色を取得
 */
export function getLeadStatusColor(leadStatus: string): string {
  const colorMap: Record<string, string> = {
    'アポイント獲得': 'success',
    'リード獲得': 'info',
    '未コール': 'warning',
    '不在': 'secondary',
    '受付拒否': 'danger',
    '不在情報取得あり': 'primary',
    'コンタクト結果NG': 'warning',
    '未設定': 'light',
  };

  return colorMap[leadStatus] || 'light';
}

/**
 * エラーメッセージの日本語化
 */
export function getLocalizedErrorMessage(error: any): string {
  if (error?.reason) {
    switch (error.reason) {
      case 'no_context':
        return '関連する企業情報が見つかりませんでした。別の言い方で質問してみてください。';
      case 'llm_unavailable':
        return 'AIサービスが一時的に利用できません。しばらく経ってから再試行してください。';
      case 'processing_error':
        return '処理中にエラーが発生しました。';
      default:
        return error.message || '予期しないエラーが発生しました。';
    }
  }

  if (error?.message) {
    if (error.message.includes('fetch')) {
      return 'サーバーとの通信に失敗しました。ネットワーク接続を確認してください。';
    }
    if (error.message.includes('timeout')) {
      return 'タイムアウトしました。しばらく経ってから再試行してください。';
    }
    return error.message;
  }

  return '予期しないエラーが発生しました。';
}

/**
 * APIエラーのカスタムクラス
 */
class ApiError extends Error {
  public status?: number;
  public details?: string;

  constructor(options: { message: string; status?: number; details?: string }) {
    super(options.message);
    this.name = 'ApiError';
    this.status = options.status;
    this.details = options.details;
  }
}

export { ApiError };