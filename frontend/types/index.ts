export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sources?: Source[];
}

export interface Source {
  source: string;
  content: string;
}

export interface ChatResponse {
  status: string;
  answer?: string;
  sources?: Source[];
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

