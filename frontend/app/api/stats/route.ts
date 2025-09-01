import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
    if (!backendUrl) {
      return NextResponse.json(
        { error: 'Internal server error', detail: 'NEXT_PUBLIC_BACKEND_URL is missing' },
        { status: 500 }
      );
    }
    const response = await fetch(`${backendUrl}/search-stats`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
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
