import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const apiKey = process.env.NEXT_PUBLIC_GEMINI_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: 'Gemini API key is missing. Set NEXT_PUBLIC_GEMINI_API_KEY in .env.local.' },
        { status: 500 }
      );
    }
    const { message } = await request.json();
    if (!message?.trim()) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (!backendUrl) {
      return NextResponse.json(
        { error: 'Internal server error', detail: 'NEXT_PUBLIC_BACKEND_URL is missing' },
        { status: 500 }
      );
    }

    // EnhancedRetrieverを使用するために /chat から /api/ask に変更
    const response = await fetch(`${backendUrl}/api/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    const text = await response.text();
    return new Response(text, { status: response.status, headers: { 'Content-Type': response.headers.get('content-type') || 'application/json' } });
  } catch (error) {
    console.error('API route error:', error);
    return NextResponse.json(
      { error: 'Internal server error', detail: error instanceof Error ? error.message : 'fetch failed' },
      { status: 500 }
    );
  }
}
