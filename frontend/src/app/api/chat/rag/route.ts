import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { db } from '@/lib/db'

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

interface RAGChatRequest {
  message: string
  history: ChatMessage[]
  useRAG?: boolean
}

interface PaneData {
  position: 'bottom' | 'right'
  type: 'key_values' | 'terminal' | 'code' | 'logs'
  data: any
}

interface ChatResponse {
  reply: string
  panes?: PaneData[]
}

// Function to detect URLs, usernames, passwords, and other sensitive info
function detectSensitiveInfo(text: string): PaneData[] {
  const panes: PaneData[] = []
  const detectedData: Record<string, string> = {}

  // URL patterns
  const urlPatterns = [
    /https?:\/\/[^\s\)]+/gi,
    /www\.[^\s\)]+/gi,
    /\b[a-zA-Z0-9.-]+\.(?:com|org|net|io|dev|app|internal|local|tech|ai|cloud)\b/gi
  ]

  // Username patterns
  const usernamePatterns = [
    /(?:username|user|login|email)[:\s=]+([^\s\n]+?)(?:\s|$|\n)/gi,
    /(?:admin|root|guest)[:\s=]+([^\s\n]+?)(?:\s|$|\n)/gi
  ]

  // Password patterns
  const passwordPatterns = [
    /(?:password|pass|pwd|secret|token|key)[:\s=]+([^\s\n]+?)(?:\s|$|\n)/gi
  ]

  // Port patterns
  const portPatterns = [
    /(?:port|Port)[:\s=]+(\d+)(?:\s|$|\n)/gi,
    /:(\d{2,5})(?:\/|\s|$|\n)/g
  ]

  // Extract URLs
  urlPatterns.forEach(pattern => {
    const matches = text.match(pattern)
    if (matches) {
      matches.forEach((url, index) => {
        if (!url.startsWith('http') && !url.startsWith('www')) return
        const key = url.includes('://') ? 'url' : `url_${index + 1}`
        detectedData[key] = url.startsWith('http') ? url : `https://${url}`
      })
    }
  })

  // Extract usernames
  usernamePatterns.forEach(pattern => {
    let match
    while ((match = pattern.exec(text)) !== null) {
      const username = match[1].replace(/[,:;]+$/, '')
      if (username && username.length > 0) {
        detectedData['username'] = username
      }
    }
  })

  // Extract passwords (mask them)
  passwordPatterns.forEach(pattern => {
    let match
    while ((match = pattern.exec(text)) !== null) {
      const password = match[1].replace(/[,:;]+$/, '')
      if (password && password.length > 0) {
        detectedData['password'] = '••••••••'
      }
    }
  })

  // Extract ports
  portPatterns.forEach(pattern => {
    let match
    while ((match = pattern.exec(text)) !== null) {
      const port = match[1]
      if (port && parseInt(port) > 0 && parseInt(port) <= 65535) {
        detectedData['port'] = port
      }
    }
  })

  // If we found any sensitive info, create a pane
  if (Object.keys(detectedData).length > 0) {
    panes.push({
      position: 'bottom',
      type: 'key_values',
      data: detectedData
    })
  }

  return panes
}

export async function POST(request: NextRequest) {
  try {
    const body: RAGChatRequest = await request.json()
    const { message, history, useRAG = false } = body

    if (!message) {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      )
    }

    // Get user session and settings
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const userSettings = await db.userSettings.findUnique({
      where: { userId: session.user.id }
    })

    // If useRAG is true or message contains configurable infrastructure keywords, use backend services
    const keywordsList = (userSettings as any)?.infrastructureKeywords?.split(',').map(k => k.trim()).filter(k => k.length > 0) || []
    const infrastructurePattern = keywordsList.length > 0 ? new RegExp(`\\b(${keywordsList.join('|')})\\b`, 'i') : null
    const shouldUseBackend = useRAG || (infrastructurePattern?.test(message) || false)

    if (shouldUseBackend) {
      // Infrastructure Intelligence Agent system prompt for RAG
      const ragSystemPrompt = `You are an Infrastructure Intelligence Agent.

You are responsible for analyzing and interpreting infrastructure-related data retrieved from the RAG database.
The data includes server configurations, cluster states, deployment details, system logs, metrics, and other operational information about the infrastructure.

Your goals:
1. Understand the user's intent — what they want to know about the infrastructure (e.g., number of web servers, status of clusters, Redis nodes, etc.).
2. Examine the retrieved context data carefully and extract relevant, factual details.
3. Structure your reasoning clearly and provide a concise, well-formatted answer.

Rules:
- Always base your answer strictly on the retrieved RAG data. Do not hallucinate.
- If some details are missing or uncertain, say so explicitly (e.g., "No data found on Redis clusters.").
- When possible, summarize findings in a structured format (lists, tables, or short bullet points).
- Focus only on infrastructure, systems, or operational topics.
- Follow this reasoning pipeline for every query:
  **Retrieve → Analyze → Correlate → Summarize → Respond**

Your output should always be professional, technically precise, and easy to understand.`

      // Note: Removed unnecessary backend settings sync call
      // System prompts are handled internally by the backend RAG service

      // Call backend RAG service (direct RAG, no auto-routing) with timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout

      const backendResponse = await fetch(`${process.env.BACKEND_URL || 'http://localhost:8000'}/api/v1/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: message,
          k: 6 // Default value for number of documents to retrieve
        }),
        signal: controller.signal
      })

      clearTimeout(timeoutId)

      if (!backendResponse.ok) {
        console.warn(`Backend returned ${backendResponse.status}, falling back to basic chat`)
        // Instead of redirecting, call basic chat directly and mark as fallback
        const fallbackResponse = await fetch(new URL('/api/chat', request.url), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message,
            history,
            useRAG: false
          })
        })

        if (fallbackResponse.ok) {
          const fallbackData = await fallbackResponse.json()
          // Add fallback indicator to the response
          return NextResponse.json({
            ...fallbackData,
            fallback: true,
            fallbackReason: 'RAG backend unavailable'
          })
        }

        // If fallback also fails, return error
        throw new Error('Both RAG and basic chat failed')
      }

      const backendData = await backendResponse.json()

      // Format response for frontend
      const response: ChatResponse = {
        reply: backendData.response,
        panes: []
      }

      // Add source information as pane if available
      if (backendData.sources && backendData.sources.length > 0) {
        response.panes?.push({
          position: 'right',
          type: 'logs',
          data: ` RAG Analysis Results:\n\n${backendData.sources.map((source: any) =>
            ` ${source.filename || 'Document'}\n Relevance: ${source.score?.toFixed(2) || 'N/A'}\n Excerpt: ${source.content?.substring(0, 200) || ''}...`
          ).join('\n\n')}`
        })
      }

      // Add processing mode information
      response.panes?.push({
        position: 'right',
        type: 'logs',
        data: ` AI Processing:\nMode: Infrastructure Intelligence Agent\nDescription: Analyzing infrastructure data with RAG retrieval`
      })

      // Detect infrastructure info in response
      const detectedPanes = detectSensitiveInfo(response.reply)
      if (detectedPanes.length > 0) {
        response.panes = [...(response.panes || []), ...detectedPanes]
      }

      return NextResponse.json(response)
    }

    // For non-infrastructure queries, redirect to basic chat
    return NextResponse.redirect(new URL('/api/chat', request.url))

  } catch (error) {
    console.error('RAG Chat API error:', error)
    // For network errors (Python backend not running), let the frontend handle the fallback
    // by throwing the error instead of returning a response
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        // Timeout - let frontend handle
        throw error
      }
      if (error.message.includes('fetch')) {
        // Network error - let frontend handle
        throw error
      }
    }

    // For other errors, return a response that frontend can handle
    return NextResponse.json(
      {
        error: 'RAG service temporarily unavailable',
        reply: 'I apologize, but the advanced RAG services are currently unavailable. Your query has been processed with basic chat instead.',
        panes: []
      },
      { status: 503 }
    )
  }
}
