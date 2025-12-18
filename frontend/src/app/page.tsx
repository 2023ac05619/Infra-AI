'use client'

import { useState, useEffect, useRef } from 'react'
import { useSession, signIn, signOut } from 'next-auth/react'
import { useRouter, usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Send,
  Copy,
  Terminal,
  Globe,
  Key,
  User,
  X,
  Pin,
  PinOff,
  Menu,
  Mic,
  MicOff,
  Settings,
  Lightbulb,
  Play,
  MessageSquare,
  Palette,
  Eye,
  CheckCircle,
  XCircle,
  FileText,
  Moon,
  Sun,
  Monitor
} from 'lucide-react'
import { useTheme } from 'next-themes'
import { useToast } from '@/hooks/use-toast'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Sidebar } from '@/components/sidebar'
import { WorkingTerminal } from '@/components/terminal'
import { FileUpload } from '@/components/file-upload'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface PaneData {
  position: 'bottom' | 'right'
  type: 'key_values' | 'terminal' | 'code' | 'logs'
  data: any
}

interface ChatResponse {
  reply: string
  panes?: PaneData[]
  fallback?: boolean
  fallbackReason?: string
  selfHealingEnabled?: boolean
  ragApplied?: boolean
}

export default function InfraChat() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const { toast } = useToast()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [bottomPane, setBottomPane] = useState<PaneData | null>(null)
  const [allPaneData, setAllPaneData] = useState<Record<string, string>>({})
  const [showAllPaneData, setShowAllPaneData] = useState(false)
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0)

  const [rightPane, setRightPane] = useState<PaneData | null>(null)
  const [isBottomPaneOpen, setIsBottomPaneOpen] = useState(false)
  const [isRightPaneOpen, setIsRightPaneOpen] = useState(false)
  const [isRightPanePinned, setIsRightPanePinned] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [recognition, setRecognition] = useState<any>(null)

  const [userSettings, setUserSettings] = useState<any>(null)
  const [aiStatus, setAiStatus] = useState<'checking' | 'reachable' | 'unreachable'>('checking')
  const [availableModels, setAvailableModels] = useState<any[]>([])
  const [isLoadingModels, setIsLoadingModels] = useState(false)
  const [rightPaneSize, setRightPaneSize] = useState(30) // Default 30% width
  const [headerHeight, setHeaderHeight] = useState(0)
  const [inputHeight, setInputHeight] = useState(180) // Default fallback
  const [chatMode, setChatMode] = useState<'chat' | 'chat-with-infra'>('chat')
  const [selfHealingEnabled, setSelfHealingEnabled] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)


  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const headerRef = useRef<HTMLDivElement>(null)
  const inputAreaRef = useRef<HTMLDivElement>(null)
  const { theme, setTheme } = useTheme()

  // Redirect to sign in if not authenticated
  useEffect(() => {
    if (status === 'loading') return
    if (!session) {
      router.push('/auth/signin')
    } else if (!currentSessionId) {
      // Load the most recent chat session instead of creating new ones
      loadMostRecentChat()
    }
  }, [session, status, router, currentSessionId])

  // Redirect to password change if required
  useEffect(() => {
    if ((session?.user as any)?.forcePasswordReset) {
      router.push('/auth/change-password')
    }
  }, [session, router])

  // Function to load the most recent chat session
  const loadMostRecentChat = async () => {
    try {
      console.log('Loading most recent chat session...')
      const response = await fetch('/api/chat-sessions')
      console.log('Chat sessions response status:', response.status)
      if (response.ok) {
        const sessions = await response.json()
        console.log('Loaded chat sessions:', sessions.length)
        if (sessions.length > 0) {
          // Get the most recently updated session
          const recentSession = sessions.sort((a: any, b: any) =>
            new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
          )[0]
          console.log('Setting current session to:', recentSession.id)
          setCurrentSessionId(recentSession.id)
          // Messages will be loaded by the existing useEffect when currentSessionId changes
        } else {
          console.log('No existing sessions, creating new chat')
          // No existing sessions, create a new one
          createNewChat()
        }
      } else {
        console.log('Failed to load sessions, status:', response.status)
        // Failed to load sessions, create new chat
        createNewChat()
      }
    } catch (error) {
      console.error('Error loading recent chat:', error)
      // Fallback to creating new chat
      createNewChat()
    }
  }

  // Load messages when session changes, but only if it's not a temporary session being created
  // and only if we're not in the middle of sending a message
  useEffect(() => {
    if (session && currentSessionId && !currentSessionId.startsWith('temp-') && !isLoading) {
      loadMessages(currentSessionId)
    }
  }, [currentSessionId, session, isLoading])

  const loadMessages = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}/messages`)
      if (response.ok) {
        const messagesData = await response.json()
        setMessages(messagesData.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.createdAt)
        })))
      } else if (response.status === 401) {
        await signOut({ callbackUrl: '/auth/signin' })
      }
    } catch (error) {
      console.error('Error loading messages:', error)
    }
  }

  const createNewChat = async () => {
    // Create a temporary local session ID for UI purposes
    // Don't save to database until first message is sent
    const tempSessionId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    setCurrentSessionId(tempSessionId)

    setMessages([])
    closePanes()
    // Don't trigger sidebar refresh since this isn't saved yet
  }

  const handleSessionSelect = (sessionId: string) => {
    setCurrentSessionId(sessionId)
    setMessages([])
    closePanes()
  }

  const scrollToBottom = (force = false) => {
    setTimeout(() => {
      if (messagesEndRef.current) {
        // Find the ScrollArea container - improved search
        let container: HTMLElement | null = messagesEndRef.current.parentElement
        let scrollContainer: HTMLElement | null = null

        // Try to find the main scroll container
        while (container && !scrollContainer) {
          if (container.classList.contains('flex-1') && container.scrollHeight > container.clientHeight) {
            scrollContainer = container
            break
          }
          container = container.parentElement
        }

        if (scrollContainer) {
          const { scrollTop, scrollHeight, clientHeight } = scrollContainer
          // More aggressive auto-scroll: scroll if within 200px of bottom, or force scroll
          const distanceFromBottom = scrollHeight - scrollTop - clientHeight
          const isNearBottom = distanceFromBottom < 200 || force || isBottomPaneOpen

          if (isNearBottom) {
            // Scroll the container directly to bottom for more reliable behavior
            scrollContainer.scrollTo({
              top: scrollHeight,
              behavior: 'smooth'
            })
          }
        }

        // Always ensure the element is in view as fallback
        messagesEndRef.current.scrollIntoView({
          behavior: 'smooth',
          block: 'end',
          inline: 'nearest'
        })
      }
    }, 50) // Small delay to ensure DOM updates are complete
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }, [input])

  // Setup speech recognition
  useEffect(() => {
    console.log('Setting up speech recognition...')
    if (typeof window !== 'undefined') {
      console.log('Window available')
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

      if (SpeechRecognition) {
        console.log('SpeechRecognition API found')
        try {
          const recognitionInstance = new SpeechRecognition()

          recognitionInstance.continuous = false // Changed to false for better triggered recognition
          recognitionInstance.interimResults = true
          recognitionInstance.lang = 'en-US'

          recognitionInstance.onresult = (event: any) => {
            console.log('Recognition result event:', event)
            let transcript = ''
            for (let i = event.resultIndex; i < event.results.length; i++) {
              transcript += event.results[i][0].transcript
            }
            console.log('Transcript:', transcript)
            setInput(transcript)
          }

          recognitionInstance.onerror = (event: any) => {
            console.error('Speech recognition error:', event.error)
            setIsRecording(false)
          }

          recognitionInstance.onend = () => {
            console.log('Speech recognition ended')
            setIsRecording(false)
          }

          recognitionInstance.onstart = () => {
            console.log('Speech recognition started')
          }

          setRecognition(recognitionInstance)
          console.log('Speech recognition set up successfully')
        } catch (error) {
          console.error('Error creating speech recognition instance:', error)
        }
      } else {
        console.log('SpeechRecognition API not found')
      }
    } else {
      console.log('Window not available')
    }
  }, [])

  // Load user settings
  useEffect(() => {
    if (session && !isLoggingOut) {
      loadSettings()
    }
  }, [session, isLoggingOut])

  // Reload settings when window regains focus (after settings page)
  useEffect(() => {
    const handleFocus = () => {
      if (session && !isLoggingOut) {
        loadSettings()
      }
    }

    window.addEventListener('focus', handleFocus)
    return () => window.removeEventListener('focus', handleFocus)
  }, [session, isLoggingOut])

  // Initialize sidebar state and chat mode from settings when they load
  useEffect(() => {
    if (userSettings) {
      console.log('Loading userSettings:', userSettings)
      const shouldBeOpen = !userSettings.sidebarCollapsed
      setSidebarOpen(shouldBeOpen)

      // Load chat mode from settings if it exists
      if (userSettings.chatMode && (userSettings.chatMode === 'chat' || userSettings.chatMode === 'chat-with-infra')) {
        console.log('Setting chatMode from settings:', userSettings.chatMode)
        setChatMode(userSettings.chatMode as 'chat' | 'chat-with-infra')
      } else {
        console.log('No valid chatMode in settings, keeping default')
      }

      // Load self-healing enabled setting
      if (typeof userSettings.selfHealingEnabled === 'boolean') {
        setSelfHealingEnabled(userSettings.selfHealingEnabled)
      }
    } else {
      console.log('userSettings not loaded yet')
    }
  }, [userSettings])

  // Calculate header height dynamically
  useEffect(() => {
    const calculateHeaderHeight = () => {
      if (headerRef.current) {
        const height = headerRef.current.offsetHeight
        setHeaderHeight(height)
      }
    }

    // Calculate initially
    calculateHeaderHeight()

    // Recalculate when sidebar state changes (affects header positioning)
    const resizeObserver = new ResizeObserver(calculateHeaderHeight)
    if (headerRef.current) {
      resizeObserver.observe(headerRef.current)
    }

    return () => {
      resizeObserver.disconnect()
    }
  }, [sidebarOpen])

  // Calculate input area height dynamically
  useEffect(() => {
    const calculateInputHeight = () => {
      if (inputAreaRef.current && currentSessionId) {
        const height = inputAreaRef.current.offsetHeight
        setInputHeight(height)
      } else {
        setInputHeight(180) // Reset to default when no session
      }
    }

    // Calculate initially
    calculateInputHeight()

    const resizeObserver = new ResizeObserver(calculateInputHeight)
    if (inputAreaRef.current) {
      resizeObserver.observe(inputAreaRef.current)
    }

    return () => {
      resizeObserver.disconnect()
    }
  }, [currentSessionId])

  // Function to toggle sidebar and save preference
  const handleSidebarToggle = async () => {
    if (!userSettings) return

    const newSidebarOpen = !sidebarOpen

    // Immediately update UI
    setSidebarOpen(newSidebarOpen)

    // Save to server
    const newSettings = {
      ...userSettings,
      sidebarCollapsed: !newSidebarOpen
    }

    const success = await saveSettings(newSettings)
    if (!success) {
      // Revert on failure
      setSidebarOpen(!newSidebarOpen)
    }
  }

  // Check AI status periodically
  useEffect(() => {
    if (session && userSettings) {
      // Check immediately
      checkAIStatus()

      // Set up interval to check every 30 seconds
      const interval = setInterval(checkAIStatus, 30000)

      return () => clearInterval(interval)
    }
  }, [session, userSettings])

  // Fetch available models when userSettings change
  useEffect(() => {
    if (session && userSettings && userSettings.ollamaUrl) {
      loadAvailableModels()
    } else {
      setAvailableModels([])
    }
  }, [session, userSettings?.ollamaUrl])

  // Function to check AI status
  const checkAIStatus = async () => {
    if (!userSettings?.ollamaUrl) {
      setAiStatus('unreachable')
      return
    }

    try {
      const response = await fetch('/api/settings/test-ollama', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ollamaUrl: userSettings.ollamaUrl })
      })

      const data = await response.json()
      setAiStatus(data.success ? 'reachable' : 'unreachable')
    } catch (error) {
      console.error('Error checking AI status:', error)
      setAiStatus('unreachable')
    }
  }

  const loadSettings = async () => {
    try {
      const response = await fetch('/api/settings')
      if (response.ok) {
        const settings = await response.json()
        setUserSettings(settings)
      }
    } catch (error) {
      console.error('Error loading settings:', error)
    }
  }

  const saveSettings = async (newSettings: any) => {
    try {
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newSettings)
      })
      if (response.ok) {
        const updatedSettings = await response.json()
        setUserSettings(updatedSettings)
        return true
      }
    } catch (error) {
      console.error('Error saving settings:', error)
    }
    return false
  }

  const loadAvailableModels = async () => {
    if (!userSettings?.ollamaUrl) {
      setAvailableModels([])
      return
    }

    setIsLoadingModels(true)
    try {
      const response = await fetch('/api/settings/test-ollama', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ollamaUrl: userSettings.ollamaUrl })
      })

      const data = await response.json()

      if (data.success && data.models) {
        setAvailableModels(data.models)
        // Auto-select first model if available and none selected
        if (!userSettings.ollamaModel && data.models.length > 0) {
          await saveSettings({
            ...userSettings,
            ollamaModel: data.models[0].name
          })
        }
      } else {
        setAvailableModels([])
        console.error('Failed to load models:', data.error)
      }
    } catch (error) {
      console.error('Error loading models:', error)
      setAvailableModels([])
    } finally {
      setIsLoadingModels(false)
    }
  }

  const handleModelSelect = async (selectedModel: string) => {
    if (!userSettings) return

    const success = await saveSettings({
      ...userSettings,
      ollamaModel: selectedModel
    })

    if (success) {
      // Check AI status again since model might affect status
      await checkAIStatus()
    }
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading || !currentSessionId) return

    // Manual pane trigger keywords for testing - DISABLED for now due to command execution issues
    const shouldTriggerPane = false // input.toLowerCase().match(/\b(docker|run|execute|command|terminal|kubectl|bash|script)\b/i)

    setIsLoading(true)

    // Refocus cursor in input field for continuous typing
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus()
        // Position cursor at the end
        textareaRef.current.setSelectionRange(0, 0)
      }
    }, 0)

    try {
      // Store the input value before clearing it
      const messageText = input.trim()

      // Clear input immediately for better UX
      setInput('')

      // Check if this is a temporary session (not yet saved to database)
      const isTempSession = currentSessionId?.startsWith('temp-')

      let realSessionId = currentSessionId

      // Add the user message to the messages array
      // const userMessage: Message = {
      //   id: `user-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      //   role: 'user',
      //   content: messageText,
      //   timestamp: new Date()
      // }
      const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)  

      if (isTempSession) {
        // Create the chat session in database with the first message as title
        const title = messageText.length > 40 ? `${messageText.substring(0, 37)}...` : messageText
        const response = await fetch('/api/chat-sessions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title })
        })

        if (response.ok) {
          const newSession = await response.json()
          realSessionId = newSession.id

          // Save the user message to the database BEFORE switching session ID
          await fetch(`/api/sessions/${realSessionId}/messages`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              content: messageText,
              role: 'user'
            })
          })

          setCurrentSessionId(realSessionId)
          // Trigger sidebar refresh to show the new chat
          setSidebarRefreshTrigger(prev => prev + 1)
        } else {
          console.error('Failed to create chat session')
          return
        }
      } else {
        // For existing sessions, save the user message immediately
        await fetch(`/api/sessions/${realSessionId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            content: messageText,
            role: 'user'
          })
        })
      }



      // All chat modes use /api/chat with different chatMode parameter
      // 'chat-with-infra' will get infrastructure-specific context in the backend

      let response
      let data: ChatResponse

      try {
        response = await fetch('/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: messageText,
            history: messages.map(msg => ({ role: msg.role, content: msg.content })),
            chatMode: chatMode,
            useRAG: selfHealingEnabled
          })
        })

        if (!response.ok) {
          // Try to get error details from response
          let errorMessage = 'API request failed'
          try {
            const errorData = await response.json()
            errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}: ${response.statusText}`
          } catch (e) {
            errorMessage = `HTTP ${response.status}: ${response.statusText}`
          }
          throw new Error(errorMessage)
        }

        data = await response.json()
      } catch (error) {
        console.error('Error sending message:', error)
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date()
        }
        setMessages(prev => [...prev, errorMessage])
        setIsLoading(false)
        return
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.reply,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])

      // Save assistant message to database
      await fetch(`/api/sessions/${realSessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: data.reply,
          role: 'assistant'
        })
      })

      // Handle panes - only detect URLs for infrastructure-related content
      let urlData: Record<string, string> = {}
      let detectedAllData: Record<string, string> = {}

      // Check if the response contains infrastructure-related keywords or credentials
      const infrastructureKeywords = /\b(docker|kubernetes|k8s|server|database|db|port|host|endpoint|api|aws|azure|gcp|cloud|infra|infrastructure|deploy|container|cluster|virtual machine|vm|network|load balancer|storage|backup|monitoring|logging|alert|scaling|auto-scal|firewall|security|ssl|certificate|domain|subdomain)\b/i

      // Check for credentials/patterns that should trigger the pane
      const credentialPatterns = /\b(pass|password|token|key|secret|auth|credential|login|username|user|credential)\w*\s*[:=]\s*[^*\s]+/i
      const hasCredentials = credentialPatterns.test(data.reply)

      const hasInfraContent = infrastructureKeywords.test(data.reply) || infrastructureKeywords.test(input)
      const shouldTriggerPane = hasInfraContent || hasCredentials

      if (shouldTriggerPane) {
        // Detect URLs
        const urlRegex = /(https?:\/\/[^\s\)\n]+|[a-zA-Z0-9-]+\.(?:com|org|net|io|dev|app|internal|local|tech|ai|cloud)(?:\/[^\s\n]*)?)/g
        const allUrls: string[] = []

        // Match URLs that start with http/https
        const httpUrls = data.reply.match(/https?:\/\/[^\s\)\n]+/g) || []
        allUrls.push(...httpUrls)

        // Match domain-style URLs without https:// prefix
        const domainUrls = data.reply.match(/(?:^|\s)([a-zA-Z0-9-]+\.(?:com|org|net|io|dev|app|internal|local|tech|ai|cloud))(?:\/[^\s\n]*)?/g) || []
        // Clean up and prefix with https:// if needed
        domainUrls.forEach(url => {
          url = url.trim()
          if (!url.startsWith('http') && url.match(/[a-zA-Z]/)) {
            allUrls.push(`https://${url}`)
          }
        })

        if (allUrls.length > 0) {
          // Store all detected URLs
          allUrls.slice(0, 5).forEach((url, index) => {
            detectedAllData[`url${index + 1}`] = url.trim()
          })
          // Initially show only the latest URL
          urlData[`url`] = allUrls[allUrls.length - 1].trim()
        }

        // Detect credentials even if no URLs found
        const credentials: Record<string, string> = {}

        // Look for patterns like "password: xyz123", "token: abc", "key: 123", etc.
        const credMatches = data.reply.match(/(\b(?:pass|password|token|key|secret|auth|credential|login)\w*)\s*[:=]\s*([^*\s]+(?:\s+[^*\s]+)*?)(?=\s|$|[\n\r])/gi)
        if (credMatches) {
          credMatches.forEach((match, index) => {
            const parts = match.split(/[:=]/, 2)
            if (parts.length === 2) {
              const label = parts[0].trim()
              const value = parts[1].trim()
              credentials[`cred${index + 1}`] = value
              detectedAllData[`cred${index + 1}`] = value
            }
          })
        }

        // If we have URLs but no credentials, still show the pane
        // If we have credentials but no URLs, still show the pane with credentials
        if (Object.keys(urlData).length > 0 || Object.keys(credentials).length > 0) {
          // Merge any credentials with URLs
          urlData = { ...urlData, ...credentials }
        }
      }

      // Store all detected data for "Show All" functionality
      // Preserve user's current view preference (don't reset showAllPaneData)
      setAllPaneData(detectedAllData)

      // Handle explicit panes and merge with URL detection
      // DISABLED: All pane triggering removed for security
      // Note: Panes are now sticky - they stay open unless explicitly closed
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const toggleRecording = () => {
    if (!recognition) {
      alert('Speech recognition is not supported in your browser. Please try Chrome or Edge.')
      return
    }

    if (isRecording) {
      recognition.stop()
      setIsRecording(false)
    } else {
      recognition.start()
      setIsRecording(true)
      setInput('') // Clear input for fresh recording
    }
  }

  const closePanes = () => {
    if (!isRightPanePinned) {
      setIsRightPaneOpen(false)
      setRightPane(null)
    }
    setIsBottomPaneOpen(false)
    setBottomPane(null)
  }

  const renderKeyValuePairs = (data: Record<string, string>) => {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Object.entries(data).map(([key, value]) => {
          const getIcon = (key: string) => {
            if (key.includes('url') || key.includes('web')) return <Globe className="w-4 h-4" />
            if (key.includes('user') || key.includes('username')) return <User className="w-4 h-4" />
            if (key.includes('pass') || key.includes('token') || key.includes('key')) return <Key className="w-4 h-4" />
            if (key.includes('port')) return <Terminal className="w-4 h-4" />
            return null
          }

          const isUrl = key.includes('url') || key.includes('web')
          const isPassword = key.includes('pass') || key.includes('token')
          const displayValue = isPassword ? '••••••••' : value

          return (
            <Card key={key} className="p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {getIcon(key.toLowerCase())}
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium text-muted-foreground capitalize">
                      {key.replace(/_/g, ' ')}
                    </div>
                    <div className="text-sm font-mono truncate">
                      {isUrl ? (
                        <a
                          href={value}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-primary hover:text-primary/80 hover:underline transition-colors"
                          onClick={(e) => {
                            e.stopPropagation()
                          }}
                        >
                          {displayValue}
                        </a>
                      ) : (
                        displayValue
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1 ml-2 flex-shrink-0">
                  {isUrl && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(value, '_blank', 'noopener,noreferrer')}
                      className="h-8 w-8 p-0"
                      title="Open in new tab"
                    >
                      <Globe className="w-3.5 h-3.5" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(value)}
                    className="h-8 w-8 p-0"
                    title="Copy to clipboard"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          )
        })}
      </div>
    )
  }

  const runCommandInTerminal = (command: string) => {
    // Clean up the command (remove $, trim whitespace)
    const cleanCommand = command.replace(/^\$/, '').trim()
    setRightPane({
      position: 'right',
      type: 'terminal',
      data: cleanCommand
    })
    setIsRightPaneOpen(true)
  }

  const renderTerminal = (command: string) => {
    return (
      <div className="bg-black text-green-400 p-4 rounded-lg font-mono text-sm">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="text-gray-400 text-xs ml-2">Terminal</span>
        </div>
        <div className="flex items-center justify-between">
          <span>$ {command}</span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => copyToClipboard(command)}
            className="text-green-400 hover:text-green-300"
          >
            <Copy className="w-4 h-4" />
          </Button>
        </div>
      </div>
    )
  }

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!session) {
    return null // Will redirect to sign in
  }


  return (
    <div className="h-screen bg-background overflow-hidden">
      {/* Sidebar - Always visible */}
      <Sidebar
        key={sidebarRefreshTrigger}
        currentSessionId={currentSessionId}
        onSessionSelect={handleSessionSelect}
        onNewChat={createNewChat}
        isOpen={sidebarOpen}
        onToggle={handleSidebarToggle}
      />

      {/* Main Content Area with Resizable Panels */}
      <PanelGroup direction="horizontal" className="h-full">
        {/* Main Content Panel */}
        <Panel defaultSize={isRightPaneOpen ? 70 : 100} minSize={50} maxSize={100}>
          <div className="flex flex-col h-full" style={{ marginLeft: sidebarOpen ? '320px' : '60px' }}>
            {/* Header */}
            <header ref={headerRef} className="fixed top-0 z-10 border-b p-4 bg-background/95 backdrop-blur-sm transition-all duration-300" style={{ left: sidebarOpen ? '320px' : '60px', right: '0' }}>
              <div className="flex items-center justify-between max-w-full px-4">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                    <Terminal className="w-5 h-5 text-primary-foreground" />
                  </div>
                  <h1 className="text-xl font-bold">InfraAI</h1>
                  {/* <Badge variant="secondary" className="flex items-center gap-2">
                    <Lightbulb
                      className={`w-3 h-3 ${
                        aiStatus === 'reachable'
                          ? 'text-green-500'
                          : aiStatus === 'unreachable'
                          ? 'text-red-500'
                          : 'text-yellow-500'
                      }`}
                    />
                    AI Assistant
                  </Badge> */}
                  <Select
                    value={chatMode}
                    onValueChange={async (value: 'chat' | 'chat-with-infra') => {
                      console.log('ChatMode changing from', chatMode, 'to', value)
                      setChatMode(value)
                      console.log('ChatMode state after setChatMode:', chatMode) // This will still show old value due to async
                      // Save to user settings
                      if (userSettings) {
                        await saveSettings({
                          ...userSettings,
                          chatMode: value
                        })
                      }
                      // Create a new chat session when mode changes
                      await createNewChat()
                    }}
                  >
                    <SelectTrigger className="w-40 h-8">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="chat">Chat</SelectItem>
                      <SelectItem value="chat-with-infra">Chat with Infra</SelectItem>
                    </SelectContent>
                  </Select>
                  {userSettings?.aiProvider === 'ollama' && availableModels.length > 0 && (
                    <Select
                      value={userSettings.ollamaModel || ''}
                      onValueChange={handleModelSelect}
                      disabled={isLoadingModels}
                    >
                      <SelectTrigger className="w-48 h-8">
                        <SelectValue placeholder={isLoadingModels ? "Loading..." : "Select model"} />
                      </SelectTrigger>
                      <SelectContent>
                        {availableModels.map((model: any) => (
                          <SelectItem key={model.name} value={model.name}>
                            {model.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="self-healing-toggle" className="text-sm font-medium">
                      Autopilot
                    </Label>
                    <Switch
                      id="self-healing-toggle"
                      checked={selfHealingEnabled}
                      onCheckedChange={async (checked) => {
                        setSelfHealingEnabled(checked)
                        // Save to user settings - always save, even if userSettings not loaded yet
                        const settingsToSave = userSettings ? {
                          ...userSettings,
                          selfHealingEnabled: checked
                        } : {
                          selfHealingEnabled: checked,
                          chatMode: chatMode,
                          // Include other essential defaults
                          aiProvider: 'ollama',
                          theme: 'system',
                          language: 'en'
                        }
                        await saveSettings(settingsToSave)
                      }}
                      className="data-[state=checked]:bg-green-500"
                    />
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => router.push('/settings')}
                    className="h-9 w-9 p-0"
                    title="Settings"
                  >
                    <Settings className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const nextTheme = theme === 'light' ? 'dark' : 'light'
                      setTheme(nextTheme)
                    }}
                    className="h-9 w-9 p-0"
                    title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
                  >
                    {theme === 'light' ? (
                      <Moon className="w-4 h-4" />
                    ) : (
                      <Sun className="w-4 h-4" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      setIsLoggingOut(true)
                      await signOut({ redirect: false })
                      router.push('/auth/signin')
                    }}
                    className="h-9 px-3 text-xs"
                    title="Logout"
                  >
                    Logout
                  </Button>
                </div>
              </div>
            </header>

            {/* Content Tabs */}
            <Tabs defaultValue="chat" className="flex flex-col h-full">
              <div className="border-b bg-background/95 backdrop-blur-sm">
                <TabsList className="grid w-full grid-cols-2 max-w-md mx-auto mt-4 mb-2">
                  <TabsTrigger value="chat" className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    Chat
                  </TabsTrigger>
                  <TabsTrigger value="documents" className="flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    Documents
                  </TabsTrigger>
                </TabsList>
              </div>

              {/* Chat Tab */}
              <TabsContent value="chat" className="flex-1 flex flex-col m-0 min-h-0">
                <div className={`flex-1 overflow-y-auto p-4 pt-16 mt-[15px] mb-2.5 transition-all duration-300 ${currentSessionId ? 'pb-48' : 'pb-4'} ${isBottomPaneOpen ? 'pb-[50vh]' : ''} min-h-0`} style={{ scrollbarWidth: 'auto', scrollbarColor: 'var(--primary) var(--muted)', minHeight: 'calc(100vh - 200px)' }}>
                  <div className="chat-scroll max-w-full px-4 space-y-3">
                        {!currentSessionId ? (
                          <div className="text-center text-muted-foreground py-8">
                            <Terminal className="w-12 h-12 mx-auto mb-4 opacity-50" />
                            <p className="text-lg font-medium">Welcome to InfraChat</p>
                            <p className="text-sm mb-4">Select a chat or start a new conversation</p>
                            <Button onClick={createNewChat}>
                              Start New Chat
                            </Button>
                          </div>
                        ) : messages.length === 0 ? (
                          <>
                            <div className="text-center text-muted-foreground py-8">
                              <Terminal className="w-12 h-12 mx-auto mb-4 opacity-50" />
                              <p className="text-lg font-medium">New Chat</p>
                              <p className="text-sm">Ask me anything about your infrastructure</p>
                            </div>
                            {/* Test content to ensure scrolling works */}
                            <div className="space-y-4 opacity-30">
                              {Array.from({ length: 20 }, (_, i) => (
                                <div key={i} className="flex justify-start">
                                  <Card className="w-fit max-w-4xl border-slate-200 dark:border-slate-700 py-0.5">
                                    <CardContent className="px-2 py-1">
                                      <p className="text-sm text-muted-foreground"></p>
                                    </CardContent>
                                  </Card>
                                </div>
                              ))}
                            </div>
                          </>
                        ) : (
                          <>
                            <AnimatePresence>
                              {messages.map((message) => (
                                <motion.div
                                  key={message.id}
                                  initial={{ opacity: 0, y: 20 }}
                                  animate={{ opacity: 1, y: 0 }}
                                  exit={{ opacity: 0, y: -20 }}
                                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                  <Card className={`${message.role === 'user' ? 'max-w-2xl bg-gray-100 text-black border-gray-300 py-0.5 dark:bg-slate-800 dark:text-white dark:border-slate-700' : 'w-fit max-w-4xl border-slate-200 dark:border-slate-700 py-0.5'}`}>
                                    <CardContent className="px-2 py-1">
                                      <div className="markdown-content">
                                        <ReactMarkdown
                                          components={{
                                            // Enhanced headers with emoji numbers
                                            h2({ node, children, ...props }) {
                                              const content = String(children)
                                              // Check if this is a numbered section with emoji (like "1️⃣", "2️⃣", etc.)
                                              const emojiMatch = content.match(/^\s*(\d+️⃣|#️⃣||||)\s*(.+)$/)

                                              if (emojiMatch) {
                                                const [, emoji, title] = emojiMatch
                                                return (
                                                  <h2 className="text-xl font-bold text-primary mt-6 mb-4 flex items-center gap-3" {...props}>
                                                    <span className="text-2xl">{emoji}</span>
                                                    <span>{title}</span>
                                                  </h2>
                                                )
                                              }

                                              return (
                                                <h2 className="text-xl font-bold text-primary mt-6 mb-4" {...props}>
                                                  {children}
                                                </h2>
                                              )
                                            },

                                            // Style headers and subheaders nicely
                                            h3({ children, ...props }) {
                                              return (
                                                <h3 className="text-lg font-semibold text-foreground mt-4 mb-3" {...props}>
                                                  {children}
                                                </h3>
                                              )
                                            },

                                            h4({ children, ...props }) {
                                              return (
                                                <h4 className="text-base font-medium text-foreground mt-3 mb-2" {...props}>
                                                  {children}
                                                </h4>
                                              )
                                            },

            // Enhanced paragraphs
            p({ children, ...props }) {
              return (
                <p className="text-sm leading-relaxed text-foreground mb-0 text-center text-justify" {...props}>
                  {children}
                </p>
              )
            },

                                            // Enhanced code blocks with terminal styling
                                            code({ node, className, children, ...props }) {
                                              const inline = !node
                                              const match = /language-(\w+)/.exec(className || '')
                                              const codeContent = String(children).replace(/\n$/, '')

                                              // Handle code blocks (not inline)
                                              if (match && !inline) {
                                                const language = match[1]

                                                // Special handling for bash/shell/terminal blocks - add inline buttons
                                                if (['bash', 'sh', 'shell', 'terminal'].includes(language)) {
                                                  const lines = codeContent.split('\n')
                                                  return (
            <div className="relative bg-gradient-to-r from-slate-900 to-slate-800 rounded-lg p-4 font-mono text-sm overflow-x-auto border border-slate-700 shadow-md">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                  <span className="text-slate-400 text-xs font-medium uppercase tracking-wider">{language}</span>
                </div>
                                                        <div className="flex items-center gap-1">
                                                          <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => runCommandInTerminal(codeContent.replace(/^\$?\s*/gm, '').trim())}
                                                            className="h-6 w-6 p-0 hover:bg-green-700 hover:text-white text-slate-400"
                                                            title="Run command in terminal"
                                                          >
                                                            <Play className="w-3 h-3" />
                                                          </Button>
                                                          <Button
                                                            variant="ghost"
                                                            size="sm"
                                                            onClick={() => copyToClipboard(codeContent.replace(/^\$?\s*/gm, '').trim())}
                                                            className="h-6 w-6 p-0 hover:bg-slate-600 hover:text-white text-slate-400"
                                                            title="Copy command"
                                                          >
                                                            <Copy className="w-3 h-3" />
                                                          </Button>
                                                        </div>
                                                      </div>
                                                      <div className="space-y-1">
                                                        {lines.map((line, lineIndex) => {
                                                          const trimmedLine = line.trim()

                                                          // Skip empty lines
                                                          if (!trimmedLine) {
                                                            return <div key={lineIndex} className="h-5"></div>
                                                          }

                                                          // Check if this line is a comment or command
                                                          const isComment = trimmedLine.startsWith('#')
                                                          const commandPart = trimmedLine.split('#')[0].trim()

                                                          // Render line with optional play button and copy icon
                                                          return (
                                                            <div key={lineIndex} className="flex items-start gap-2 group">
                                                              <div className="flex-1 flex items-center min-w-0">
                                                                <span
                                                                  className={`${
                                                                    isComment
                                                                      ? 'text-slate-500 italic'
                                                                      : 'text-green-300'
                                                                  } flex-1 whitespace-pre-wrap break-all`}
                                                                  style={{ fontFamily: 'monospace' }}
                                                                >
                                                                  {line}
                                                                </span>
                                                              </div>
                                                              {!isComment && /[a-zA-Z0-9]/.test(commandPart) && (
                                                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex-shrink-0">
                                                                  <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    onClick={() => runCommandInTerminal(commandPart)}
                                                                    className="h-6 w-6 p-0 hover:bg-green-700 hover:text-white"
                                                                    title="Run command in terminal"
                                                                  >
                                                                    <Play className="w-3 h-3" />
                                                                  </Button>
                                                                  <Button
                                                                    variant="ghost"
                                                                    size="sm"
                                                                    onClick={() => copyToClipboard(commandPart)}
                                                                    className="h-6 w-6 p-0 hover:bg-slate-600 hover:text-white"
                                                                    title="Copy command"
                                                                  >
                                                                    <Copy className="w-3 h-3" />
                                                                  </Button>
                                                                </div>
                                                              )}
                                                            </div>
                                                          )
                                                        })}
                                                      </div>
                                                    </div>
                                                  )
                                                }

                                                // Regular code blocks with enhanced styling
                                                return (
                                                  <div className="relative">
                                                    <SyntaxHighlighter
                                                      style={oneDark as any}
                                                      language={match[1]}
                                                      PreTag="div"
                                                      className="rounded-lg !bg-slate-900 !border !border-slate-700"
                                                    >
                                                      {codeContent}
                                                    </SyntaxHighlighter>
                                                    <div className="absolute top-3 right-3 text-xs font-medium uppercase tracking-wider bg-slate-800 text-slate-400 px-2 py-1 rounded">
                                                      {language}
                                                    </div>
                                                  </div>
                                                )
                                              }

                                              // Enhanced inline code
                                              return (
                                                <code className="bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-1.5 py-0.5 rounded text-xs font-mono" {...props}>
                                                  {children}
                                                </code>
                                              )
                                            },

                                            // Enhanced strong/bold text
                                            strong({ children, ...props }) {
                                              return (
                                                <strong className="font-bold text-foreground" {...props}>
                                                  {children}
                                                </strong>
                                              )
                                            },

                                            // Enhanced emphasis/italic
                                            em({ children, ...props }) {
                                              return (
                                                <em className="italic text-foreground/80" {...props}>
                                                  {children}
                                                </em>
                                              )
                                            },

                                            // Enhanced lists
                                            ul({ children, ...props }) {
                                              return (
                                                <ul className="space-y-2 mb-4" {...props}>
                                                  {children}
                                                </ul>
                                              )
                                            },

                                            li({ children, ...props }) {
                                              return (
                                                <li className="text-sm text-muted-foreground flex items-start gap-2" {...props}>
                                                  <span className="text-primary mt-1.5 block w-1 h-1 rounded-full bg-current flex-shrink-0"></span>
                                                  {children}
                                                </li>
                                              )
                                            },

                                            // Enhanced tables for command cheat-sheets
                                            table({ children, ...props }) {
                                              return (
                                                <div className="overflow-x-auto my-4 border border-slate-200 dark:border-slate-700 rounded-lg">
                                                  <table className="w-full text-sm" {...props}>
                                                    {children}
                                                  </table>
                                                </div>
                                              )
                                            },

                                            thead({ children, ...props }) {
                                              return (
                                                <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700" {...props}>
                                                  {children}
                                                </thead>
                                              )
                                            },

                                            th({ children, ...props }) {
                                              return (
                                                <th className="py-3 px-4 text-left font-semibold text-slate-900 dark:text-slate-100 uppercase text-xs tracking-wider" {...props}>
                                                  {children}
                                                </th>
                                              )
                                            },

                                            tbody({ children, ...props }) {
                                              return (
                                                <tbody className="divide-y divide-slate-200 dark:divide-slate-700" {...props}>
                                                  {children}
                                                </tbody>
                                              )
                                            },

                                            td({ children, ...props }) {
                                              return (
                                                <td className="py-3 px-4 text-slate-700 dark:text-slate-300" {...props}>
                                                  {children}
                                                </td>
                                              )
                                            },

                                            // Enhanced blockquotes for notes/tips
                                            blockquote({ children, ...props }) {
                                              return (
                                                <blockquote className="border-l-4 border-primary bg-primary/5 py-3 px-4 my-4 rounded-r-lg text-sm text-muted-foreground" {...props}>
                                                  {children}
                                                </blockquote>
                                              )
                                            },

                                            // Enhanced horizontal rules for section breaks
                                            hr({ ...props }) {
                                              return (
                                                <hr className="my-8 border-slate-200 dark:border-slate-700" {...props} />
                                              )
                                            }
                                          }}
                                        >
                                          {message.content}
                                        </ReactMarkdown>
                                      </div>
                                    </CardContent>
                                  </Card>
                                </motion.div>
                              ))}
                            </AnimatePresence>
                          </>
                        )}

                        {isLoading && (
                          <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="flex justify-start"
                          >
                            <Card className="max-w-4xl">
                              <CardContent className="p-3">
                                <div className="flex items-center gap-2">
                                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                                </div>
                              </CardContent>
                            </Card>
                          </motion.div>
                        )}
                        <div ref={messagesEndRef} />
                      </div>
                </div>

            {/* Fixed Input - Always at bottom */}
            {currentSessionId && (
              <div ref={inputAreaRef} className="fixed bottom-0 z-20 border-t bg-background/95 backdrop-blur-sm p-6 transition-all duration-300" style={{ left: sidebarOpen ? '320px' : '60px', right: '0' }}>
                <div className="max-w-full px-4">
                  <div className="relative group">
                    <div className="absolute inset-0 bg-gradient-to-r from-primary/20 via-primary/10 to-primary/5 rounded-2xl blur-xl opacity-60 group-hover:opacity-80 group-hover:blur-2xl transition-all duration-500"></div>
                    <div className="relative flex items-end gap-3 bg-muted/30 border border-border/40 rounded-2xl p-3.5 backdrop-blur-sm transition-all duration-300 hover:border-primary/40 hover:bg-muted/40 focus-within:border-primary/60 focus-within:bg-background/90 focus-within:shadow-lg focus-within:shadow-primary/5">
                      <div className="flex-1 min-w-0">
                        <textarea
                          ref={textareaRef}
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          onKeyDown={handleKeyPress}
                          placeholder="Type or speak your message..."
                          rows={1}
                          autoFocus
                          className="w-full resize-none bg-transparent border-none outline-none text-base placeholder:text-muted-foreground/50 py-2.5 px-2 min-h-[28px] max-h-[120px] leading-relaxed overflow-y-auto scrollbar-thin scrollbar-thumb-muted-foreground/30 scrollbar-track-muted hover:scrollbar-thumb-muted-foreground/50"
                          style={{}}
                        />
                      </div>
                      <Button
                        onClick={toggleRecording}
                        disabled={isLoading}
                        size="sm"
                        variant={isRecording ? "destructive" : "ghost"}
                        className={`shrink-0 h-11 w-11 rounded-xl transition-all duration-200 hover:scale-105 active:scale-95 disabled:hover:scale-100 shadow-sm hover:shadow-md ${
                          isRecording
                            ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
                            : 'bg-muted/60 hover:bg-muted/80 text-muted-foreground hover:text-foreground'
                        }`}
                      >
                        {isRecording ? <MicOff className="w-4.5 h-4.5" /> : <Mic className="w-4.5 h-4.5" />}
                      </Button>
                      <Button
                        onClick={sendMessage}
                        disabled={isLoading || !input.trim()}
                        size="sm"
                        className="shrink-0 h-11 w-11 rounded-xl bg-primary hover:bg-primary/90 transition-all duration-200 hover:scale-105 active:scale-95 disabled:hover:scale-100 shadow-sm hover:shadow-md"
                      >
                        <Send className="w-4.5 h-4.5" />
                      </Button>
                    </div>
                    <div className="flex items-center justify-between mt-3 px-3">
                      <p className="text-xs text-muted-foreground/70 font-medium">
                        <kbd className="px-2 py-1 bg-muted/60 hover:bg-muted/80 rounded-md text-xs font-mono transition-colors">Enter</kbd>
                        <span className="mx-1.5">to send</span>
                        <kbd className="px-2 py-1 bg-muted/60 hover:bg-muted/80 rounded-md text-xs font-mono transition-colors">Shift+Enter</kbd>
                        <span className="mx-1.5">for new line</span>
                        <span className="mx-1.5">•</span>
                        <span className="mx-1.5">Click mic to record voice</span>
                      </p>
                      {isLoading && (
                        <div className="flex items-center gap-1.5">
                          <div className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse"></div>
                          <div className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" style={{ animationDelay: '0.15s' }}></div>
                          <div className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" style={{ animationDelay: '0.3s' }}></div>
                          <span className="text-xs text-muted-foreground/70 ml-2">Thinking...</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
                </TabsContent>

                {/* Documents Tab */}
                <TabsContent value="documents" className="flex-1 flex flex-col m-0">
                  <div className="flex-1 p-4">
                    <FileUpload />
                  </div>
                </TabsContent>
              </Tabs>
</div>
        </Panel>
      </PanelGroup>

      {/* Bottom Pane - Absolutely positioned at bottom */}
      <AnimatePresence>
        {isBottomPaneOpen && bottomPane && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className={`fixed bottom-0 right-0 bg-background border-t shadow-lg z-30`}
            style={{
              left: sidebarOpen ? '320px' : '60px',
              maxHeight: '50vh'
            }}
          >
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Key className="w-4 h-4" />
                  <span className="font-medium">Infrastructure Details</span>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const displayData = showAllPaneData ? allPaneData : bottomPane.data
                      const dataToCopy = Object.values(displayData).join('\n')
                      copyToClipboard(dataToCopy)
                    }}
                  >
                    Copy {showAllPaneData ? 'All' : 'Shown'}
                  </Button>
                  {Object.keys(allPaneData).length > 1 && !showAllPaneData && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setShowAllPaneData(true)
                        setBottomPane({
                          ...bottomPane,
                          data: allPaneData
                        })
                      }}
                    >
                      Show All
                    </Button>
                  )}
                  {showAllPaneData && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setShowAllPaneData(false)
                        setBottomPane({
                          ...bottomPane,
                          data: { url: Object.values(allPaneData)[Object.keys(allPaneData).length - 1] }
                        })
                      }}
                    >
                      Show Latest
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setIsBottomPaneOpen(false)
                      setBottomPane(null)
                      setAllPaneData({})
                      setShowAllPaneData(false)
                    }}
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              <ScrollArea className="max-h-64">
                {bottomPane.type === 'key_values' && renderKeyValuePairs(bottomPane.data)}
              </ScrollArea>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
