export const runtime = 'nodejs';

import { NextRequest } from 'next/server';

function getBackend(): string {
  const url = process.env.NEXT_PUBLIC_BACKEND_URL;
  if (!url) {
    throw new Error('NEXT_PUBLIC_BACKEND_URL is missing');
  }
  return url;
}

export async function POST(request: NextRequest) {
  try {
    const backendUrl = getBackend();
    const body = await request.json();

    const res = await fetch(`${backendUrl}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const text = await res.text();
    return new Response(text, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('content-type') || 'application/json' },
    });
  } catch (e: any) {
    return new Response(
      JSON.stringify({ error: 'Internal server error', detail: e?.message ?? 'fetch failed' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
