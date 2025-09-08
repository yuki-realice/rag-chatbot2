// Gemini embeddings utility for Next.js frontend
// Throws clear error if API key is missing and uses text-embedding-004

import { GoogleGenerativeAI } from "@google/generative-ai";

const GEMINI_API_KEY = process.env.NEXT_PUBLIC_GEMINI_API_KEY;

function assertApiKey(): string {
  if (!GEMINI_API_KEY) {
    throw new Error("Gemini API key is missing. Set NEXT_PUBLIC_GEMINI_API_KEY in .env.local.");
  }
  return GEMINI_API_KEY as string;
}

export async function embedText(text: string): Promise<number[]> {
  const key = assertApiKey();
  const genAI = new GoogleGenerativeAI(key);
  const model = genAI.getGenerativeModel({ model: "text-embedding-004" });

  const result = await model.embedContent(text);

  const values = (result as any)?.embedding?.values ?? (result as any)?.embedding?.value;
  if (!values || !Array.isArray(values)) {
    throw new Error("Embedding response was invalid");
  }
  return values as number[];
}

export async function embedMany(texts: string[]): Promise<number[][]> {
  const embeddings: number[][] = [];
  for (const t of texts) {
    embeddings.push(await embedText(t));
  }
  return embeddings;
}

export function hasFrontendGeminiKey(): boolean {
  return !!process.env.NEXT_PUBLIC_GEMINI_API_KEY;
}
