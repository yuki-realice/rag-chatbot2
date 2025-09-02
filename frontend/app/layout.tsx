import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'RAG Chat',
  description: 'Apple-like enterprise chat UI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ja">
      <body>
        <div className="min-h-screen px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </div>
      </body>
    </html>
  )
}