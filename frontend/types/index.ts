export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sources?: Source[];
  items?: CompanyInfo[];
}

export interface Source {
  source: string;
  content: string;
}

export interface CompanyInfo {
  company: string;
  lead_status: string;
  source_id: string;
}

export interface ChatResponse {
  status: string;
  answer?: string;
  sources?: Source[];
  items?: CompanyInfo[];
  message?: string;
}

export interface IngestResponse {
  status: string;
  message: string;
  processed_files?: string[];
  total_chunks?: number;
}

export interface UploadResponse {
  status: string;
  message: string;
  filename?: string;
}