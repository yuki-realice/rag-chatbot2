import { NextRequest, NextResponse } from 'next/server'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const cell = searchParams.get('cell')

    if (!cell) {
      return NextResponse.json(
        { error: 'cellパラメータが必要です' },
        { status: 400 }
      )
    }

    const response = await fetch(`${BACKEND_URL}/company/by-cell?cell=${encodeURIComponent(cell)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorText = await response.text()
      return NextResponse.json(
        { error: 'バックエンドエラー', detail: errorText },
        { status: response.status }
      )
    }

    const data = await response.json()
    return NextResponse.json(data)

  } catch (error) {
    console.error('API Error:', error)
    return NextResponse.json(
      { error: 'APIエラー', detail: error instanceof Error ? error.message : '不明なエラー' },
      { status: 500 }
    )
  }
}
