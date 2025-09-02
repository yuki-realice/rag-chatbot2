export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sources?: Source[];
  items?: CompanyInfo[] // ← 追加
}

export interface Source {
  source: string;
  content: string;
}

export interface CompanyInfo { // ← 追加
  company: string;
  lead_status: string;
  source_id: string;
}

export interface ChatResponse {
  status: string;
  answer?: string;
  sources?: Source[];
  items?: CompanyInfo[]; // ← 追加
  message?: string;
}

// 既存の他の型はそのまま