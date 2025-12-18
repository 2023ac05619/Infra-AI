import { NextRequest, NextResponse } from 'next/server'
import ZAI from 'z-ai-web-dev-sdk'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { db } from '@/lib/db'

interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

interface ChatRequest {
  message: string
  history: ChatMessage[]
  chatMode?: string
  useRAG?: boolean
}

interface RAGChatRequest {
  message: string
  history: ChatMessage[]
  userSettings?: any
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

// Function to call Ollama API
async function callOllamaAPI(messages: { role: string; content: string }[], ollamaUrl: string, model: string, maxTokens: number, temperature: number) {
  try {
    const response = await fetch(`${ollamaUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: model,
        messages: messages,
        stream: false,
        options: {
          temperature: temperature,
          num_predict: maxTokens
        }
      })
    })

    if (!response.ok) {
      throw new Error(`Ollama API error: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    return data.message?.content || 'No response from Ollama'
  } catch (error) {
    console.error('Ollama API error:', error)
    throw error
  }
}

export async function POST(request: NextRequest) {
  try {
    console.log('[FRONTEND-API] Received request')
    const body: ChatRequest = await request.json()
    console.log('[FRONTEND-API] Parsed body:', JSON.stringify(body, null, 2))

    const { message, history, chatMode, useRAG } = body
    console.log('[FRONTEND-API] Extracted message:', message)
    console.log('[FRONTEND-API] Message length:', message?.length)

    if (!message) {
      console.log('[FRONTEND-API] Message is empty, returning 400')
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      )
    }

    // Get user session
    const session = await getServerSession(authOptions)
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    // Get backend configuration from environment
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8001'
    const apiKey = process.env.BACKEND_API_KEY || 'dev-key-12345'

    // Create a unique session ID for this conversation
    const sessionId = `frontend_${session?.user?.id || 'anonymous'}_${Date.now()}`

    // Prepare the request for InfraAI backend with full conversation context
    const infraAiRequest = {
      session_id: sessionId,
      prompt: message,
      chatMode: chatMode || 'chat',
      useRAG: useRAG || false,
      history: history || []  // Include full conversation history
    }

    // Call InfraAI backend
    const response = await fetch(`${backendUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-KEY': apiKey
      },
      body: JSON.stringify(infraAiRequest)
    })

    if (!response.ok) {
      throw new Error(`InfraAI backend error: ${response.status} ${response.statusText}`)
    }

    const infraAiResponse = await response.json()

    // Convert InfraAI response to InfraChat format
    let chatResponse: ChatResponse = {
      reply: infraAiResponse.message?.content || infraAiResponse.message || 'No response from InfraAI',
      panes: []
    }

    // Try to parse JSON response, fallback to plain text if not valid JSON
    try {
      const responseContent = chatResponse.reply
      // Look for JSON code blocks in the response
      const jsonMatch = responseContent.match(/```json\s*([\s\S]*?)\s*```/)
      if (jsonMatch) {
        chatResponse = JSON.parse(jsonMatch[1])
      } else {
        // Try to parse the entire response as JSON
        chatResponse = JSON.parse(responseContent)
      }
    } catch (e) {
      // If parsing fails, keep the plain text response
      // chatResponse is already set above
    }

    // Validate response structure
    if (!chatResponse.reply) {
      chatResponse.reply = infraAiResponse.message?.content || infraAiResponse.message || 'No response from InfraAI'
    }

    // Auto-detect URLs, usernames, and passwords in the response
    const detectedPanes = detectSensitiveInfo(chatResponse.reply)
    if (detectedPanes.length > 0) {
      chatResponse.panes = [...(chatResponse.panes || []), ...detectedPanes]
    }

    return NextResponse.json(chatResponse)

  } catch (error) {
    console.error('Chat API error:', error)
    return NextResponse.json(
      {
        error: 'Internal server error',
        reply: 'Sorry, I encountered an error while processing your request. Please try again.',
        panes: []
      },
      { status: 500 }
    )
  }
}
