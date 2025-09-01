import { NextRequest, NextResponse } from 'next/server';

export async function GET(_req: NextRequest) {
  const hasKey = !!process.env.NEXT_PUBLIC_GEMINI_API_KEY;
  return NextResponse.json({ ok: hasKey });
}
