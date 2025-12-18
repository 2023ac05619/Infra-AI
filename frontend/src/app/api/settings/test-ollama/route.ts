import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    let requestBody
    try {
      requestBody = await request.json()
    } catch (error) {
      console.error('Invalid JSON in request body:', error)
      return NextResponse.json({ error: 'Invalid JSON in request body' }, { status: 400 })
    }

    const { ollamaUrl } = requestBody

    if (!ollamaUrl) {
      return NextResponse.json({ error: 'Ollama URL is required' }, { status: 400 })
    }

    if (typeof ollamaUrl !== 'string' || !ollamaUrl.trim()) {
      return NextResponse.json({ error: 'Ollama URL must be a non-empty string' }, { status: 400 })
    }

    // Test connection and get models
    try {
      const response = await fetch(`${ollamaUrl}/api/tags`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: AbortSignal.timeout(10000) // 10 second timeout
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      
      return NextResponse.json({
        success: true,
        models: data.models || [],
        message: 'Connection successful'
      })
    } catch (error) {
      return NextResponse.json({
        success: false,
        error: error instanceof Error ? error.message : 'Failed to connect to Ollama server'
      }, { status: 400 })
    }
  } catch (error) {
    console.error('Error testing Ollama connection:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
