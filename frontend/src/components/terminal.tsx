'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card } from '@/components/ui/card'
import {
  Terminal,
  Play,
  Copy,
  RotateCcw,
  ChevronDown,
  FolderOpen
} from 'lucide-react'

interface TerminalCommand {
  id: string
  command: string
  output: string
  error?: string
  exitCode: number
  timestamp: Date
  workingDirectory?: string
}

interface WorkingTerminalProps {
  initialCommand?: string
  onClose?: () => void
  onAskAI?: (command: string, output: string, error?: string) => void
  headerHeight?: number
}

export function WorkingTerminal({ initialCommand = '', onClose, onAskAI, headerHeight = 0 }: WorkingTerminalProps) {
  const [commands, setCommands] = useState<TerminalCommand[]>([])
  const [currentCommand, setCurrentCommand] = useState(initialCommand)
  const [isExecuting, setIsExecuting] = useState(false)
  const [workingDirectory, setWorkingDirectory] = useState(process.cwd() || '/home/z/my-project')
  const [commandHistory, setCommandHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [cursorPosition, setCursorPosition] = useState(0)
  const [lastExecutedCommand, setLastExecutedCommand] = useState('')
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const resizeObserverRef = useRef<ResizeObserver | null>(null)

  useEffect(() => {
    if (initialCommand && initialCommand !== lastExecutedCommand) {
      executeCommand(initialCommand)
      setLastExecutedCommand(initialCommand)
    }
  }, [initialCommand, lastExecutedCommand])

  const scrollToBottom = (force = false) => {
    setTimeout(() => {
      if (messagesEndRef.current) {
        // Find the ScrollArea container - exact same as chat
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
          const isNearBottom = distanceFromBottom < 200 || force || false // isBottomPaneOpen equivalent not needed for terminal

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
  }, [commands])

  const executeCommand = async (command: string) => {
    if (!command.trim()) return

    setIsExecuting(true)

    const newCommand: TerminalCommand = {
      id: Date.now().toString(),
      command,
      output: '',
      exitCode: -1,
      timestamp: new Date(),
      workingDirectory
    }

    setCommands(prev => [...prev, newCommand])

    try {
      const response = await fetch('/api/terminal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          command,
          workingDirectory
        })
      })

      const result = await response.json()

      setCommands(prev =>
        prev.map(cmd =>
          cmd.id === newCommand.id
            ? {
                ...cmd,
                output: result.output || '',
                error: result.error || '',
                exitCode: result.exitCode || 0
              }
            : cmd
        )
      )

      // Update working directory if cd command was successful
      if (command.trim().startsWith('cd ') && result.success && result.output) {
        const newDir = result.output.trim()
        if (newDir) {
          setWorkingDirectory(newDir)
        }
      }

    } catch (error) {
      setCommands(prev =>
        prev.map(cmd =>
          cmd.id === newCommand.id
            ? {
                ...cmd,
                error: 'Failed to execute command',
                exitCode: 1
              }
            : cmd
        )
      )
    } finally {
      setIsExecuting(false)
      setCurrentCommand('')
      inputRef.current?.focus()
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !isExecuting) {
      executeCommand(currentCommand)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (commandHistory.length > 0) {
        const newIndex = historyIndex === -1 ? 0 : Math.min(historyIndex + 1, commandHistory.length - 1)
        setHistoryIndex(newIndex)
        setCurrentCommand(commandHistory[newIndex] || '')
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1
        setHistoryIndex(newIndex)
        setCurrentCommand(commandHistory[newIndex] || '')
      } else if (historyIndex === 0) {
        setHistoryIndex(-1)
        setCurrentCommand('')
      }
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCurrentCommand(e.target.value)
    setCursorPosition(e.target.selectionStart || 0)
  }

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'Home' || e.key === 'End') {
      setTimeout(() => {
        setCursorPosition((e.target as HTMLInputElement).selectionStart || 0)
      }, 0)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const clearTerminal = () => {
    setCommands([])
  }

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  return (
    <div className="h-full flex flex-col bg-black text-green-400 font-mono text-sm relative">
      {/* Terminal Header */}
      <div className="flex items-center justify-between p-3 bg-gray-900 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-green-400" />
          <span className="text-white text-sm font-medium">Terminal</span>
          <div className="flex items-center gap-1 text-xs text-gray-400">
            <FolderOpen className="w-3 h-3" />
            <span className="truncate max-w-32">{workingDirectory}</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={clearTerminal}
            className="h-6 w-6 p-0 text-gray-400 hover:text-white"
            title="Clear terminal"
          >
            <RotateCcw className="w-3 h-3" />
          </Button>
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-6 w-6 p-0 text-gray-400 hover:text-white"
            >
              ×
            </Button>
          )}
        </div>
      </div>

      {/* Terminal Output - takes full height minus input height */}
      <ScrollArea
        ref={scrollAreaRef}
        className="flex-1 p-3 pb-16"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none', overflow: 'hidden' }}
      >
        <style jsx>{`
          [data-radix-scroll-area-viewport] {
            scrollbar-width: none !important;
            -ms-overflow-style: none !important;
            overflow-x: hidden !important;
            overflow-y: auto !important;
          }
          * [data-radix-scroll-area-viewport]::-webkit-scrollbar,
          [data-radix-scroll-area-viewport]::-webkit-scrollbar {
            display: none !important;
            width: 0 !important;
            height: 0 !important;
          }
          * [data-radix-scroll-area-viewport]::-webkit-scrollbar-track,
          [data-radix-scroll-area-viewport]::-webkit-scrollbar-track {
            display: none !important;
          }
          * [data-radix-scroll-area-viewport]::-webkit-scrollbar-thumb,
          [data-radix-scroll-area-viewport]::-webkit-scrollbar-thumb {
            display: none !important;
          }
          * [data-radix-scroll-area-viewport]::-webkit-scrollbar-corner,
          [data-radix-scroll-area-viewport]::-webkit-scrollbar-corner {
            display: none !important;
          }
          .terminal-scroll ::-webkit-scrollbar {
            display: none;
          }
        `}</style>
        <div className="terminal-scroll space-y-2">
        {commands.map((cmd) => (
          <div key={cmd.id} className="space-y-1">
            {/* Command Input */}
            <div className="flex items-center gap-2">
              <span className="text-green-400">$</span>
              <span className="text-white flex-1">{cmd.command}</span>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => copyToClipboard(cmd.command)}
                  className="h-4 w-4 p-0 text-gray-400 hover:text-white"
                  title="Copy command"
                >
                  <Copy className="w-3 h-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    console.log('Play button clicked for command:', cmd.command)
                    executeCommand(cmd.command)
                  }}
                  disabled={isExecuting}
                  className="h-6 w-6 p-0 text-slate-400 hover:bg-green-700 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                  title={`Run again: ${cmd.command}`}
                >
                  <Play className="w-3 h-3" />
                </Button>
              </div>
            </div>

            {/* Command Output */}
            {cmd.output && (
              <div className="ml-4 text-green-300 whitespace-pre-wrap break-words">
                {cmd.output}
              </div>
            )}

            {/* Command Error */}
            {cmd.error && (
              <div className="ml-4 text-red-400 whitespace-pre-wrap break-words">
                {cmd.error}
              </div>
            )}

            {/* Exit Code */}
            {cmd.exitCode !== 0 && (
              <div className="ml-4 text-yellow-400 text-xs">
                Exit code: {cmd.exitCode}
              </div>
            )}

            {/* Timestamp */}
            <div className="ml-4 text-gray-500 text-xs">
              {formatTimestamp(cmd.timestamp)}
            </div>
          </div>
        ))}

        {/* Loading Indicator */}
        {isExecuting && (
          <div className="flex items-center gap-2">
            <span className="text-green-400">$</span>
            <span className="text-white">{currentCommand}</span>
            <div className="flex items-center gap-1">
              <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse"></div>
              <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse" style={{ animationDelay: '0.1s' }}></div>
              <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
            </div>
          </div>
        )}

        {/* Invisible element to mark the end for scrolling */}
        <div ref={messagesEndRef} />
        </div>
      </ScrollArea>

      {/* Terminal Input - Fixed at bottom */}
      <div className="absolute bottom-0 left-0 right-0 border-t border-gray-700 p-3 bg-gray-900">
        <div className="flex items-center gap-2">
          <span className="text-green-400">$</span>
          <input
            ref={inputRef}
            type="text"
            value={currentCommand}
            onChange={handleInputChange}
            onKeyDown={handleInputKeyDown}
            onKeyPress={handleKeyPress}
            disabled={isExecuting}
            placeholder="Type a command..."
            className="flex-1 bg-transparent border-none outline-none text-white placeholder-gray-500 disabled:opacity-50"
          />
          <Button
            onClick={() => executeCommand(currentCommand)}
            disabled={isExecuting || !currentCommand.trim()}
            size="sm"
            className="h-6 px-2 bg-green-600 hover:bg-green-700 text-white text-xs"
          >
            Run
          </Button>
        </div>
      </div>
    </div>
  )
}
