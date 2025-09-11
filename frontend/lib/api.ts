/**
 * バックエンド API との通信を管理するモジュール
 * 新しい企業データベース RAG システム用のAPIラッパー
 */

// === エラーハンドリング用の型定義 ===

export interface ApiErrorDetails {
  message: string;
  status?: number;
  code?: string;
  debug?: string;
  timestamp?: string;
  requestId?: string;
  backendUrl?: string;
}

export class ApiError extends Error {
  public status?: number;
  public code?: string;
  public debug?: string;
  public timestamp: string;
  public requestId?: string;
  public backendUrl?: string;

  constructor(details: ApiErrorDetails) {
    super(details.message);
    this.name = 'ApiError';
    this.status = details.status;
    this.code = details.code;
    this.debug = details.debug;
    this.timestamp = details.timestamp || new Date().toISOString();
    this.requestId = details.requestId;
    this.backendUrl = details.backendUrl;
  }
}

// === ユーティリティ関数 ===

function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function getErrorCode(error: any): string {
  if (error?.code) return error.code;
  if (error?.name === 'AbortError') return 'TIMEOUT';
  if (error?.message?.includes('fetch')) return 'NETWORK_ERROR';
  if (error?.message?.includes('JSON')) return 'PARSE_ERROR';
  if (error?.status >= 400 && error?.status < 500) return 'CLIENT_ERROR';
  if (error?.status >= 500) return 'SERVER_ERROR';
  return 'UNKNOWN_ERROR';
}

function getLocalizedErrorMessage(error: any): string {
  const code = getErrorCode(error);

  switch (code) {
    case 'TIMEOUT':
      return 'リクエストがタイムアウトしました。しばらく後に再試行してください。';
    case 'NETWORK_ERROR':
      return 'ネットワーク接続エラーが発生しました。インターネット接続を確認してください。';
    case 'PARSE_ERROR':
      return 'サーバーからの応答を解析できませんでした。';
    case 'CLIENT_ERROR':
      return 'リクエストに問題があります。入力内容を確認してください。';
    case 'SERVER_ERROR':
      return 'サーバーでエラーが発生しました。しばらく後に再試行してください。';
    case 'UNKNOWN_ERROR':
    default:
      return '予期しないエラーが発生しました。';
  }
}

/**
 * 本番(https配信)のフロントからは http/localhost/127.0.0.1 を拒否し、
 * 正しい https のバックエンドURLだけを許可する。
 */
function resolveBackendBase(): string {
  const url = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();
  if (!url) {
    throw new ApiError({
      message: 'NEXT_PUBLIC_BACKEND_URL が未設定です',
      status: 500,
      code: 'MISSING_ENV_VAR',
      debug: '環境変数 NEXT_PUBLIC_BACKEND_URL を .env.* に設定してください',
    });
  }

  const isProd =
    typeof window !== 'undefined' && /^https:\/\//i.test(window.location.origin);

  const isLocalLike = /^http:\/\/(localhost|127\.0\.0\.1)/i.test(url);

  if (isProd) {
    if (!/^https:\/\//i.test(url)) {
      throw new ApiError({
        message: '本番では https のバックエンドURLのみ許可されます',
        status: 500,
        code: 'INVALID_BACKEND_URL',
        debug: `現在のURL: ${url}`,
      });
    }
    if (isLocalLike) {
      throw new ApiError({
        message: '本番環境でローカルホスト(127.0.0.1/localhost)は使用できません',
        status: 500,
        code: 'INVALID_BACKEND_URL',
        debug: `現在のURL: ${url}`,
      });
    }
  }

  return url.replace(/\/+$/,''); // 末尾スラッシュ除去
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

export interface ChatResponse {
  status: string;
  answer?: string;
  sources?: Array<{ source: string; content: string }>;
  items?: CompanyInfo[];
  message?: string;
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
  size?: number;
}

export interface StatsResponse {
  status: string;
  message: string;
  total_documents?: number;
  total_chunks?: number;
  collection_name?: string;
  last_updated?: string;
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

// === API関数 ===

export async function chat(message: string): Promise<ChatResponse> {
  const requestId = generateRequestId();
  const startTime = Date.now();
  console.log(`🚀 [${requestId}] chat() 関数開始:`, message);

  try {
    const backend = resolveBackendBase();
    const endpoint = `${backend}/api/ask`;
    console.log(` [${requestId}] バックエンドにリクエスト送信:`, endpoint);

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': requestId, // ← 禁止ヘッダ(User-Agent)は送らない
      },
      body: JSON.stringify({ message }),
      signal: AbortSignal.timeout(120000), // 120秒
    });

    const responseTime = Date.now() - startTime;
    console.log(`⏱️ [${requestId}] レスポンス時間: ${responseTime}ms`);

    if (!response.ok) {
      let errorText = '';
      let errorData: any = {};
      try {
        errorText = await response.text();
        errorData = JSON.parse(errorText);
      } catch (parseError) {
        console.warn(`⚠️ [${requestId}] エラーレスポンスの解析に失敗:`, parseError);
      }

      throw new ApiError({
        message: `HTTP ${response.status}: ${errorData.error || errorData.detail || errorText || 'サーバーエラー'}`,
        status: response.status,
        code: getErrorCode({ status: response.status }),
        debug: errorData.debug || `バックエンドからエラー応答: ${response.status}`,
        requestId,
        backendUrl: backend,
      });
    }

    const responseText = await response.text();
    const ask: AskResponse = JSON.parse(responseText);

    const data: ChatResponse = {
      status: ask.status,
      answer: ask.answer ?? undefined,
      items: ask.items ?? undefined,
      sources: ask.sources?.map((s: string) => ({ source: s, content: '' })) ?? undefined,
      message: ask.message ?? undefined,
    };

    console.log(`🎉 [${requestId}] チャット処理完了:`, data);
    return data;

  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.error(`❌ [${requestId}] chat() 関数エラー:`, error);

    const errorCode = getErrorCode(error);
    const localizedMessage = getLocalizedErrorMessage(error);

    throw new ApiError({
      message: localizedMessage,
      status: error instanceof Error && 'status' in error ? (error as any).status : undefined,
      code: errorCode,
      debug: error instanceof Error ? error.message : 'Unknown error',
      requestId,
      backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL,
    });
  }
}

export async function ingestExcel(): Promise<IngestResponse> {
  const requestId = generateRequestId();
  const startTime = Date.now();
  console.log(`🚀 [${requestId}] ingestExcel() 関数開始`);

  try {
    const backend = resolveBackendBase();
    const response = await fetch(`${backend}/ingest-excel`, {
      method: 'POST',
      signal: AbortSignal.timeout(600000), // 10分
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError({
        message: `Excel インジェストエラー: HTTP ${response.status}`,
        status: response.status,
        code: getErrorCode({ status: response.status }),
        debug: errorText,
        requestId,
        backendUrl: backend,
      });
    }

    return await response.json();
  } catch (error) {
    throw new ApiError({
      message: getLocalizedErrorMessage(error),
      code: getErrorCode(error),
      debug: error instanceof Error ? error.message : 'Unknown error',
      requestId,
      backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL,
    });
  }
}

// ※ この関数は同一オリジンの /api/search を前提にしています（Next.jsのAPI Routesやrewriteで用いる想定）
export async function ask(question: string): Promise<AskResponse> {
  try {
    const response = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: question }),
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    return await response.json();
  } catch (error) {
    throw new ApiError({
      message: error instanceof Error ? error.message : '検索エラー',
      status: error instanceof Error && 'status' in error ? (error as any).status : undefined,
    });
  }
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const requestId = generateRequestId();
  console.log(`🚀 [${requestId}] uploadFile() 関数開始:`, file.name);

  try {
    const backend = resolveBackendBase();
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${backend}/upload`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(300000), // 5分
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError({
        message: `アップロードエラー: HTTP ${response.status}`,
        status: response.status,
        code: getErrorCode({ status: response.status }),
        debug: errorText,
        requestId,
        backendUrl: backend,
      });
    }

    return await response.json();
  } catch (error) {
    throw new ApiError({
      message: getLocalizedErrorMessage(error),
      code: getErrorCode(error),
      debug: error instanceof Error ? error.message : 'Unknown error',
      requestId,
      backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL,
    });
  }
}

export async function ingestData(): Promise<IngestResponse> {
  const requestId = generateRequestId();
  console.log(`🚀 [${requestId}] ingestData() 関数開始`);

  try {
    const backend = resolveBackendBase();
    const response = await fetch(`${backend}/ingest`, {
      method: 'POST',
      signal: AbortSignal.timeout(600000), // 10分
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError({
        message: `インジェストエラー: HTTP ${response.status}`,
        status: response.status,
        code: getErrorCode({ status: response.status }),
        debug: errorText,
        requestId,
        backendUrl: backend,
      });
    }

    return await response.json();
  } catch (error) {
    throw new ApiError({
      message: getLocalizedErrorMessage(error),
      code: getErrorCode(error),
      debug: error instanceof Error ? error.message : 'Unknown error',
      requestId,
      backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL,
    });
  }
}

export async function getStats(): Promise<StatsResponse> {
  const requestId = generateRequestId();
  console.log(` [${requestId}] getStats() 関数開始`);

  try {
    const backend = resolveBackendBase();
    const response = await fetch(`${backend}/search-stats`, {
      method: 'GET',
      signal: AbortSignal.timeout(30000), // 30秒
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new ApiError({
        message: `統計取得エラー: HTTP ${response.status}`,
        status: response.status,
        code: getErrorCode({ status: response.status }),
        debug: errorText,
        requestId,
        backendUrl: backend,
      });
    }

    return await response.json();
  } catch (error) {
    throw new ApiError({
      message: getLocalizedErrorMessage(error),
      code: getErrorCode(error),
      debug: error instanceof Error ? error.message : 'Unknown error',
      requestId,
      backendUrl: process.env.NEXT_PUBLIC_BACKEND_URL,
    });
  }
}

// === ユーティリティ関数 ===

export function getLeadStatusClass(status: string): string {
  switch (status?.toLowerCase()) {
    case 'hot':
    case 'warm':
      return 'text-green-600 bg-green-100';
    case 'cold':
      return 'text-blue-600 bg-blue-100';
    case 'dead':
    case 'lost':
      return 'text-red-600 bg-red-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}
