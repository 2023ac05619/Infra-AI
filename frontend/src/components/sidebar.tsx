'use client'

import { useState, useEffect } from 'react'
import { useSession, signOut } from 'next-auth/react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import {
  MessageSquare,
  Plus,
  Menu,
  X,
  LogOut,
  Moon,
  Sun,
  User,
  Trash2,
  Lightbulb
} from 'lucide-react'
import { useTheme } from 'next-themes'

interface ChatSession {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  _count: { messages: number }
}

interface SidebarProps {
  currentSessionId: string | null
  onSessionSelect: (sessionId: string) => void
  onNewChat: () => void
  isOpen: boolean
  onToggle: () => void
}

const COLLAPSED_WIDTH = 60 // Thin sidebar width
const EXPANDED_WIDTH = 320 // Full sidebar width

export function Sidebar({ 
  currentSessionId, 
  onSessionSelect, 
  onNewChat, 
  isOpen, 
  onToggle 
}: SidebarProps) {
  const { data: session } = useSession()
  const { theme, setTheme } = useTheme()
  const router = useRouter()
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([])
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    if (session?.user) {
      fetchChatSessions()
    }
  }, [session])

  const fetchChatSessions = async () => {
    try {
      setIsLoading(true)
      const response = await fetch('/api/chat-sessions')
      if (response.ok) {
        const sessions = await response.json()
        setChatSessions(sessions)
      }
    } catch (error) {
      // Error fetching chat sessions
    } finally {
      setIsLoading(false)
    }
  }

  const handleSignOut = async () => {
    await signOut({ redirect: false })
    router.push('/auth/signin')
  }

  const handleDeleteChat = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent triggering the chat selection
    
    if (!confirm('Are you sure you want to delete this chat? This action cannot be undone.')) {
      return
    }

    try {
      const response = await fetch(`/api/chat-sessions?sessionId=${sessionId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        // Remove the chat from local state
        setChatSessions(prev => prev.filter(session => session.id !== sessionId))
        
        // If the deleted chat was the current one, clear the current session
        if (currentSessionId === sessionId) {
          onSessionSelect('')
        }
      } else {
        // Failed to delete chat session
      }
    } catch (error) {
      // Error deleting chat session
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = Math.abs(now.getTime() - date.getTime())
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    return date.toLocaleDateString()
  }

  return (
    <>
      {/* Always visible collapsed sidebar */}
      <motion.div
        initial={false}
        animate={{
          width: isOpen ? EXPANDED_WIDTH : COLLAPSED_WIDTH,
          transition: { duration: 0.3, ease: 'easeInOut' }
        }}
        className="fixed left-0 top-0 h-full bg-background/95 backdrop-blur-xl border-r border-border/50 z-40 flex flex-col"
        style={{
          justifyContent: !isOpen ? 'space-between' : 'initial'
        }}
      >
        {/* Collapsed Header - Always visible */}
        <div className="flex flex-col items-center gap-4 p-4 border-b border-border/50">
          {/* Expand/Collapse Button */}
          <Button
            variant="ghost"
            size="sm"
            onClick={onToggle}
            className={`${isOpen ? 'self-end' : 'w-full justify-center'} transition-all duration-300`}
          >
            {isOpen ? <Menu className="w-4 h-4" /> : <MessageSquare className="w-5 h-5" />}
          </Button>

          {/* New Chat Button - Collapsed or expanded */}
          <AnimatePresence>
            {!isOpen ? (
              <motion.div
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Button
                  onClick={onNewChat}
                  variant="default"
                  size="sm"
                  className="w-8 h-8 p-0"
                  title="New Chat"
                >
                  <Plus className="w-4 h-4" />
                </Button>
              </motion.div>
            ) : null}
          </AnimatePresence>
        </div>

        {/* User Icon - Bottom of collapsed sidebar */}
        <AnimatePresence>
          {!isOpen && session?.user ? (
            <motion.div
              initial={{ opacity: 0, scale: 0 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0 }}
              transition={{ duration: 0.1, delay: isOpen ? 0.1 : 0 }}
              className="flex justify-center pb-4"
            >
              <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                <Avatar className="w-6 h-6">
                  <AvatarImage src={session.user.image || ''} />
                  <AvatarFallback className="text-xs bg-black text-white">
                    {(session.user.name?.charAt(0) || session.user.email?.charAt(0) || 'U').toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>

        {/* Content - Only visible when expanded */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2, delay: 0.1 }}
              className="flex flex-col h-full"
            >
              {/* New Chat Button - Expanded */}
              <div className="p-4">
                <Button
                  onClick={onNewChat}
                  className="w-full justify-start gap-2 h-11"
                  variant="default"
                >
                  <Plus className="w-4 h-4" />
                  New Chat
                </Button>
              </div>

              {/* Chat Sessions */}
              <ScrollArea className="flex-1 px-4">
                <div className="space-y-2 pb-4">
                  {isLoading ? (
                    <div className="space-y-2">
                      {[1, 2, 3].map((i) => (
                        <div
                          key={i}
                          className="h-16 bg-muted/50 rounded-lg animate-pulse"
                        />
                      ))}
                    </div>
                  ) : chatSessions.length === 0 ? (
                    <div className="text-center text-muted-foreground py-8">
                      <MessageSquare className="w-12 h-12 mx-auto mb-2 opacity-50" />
                      <p className="text-sm">No chat history yet</p>
                      <p className="text-xs">Start a new conversation</p>
                    </div>
                  ) : (
                    chatSessions.map((chatSession) => (
                      <motion.div
                        key={chatSession.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className={`w-full text-left p-3 rounded-lg transition-all duration-200 group ${
                          currentSessionId === chatSession.id
                            ? 'bg-primary/10 border border-primary/20'
                            : 'hover:bg-muted/50 border border-transparent'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <button
                            onClick={() => onSessionSelect(chatSession.id)}
                            className="flex-1 min-w-0 text-left"
                          >
                            <h3 className="text-sm font-medium truncate">
                              {chatSession.title}
                            </h3>
                            <div className="flex items-center gap-2 mt-1">
                              <p className="text-xs text-muted-foreground">
                                {formatDate(chatSession.updatedAt)}
                              </p>
                              <Badge variant="secondary" className="text-xs">
                                {chatSession._count.messages} msgs
                              </Badge>
                            </div>
                          </button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => handleDeleteChat(chatSession.id, e)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 h-8 w-8 p-0 hover:bg-destructive/10 hover:text-destructive"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </motion.div>
                    ))
                  )}
                </div>
              </ScrollArea>

              {/* User Section - Bottom */}
              {session?.user && (
                <div className="p-4 border-t border-border/50">
                  <div className="flex items-center gap-3 w-full p-3">
                    <Avatar className="h-10 w-10">
                      <AvatarImage src={session.user.image || ''} />
                      <AvatarFallback className="bg-black text-white">
                        {(session.user.name?.charAt(0) || session.user.email?.charAt(0) || 'U').toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0 text-left">
                      <p className="text-sm font-medium truncate">
                        {session.user.name || session.user.email}
                      </p>
                      <p className="text-xs text-muted-foreground truncate">
                        {session.user.email}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Footer */}
              <div className="p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                    className="flex-1 justify-start"
                  >
                    {theme === 'dark' ? <Sun className="w-4 h-4 mr-2" /> : <Moon className="w-4 h-4 mr-2" />}
                    {theme === 'dark' ? 'Light' : 'Dark'}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleSignOut}
                    className="flex-1 justify-start"
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Sign Out
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </>
  )
}
